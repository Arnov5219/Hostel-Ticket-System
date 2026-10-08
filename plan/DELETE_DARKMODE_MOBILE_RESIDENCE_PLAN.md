# Hostel Ticket System: Residence, Ticket Deletion, Dark Mode & Mobile

> **For Antigravity.** Feature addendum to `HOSTEL_TICKET_SYSTEM_PLAN.md`, `UI_UX_IMPROVEMENT_PLAN.md`, and `COMMUNITY_FEED_AND_ANNOUNCEMENTS_PLAN.md`. It adds four things:
>
> 1. **Mandatory hostel, block, and room selection** for every hosteler (onboarding and the raise-ticket form).
> 2. **Delete ticket** (safe soft-delete with audit trail).
> 3. **Dark mode** (Light / Dark / System).
> 4. **Full mobile usability** (phones are the main device for hostelers).
>
> Backend changes are allowed here. Rules carried over: logic in `services/`, permission checks in querysets, tokens-only styling, no new UI framework, no new dependency without asking, tests for every service.
>
> **Important:** from now on, every new or changed screen is built **mobile-first** (Section 5). Do not leave mobile for the end of a phase.

---

## 1. Decisions Made (defaults: change here if you disagree)

| # | Decision | Default |
|---|---|---|
| D1 | Residence = **Hostel → Block → Room**, all three required for hostelers. | Yes |
| D2 | Hostelers without a saved residence are **blocked** from everything except onboarding, logout, and theme until they complete it. | Yes |
| D3 | The raise-ticket form shows Hostel, Block, Room as **required**, prefilled from the hosteler's residence. Room and block can be changed freely within the same hostel (for example a common bathroom). Changing the hostel needs an explicit toggle ("This issue is in a different hostel") and is flagged to staff. | Yes |
| D4 | A short optional **"Location detail"** text (for example "2nd floor washroom") is available for issues not tied to a room. | Yes |
| D5 | Room capacity is **warn-only** by default ("This room already has 2 residents"). A setting `ENFORCE_ROOM_CAPACITY` can make it a hard block. | Warn only |
| D6 | Delete is a **soft delete**. Nothing is physically removed, so audit history, SLA stats, and notifications stay consistent. | Yes |
| D7 | A hosteler can delete **their own** ticket only while it is **Open or Assigned**, has **no reposts**, and has **no staff comment**. After that they can't delete it. | Yes |
| D8 | **Warden** (own hostel), **Chief Warden**, and **Admin** can delete any ticket in scope, with a **required reason**. Only **Admin** can restore, and only Admin can purge. | Yes |
| D9 | Deleted tickets are excluded from every list, Kanban, feed, dashboard count, SLA/escalation job, and search. Ticket numbers are never reused. | Yes |
| D10 | Theme options: **Light, Dark, System** (default System). Saved per user and mirrored in `localStorage` so the first paint is correct. | Yes |
| D11 | Mobile layout: bottom navigation, tables become card lists, filters become bottom sheets, Kanban becomes swipeable columns. No offline mode and no service worker in this phase. | Yes |

---

## 2. Feature A: Mandatory Hostel, Block & Room

### 2.1 Why
Routing, SLA, the community feed, and staff scope all depend on correct hostel and room data. Today residence comes from seed data; real users must set it themselves, and bad data must not get in.

### 2.2 Data model changes
- **`accounts.User`** (existing `hostel`, `room`): keep. Add `residence_set_at` (DateTime, null). Add property `has_residence`: role is Hostelers and `hostel` and `room` are set and `room.block.hostel == hostel`.
- **`accounts.ResidenceHistory`** (new): `user`, `hostel`, `room`, `changed_by`, `changed_at`. Written whenever residence changes (onboarding, profile edit, admin edit). Visible to Warden+.
- **`tickets.Ticket`** (existing `hostel`, `room`): both become **required** for new tickets (enforced in the form and service, not by a hard DB `NOT NULL`, because old rows may be incomplete). Add `location_detail` (CharField(120), blank) and `outside_own_hostel` (Bool, default False, set by the service when `ticket.hostel != reporter.hostel`).
- Existing hostelers with empty hostel or room are handled by the gate in 2.3.

### 2.3 Onboarding gate
- Middleware `RequireResidenceMiddleware`: for authenticated hostelers where `has_residence` is False, redirect every request to `/accounts/onboarding/`, except: `/accounts/onboarding/`, `/accounts/logout/`, `/accounts/theme/`, the dependent-options endpoints, static and media. HTMX requests get an `HX-Redirect` header instead of a body swap.
- **Onboarding page** (auth layout, centered card):
```
        Welcome, Arnov
        Tell us where you live so tickets reach the right person.

        Hostel   [ Select hostel          ▾ ]
        Block    [ Select block           ▾ ]   (disabled until hostel chosen)
        Room     [ Select room            ▾ ]   (disabled until block chosen)

        ⓘ Room 204 already has 2 residents.        (warn-only note)

        [            Save and continue            ]
```
- On save, the service `set_residence(user, hostel, block, room)` validates the chain, writes `ResidenceHistory`, and sets `residence_set_at`.
- **Profile page:** shows the residence card (Hostel · Block · Room) with a **Change** button that opens the same selector. Changes are logged. Existing tickets keep their original location snapshot.

### 2.4 Cascading selects (no new dependency)
- `GET /hostels/options/blocks/?hostel=<id>` returns `<option>` elements for active blocks. `GET /hostels/options/rooms/?block=<id>` returns `<option>` elements for rooms, with labels like `Room 204 · Floor 2`.
- HTMX: `hx-get` on the parent select, `hx-target` the child select, `hx-trigger="change"`. Clear and disable the child while loading. Use a loading indicator.
- On phones the selects stay **native** (best picker, no custom widget). On desktop they use the shared styled select. For blocks with many rooms, add a small filter input above the room select (client-side `Alpine` filter).
- Warn-only capacity note is returned with the room options (data attribute `data-residents`), shown by Alpine under the field.

### 2.5 Raise-ticket form changes
- New **Location** section (above Title): Hostel, Block, Room, and optional Location detail. Prefilled from the residence. A summary chip shows `Boys Hostel 1 · Block 2 · Room 204` once complete.
- Hostel is **locked** to the residence hostel. A switch "This issue is in a different hostel" unlocks it (D3). When unlocked, Block and Room reset and the helper text says "Staff in that hostel will receive this ticket."
- All three selects show an inline error if empty: "Select your room".
- **Server-side validation** (service `validate_location`): hostel, block, and room must exist, be active, and form a valid chain (`room.block.hostel == hostel`). A crafted POST with a mismatched room must be rejected with a form error. Admin creating a ticket on behalf of a hosteler must also choose the location.
- Staff views: add **Room** to the ticket list and detail; show an "Outside own hostel" chip when `outside_own_hostel` is true.
- Community feed: unchanged privacy rule (block shown, room never shown to other hostelers).

---

## 3. Feature B: Delete Ticket

### 3.1 Data model
Add to `tickets.Ticket`:

| Field | Type | Notes |
|---|---|---|
| `is_deleted` | Bool, default False, indexed | |
| `deleted_at` | DateTime, null | |
| `deleted_by` | FK User, null | |
| `delete_reason` | CharField(200), blank | Required when staff delete; optional for the reporter. |

- Managers: `Ticket.objects` returns **active only** (`is_deleted=False`); `Ticket.all_objects` returns everything (used by Admin trash, restore, and purge).
- `TicketActivity` actions: `DELETED`, `RESTORED`, `PURGED` (kept in a separate log table if the ticket row is purged).

### 3.2 Rules (service `tickets/services/deletion.py`)
- `can_delete(user, ticket)`:
  - Hosteler: reporter is the user, status in Open/Assigned, `repost_count == 0`, and no staff-authored comment.
  - Warden: ticket's hostel is the user's hostel. Chief Warden, Admin: any ticket.
  - Staff reason is mandatory (min 5 characters).
- `soft_delete(ticket, actor, reason)`: in a transaction, set the fields, remove the ticket from followers' pending notifications, write `DELETED` activity, notify the assignee ("Ticket HTL-… was deleted by the reporter" or "by the Warden: reason"), and notify reposters if any (staff delete only). A related announcement keeps its link but shows "Ticket removed".
- `restore(ticket, actor)`: Admin only. Clears the fields, recomputes `due_at` from `level_started_at`, writes `RESTORED`.
- `purge_deleted` management command: permanently removes tickets soft-deleted more than 90 days ago (Admin-run or scheduled). Prints a count. Never runs automatically without the flag `--confirm`.
- Escalation job, dashboard selectors, feed, Kanban, list, export CSV, search, and notifications all use `Ticket.objects`, so deleted tickets disappear everywhere. Add a test for each one.
- The ticket number is not reused (numbering sequence is global and unaffected).

### 3.3 URLs
| URL | Method | Who |
|---|---|---|
| `/tickets/<ticket_no>/delete/` | POST | Per `can_delete` |
| `/tickets/<ticket_no>/restore/` | POST | Admin |
| `/manage/trash/` | GET | Warden+ (own scope), Admin sees all |

### 3.4 UI
- **Entry points:** ticket detail action menu (`⋯` → "Delete ticket", danger color), the My tickets row menu on mobile, and the staff ticket detail. Hidden (not just disabled) when not allowed. When blocked by D7 (for example reposts exist), show a muted line instead: "Other hostelers have reposted this issue, so it can't be deleted. Ask your Warden to close it."
- **Hosteler confirm dialog:** "Delete this ticket? Staff will no longer see it. This can't be undone by you." Buttons: Cancel, Delete (danger). On success: toast "Ticket deleted" with an **Undo** link for 8 seconds (calls restore through a short-lived token allowed for the reporter only within those 8 seconds). The card or row is removed with `hx-swap="delete"`.
- **Staff confirm dialog:** adds a required **Reason** select (Duplicate, Spam or test, Raised by mistake, Inappropriate, Other) plus a text box for Other. Delete button stays disabled until a reason is given.
- **Mobile:** the confirm dialog is a bottom sheet with full-width buttons (see Section 5).
- **Trash page** (`/manage/trash/`): shared data table with Ticket · Title · Hostel · Deleted by · Reason · Deleted at · Restore (Admin). Empty state: "Nothing in the trash."

---

## 4. Feature C: Dark Mode

### 4.1 Behavior
- Options: **Light · Dark · System**. Control locations: segmented control in the avatar menu, a sun/moon icon button in the desktop top bar, and a row in the mobile "More" sheet. Also a small icon button on the login and onboarding pages.
- **Persistence:** add `User.theme` (choices `SYSTEM`, `LIGHT`, `DARK`, default `SYSTEM`). `POST /accounts/theme/` saves it (HTMX, no page reload). Logged-out pages and first paint use `localStorage`.
- **No flash on load:** an inline script at the very top of `<head>` reads `localStorage.theme` (or the server-rendered attribute for logged-in users) and sets `data-theme` on `<html>` before any CSS paints. For `SYSTEM`, it follows `prefers-color-scheme` and listens for changes.
- Set `color-scheme: light dark` and switch it with the theme so scrollbars, date pickers, and native selects match.
- Update `<meta name="theme-color">` on theme change (mobile browser chrome color).
- Briefly add a `theme-switching` class that disables transitions while swapping, to avoid a slow color wash.
- Dispatch a `themechange` event so Chart.js can rebuild with new colors.

### 4.2 Tokens
All dark values live in `tokens.css` under `:root[data-theme="dark"]`. **No component CSS may contain hard-coded colors**; any that are found during the audit are moved into tokens.

```css
:root[data-theme="dark"] {
  color-scheme: dark;

  /* Surfaces */
  --bg-app:        #0F1115;
  --bg-surface:    #161A20;
  --bg-subtle:     #1D222A;
  --surface-glass: rgba(22, 26, 32, 0.82);
  --border:        #272D37;
  --border-strong: #353C48;
  --border-soft:   rgba(255, 255, 255, 0.07);
  --border-hover:  rgba(255, 255, 255, 0.16);

  /* Text */
  --text-primary:   #E8EAED;
  --text-secondary: #A9B1BE;
  --text-muted:     #7D8696;

  /* Actions: the black primary button inverts so it stays visible */
  --primary:       #F2F4F7;
  --primary-text:  #11141A;
  --accent:        #4DA3FF;
  --ring:          0 0 0 3px rgba(77, 163, 255, 0.35);

  /* Status pills */
  --st-open-bg:      rgba(224, 62, 62, 0.16);   --st-open-fg:      #FF8A8A;
  --st-assigned-bg:  rgba(36, 144, 239, 0.16);  --st-assigned-fg:  #7DB8FF;
  --st-progress-bg:  rgba(240, 140, 0, 0.16);   --st-progress-fg:  #FFB454;
  --st-hold-bg:      rgba(140, 100, 220, 0.18); --st-hold-fg:      #C3A6FF;
  --st-resolved-bg:  rgba(52, 160, 107, 0.16);  --st-resolved-fg:  #5FD39A;
  --st-closed-bg:    rgba(255, 255, 255, 0.08); --st-closed-fg:    #A9B1BE;
  --st-escalated-bg: rgba(228, 70, 120, 0.16);  --st-escalated-fg: #FF8FB1;

  /* Kanban column tints (subtle) */
  --col-open:     rgba(224, 62, 62, 0.07);
  --col-assigned: rgba(36, 144, 239, 0.07);
  --col-progress: rgba(240, 140, 0, 0.07);
  --col-hold:     rgba(140, 100, 220, 0.08);
  --col-resolved: rgba(52, 160, 107, 0.07);

  /* Priority and criticality */
  --prio-urgent: #FF6B6B; --prio-high: #FFA94D; --prio-medium: #4DA3FF; --prio-low: #8A93A3;
  --crit-low: #8A93A3; --crit-med: #4DA3FF; --crit-high: #FFA94D; --crit-urgent: #FF6B6B;

  /* Announcement severities */
  --ann-info-bg: rgba(36, 144, 239, 0.16); --ann-info-fg: #7DB8FF;
  --ann-imp-bg:  rgba(240, 140, 0, 0.16);  --ann-imp-fg:  #FFB454;
  --ann-urg-bg:  rgba(224, 62, 62, 0.16);  --ann-urg-fg:  #FF8A8A;

  /* Background layer */
  --bg-base:        #0F1115;
  --bg-glow-accent: rgba(77, 163, 255, 0.12);
  --bg-glow-violet: rgba(140, 100, 220, 0.10);
  --bg-dot:         rgba(255, 255, 255, 0.06);
  --bg-line:        rgba(255, 255, 255, 0.03);

  /* Depth: dark UIs use borders and subtle highlights, not heavy shadows */
  --elev-1:   0 1px 0 rgba(255, 255, 255, 0.03) inset, 0 1px 2px rgba(0, 0, 0, 0.4);
  --elev-2:   0 1px 0 rgba(255, 255, 255, 0.04) inset, 0 8px 24px -8px rgba(0, 0, 0, 0.6);
  --elev-pop: 0 16px 40px -8px rgba(0, 0, 0, 0.7);
}
```

### 4.3 Component rules
- **Primary button:** in dark mode it is light-on-dark (token inversion above), so no per-component overrides.
- **Cards and tables:** use `--bg-surface` with `--border`; row hover uses `--bg-subtle`.
- **Charts:** a helper in `charts.js` reads colors from CSS variables (`getComputedStyle`) for series, gridlines, ticks, legend, and tooltip, and re-renders on the `themechange` event. Gridlines are low-contrast; series colors use the lighter dark-mode tokens.
- **Inputs:** background `--bg-subtle`, text `--text-primary`, autofill override uses the surface token (so browser autofill doesn't paint white or blue).
- **Images and uploads:** thumbnails get a 1px `--border` and keep their original colors. No filter inversion.
- **SVG icons** use `currentColor`.
- **Focus rings** use `--ring` so they stay visible on dark surfaces.
- **Contrast:** text and pill pairs meet WCAG AA in both themes (check with a script or the browser devtools; list any exceptions in `docs/theme-contrast.md`).
- **Guard test:** `tests/test_no_hardcoded_colors.py` scans `static/css/**` (except `tokens.css`) and `templates/**` for `#hex`, `rgb(`, `hsl(` and fails the build if it finds any (allow-list only for `currentColor`, `transparent`, and `inherit`).

---

## 5. Feature D: Mobile Usability

Target devices: iPhone SE to Pro Max, Android 360 to 430px wide, Safari iOS and Chrome Android. Build with `min-width` media queries (mobile-first). Breakpoints stay: `<768` phone, `768 to 1023` tablet, `>=1024` desktop.

### 5.1 Global rules
- `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`. Respect `env(safe-area-inset-*)` for the top bar, bottom nav, and sticky action bars.
- Use `100dvh` for full-height layouts (not `100vh`).
- **Touch targets at least 44×44px** (buttons, nav items, checkboxes, table row actions). Minimum 8px gap between adjacent targets.
- **Form inputs use `font-size: 16px` on phones**, which stops iOS from auto-zooming. Use correct `type`, `inputmode`, `autocomplete` (`username`, `current-password`), and `enterkeyhint`.
- **No hover-only features.** Wrap hover styles in `@media (hover: hover)`. Tooltips become tap-to-show or are replaced by visible text. Row actions are always visible on touch.
- No horizontal page scroll anywhere (`overflow-x: hidden` is not an allowed fix; fix the cause). Wide content scrolls inside its own container.
- Simplify the background on phones: no `backdrop-filter`, hide the dot grid, keep faint glows. Drop heavy shadows for borders.
- Fonts: `font-display: swap`; load only the Inter weights used (400, 500, 600, 650).
- Images: `loading="lazy"`, `decoding="async"`, explicit `width`/`height`.
- Respect `prefers-reduced-motion`.

### 5.2 Navigation
- **Bottom navigation bar** (fixed, 56px + safe area, blurred surface or solid):
  - Hosteler: **Home · Community · ＋ Raise (center, raised accent button) · News · More**
  - Staff: **Dashboard · Tickets · Kanban · Alerts · More**
  - Active item: accent icon + label + small top indicator. Badges for unread notifications and announcements.
- **More** opens a bottom sheet: Profile, residence, theme selector, Hostels/Staff/Routing (admin), Notifications, Log out.
- **Top bar (phone):** left = back arrow on inner pages (or logo on root pages), center = page title (truncated), right = search icon (opens a full-screen search sheet; the `⌘K` hint is hidden) and the bell. The avatar moves into **More**.
- The desktop sidebar is hidden on phones. Tablet keeps the narrow icon rail.

### 5.3 Pattern conversions (phone only)

| Desktop pattern | Phone pattern |
|---|---|
| Data tables | **Card list.** Each row becomes a card: title (2 lines), status pill, meta line (ID · hostel/room · time), priority dot, SLA text. Tap opens detail. Implement with a card partial rendered from the same context (preferred) or CSS table-to-card with `data-label`. |
| Filter sidebar | **"Filters" button** (shows active count) opening a **bottom sheet** with the selects and "Apply / Clear". Sort moves into the same sheet. |
| Modals and confirm dialogs | **Bottom sheets** with full-width buttons, drag handle, and swipe-down to close. |
| Dropdown menus (`⋯`, avatar) | **Action sheets** (bottom), large rows. |
| Kanban | **Swipeable columns**: horizontal `scroll-snap` at about 88vw per column plus a sticky **tab strip** of statuses with counts for quick jumping. Drag and drop works on touch with a 200ms long-press delay (`delayOnTouchOnly`), and each card has a **"Move to…"** action-sheet fallback for accessibility and reliability. |
| Dashboard | Stat cards in a 2×2 grid. Charts full width at about 220px height; legends under the chart; the wide monthly bar chart scrolls horizontally inside its card. Bottom widgets stack. |
| Ticket detail | One column. The "Details" card collapses into an accordion under the title. A **sticky bottom action bar** holds the main action (for example Change status, Comment). |
| Raise ticket form | One column in short sections (Location, Issue, Photos, Share). **Sticky bottom bar** with "Submit". Photo field offers **Take photo** and **Choose from gallery** (`accept="image/*"`, `capture` as a separate option). Optional client-side downscale of large photos with `canvas` before upload (no dependency). |
| Community feed | Full-width cards with a 12px gutter. Repost and Comment buttons are large and side by side. Comment input opens in a bottom sheet with the thread above it. Infinite scroll with a visible "Loading…" row. |
| Announcements | Cards full width; urgent banner is a compact sticky strip under the top bar with a tap-to-read action. |
| Admin forms and lists | Single column forms; lists as card lists; actions in an action sheet. Routing and SLA groups stay collapsible. |
| Notifications | Full page list (the bell opens the page on phones, not a dropdown). Tap marks read and opens the ticket. |
| Toasts | Above the bottom nav (`bottom: calc(56px + env(safe-area-inset-bottom) + 12px)`), full width minus 16px, swipe to dismiss. |

### 5.4 Performance and resilience
- Server-render the first page of every list. HTMX loads further pages (20 per page).
- Skeleton states and `htmx-indicator` on every swap. A friendly retry message on request failure ("Couldn't load. Tap to retry").
- Debounce search and the similar-issues check at 400ms.
- Add a `manifest.webmanifest` (name, icons 192/512, `display: standalone`, theme and background colors) and `<meta name="theme-color">`, so users can add the app to their home screen. **No service worker** in this phase.
- Budget: first meaningful render under 2.5s on a mid-range Android over throttled 4G; total CSS+JS under 300 KB gzipped (excluding vendor Chart.js, loaded only on chart pages).

### 5.5 Mobile acceptance tests (Playwright device emulation)
- Devices: iPhone SE (375×667), iPhone 13 (390×844), Pixel 7 (412×915), and landscape on one of them. Also 130% text zoom.
- Automated checks on every main page: `document.documentElement.scrollWidth <= window.innerWidth`; every interactive element has a bounding box of at least 44×44; inputs have computed font-size of at least 16px; no element is hidden behind the bottom nav (last content has bottom padding).
- Manual checks: raise a ticket with a photo, filter and sort the list, repost and comment in the feed, drag or "Move to…" in Kanban, delete a ticket with Undo, switch theme, onboard a new hosteler.
- Lighthouse mobile: Accessibility ≥ 90, Best Practices ≥ 90, Performance ≥ 80.

---

## 6. Data Model and URL Summary

**Migrations (in order):** (1) `User.residence_set_at`, `User.theme`, `ResidenceHistory`; (2) `Ticket.location_detail`, `outside_own_hostel`; (3) `Ticket` soft-delete fields plus manager changes; (4) activity/notification choices. Data migration: backfill `outside_own_hostel` as False and leave existing deleted flags False.

| URL | Purpose |
|---|---|
| `/accounts/onboarding/` | Residence gate |
| `/accounts/profile/residence/` | Change residence |
| `/accounts/theme/` (POST) | Save theme |
| `/hostels/options/blocks/`, `/hostels/options/rooms/` | Dependent option partials |
| `/tickets/<no>/delete/`, `/tickets/<no>/restore/` | Delete and restore |
| `/manage/trash/` | Deleted tickets |

**Permissions added:** delete (Section 3.2), restore (Admin), trash (Warden+), residence change history (Warden+).

---

## 7. Build Phases

### Phase M0: Setup
- [ ] Branch `feature/residence-delete-theme-mobile`.
- [ ] Add the hardcoded-color test and fix every violation by moving colors into `tokens.css`. This is required before dark mode.
- [ ] Add the Playwright mobile smoke suite (it should fail on the current app; that is the baseline).

### Phase M1: Residence (Feature A)
- [ ] Migrations, services (`set_residence`, `validate_location`), `ResidenceHistory`.
- [ ] Dependent option endpoints and partials.
- [ ] Onboarding page, middleware gate, profile residence card.
- [ ] Raise-ticket Location section with the different-hostel switch; staff Room column and "Outside own hostel" chip.
- **Done when:** a new hosteler cannot reach any page until residence is saved; a crafted POST with a mismatched room is rejected; tickets always have a valid hostel, block, and room.

### Phase M2: Delete ticket (Feature B)
- [ ] Soft-delete fields, managers, `deletion.py`, URLs, views, confirm dialogs, Undo toast, Trash page.
- [ ] Verify every query path uses `Ticket.objects`.
- **Done when:** a hosteler can delete an eligible ticket and undo within 8 seconds; ineligible cases show the explanation; Warden/Admin deletes require a reason; deleted tickets vanish from list, Kanban, feed, dashboard, search, CSV, and the escalation job; Admin can restore.

### Phase M3: Dark mode (Feature C)
- [ ] Dark tokens, the head script, `User.theme`, theme endpoint, toggle controls, `theme-color` meta, chart theming and re-render.
- [ ] Walk every screen in dark mode and fix any contrast or leftover light surfaces.
- **Done when:** no flash on load, preference persists across devices, every page and chart is readable in both themes, and the hardcoded-color test passes.

### Phase M4: Mobile (Feature D)
- [ ] Global rules (5.1), bottom nav and More sheet, mobile top bar.
- [ ] Card-list partials for ticket list, dashboard tables, admin tables, trash, recent tickets.
- [ ] Bottom-sheet component (filters, confirm dialogs, action sheets, comments).
- [ ] Kanban swipe columns, touch drag, "Move to…" fallback.
- [ ] Raise-ticket form and ticket detail mobile layouts, camera upload.
- [ ] Feed, announcements, notifications mobile layouts.
- [ ] Manifest and theme-color.
- **Done when:** the mobile acceptance tests in 5.5 pass at all listed sizes.

### Phase M5: Regression and release
- [ ] `python manage.py check`, the full test suite, and the Playwright suites pass.
- [ ] Manual pass as each role on a real phone (or device emulation) in both themes.
- [ ] Seed demo data includes hostelers with and without residence, deleted tickets, and a mix of theme preferences.
- [ ] Update README (residence rules, delete rules, theme, mobile support matrix).

---

## 8. Testing Plan

| Area | Tests |
|---|---|
| Residence | Gate redirects incomplete hostelers (and HTMX gets `HX-Redirect`); allowed paths work; chain validation rejects room from another hostel; blocked inactive hostels, blocks, and rooms; `ResidenceHistory` written; capacity warn-only, and the hard block when `ENFORCE_ROOM_CAPACITY=True`; the different-hostel switch sets `outside_own_hostel`. |
| Delete | Each D7 condition (status, reposts, staff comment, ownership) allowed or denied; Warden scope; reason required for staff; Undo token expires after 8 seconds and works only for the reporter; restore Admin-only; purge only with `--confirm` and the 90-day rule; deleted tickets absent from list, Kanban, feed, dashboard counts, CSV export, search, notifications, and escalation; activity log entries exist. |
| Theme | Saving persists; `SYSTEM` follows the media query; logged-out fallback uses `localStorage`; no inline color literals (guard test); charts rebuild on `themechange`. |
| Mobile | Playwright suite (no horizontal overflow, tap target size, input font size, bottom nav padding); filters sheet applies and clears; Kanban "Move to…" changes status; sticky submit bar visible with the keyboard open. |
| Regression | Existing tests, community feed, announcements, escalation, and status workflow remain green. |

---

## 9. Acceptance Checklist

**Residence**
- [ ] Hostelers must select Hostel, Block, and Room before using the app.
- [ ] Raise-ticket form requires all three, prefilled, with server-side chain validation.
- [ ] Staff see the room and an "Outside own hostel" flag.

**Delete**
- [ ] Hostelers can delete eligible own tickets with Undo; ineligible cases are explained.
- [ ] Warden, Chief Warden, and Admin can delete with a reason; Admin can restore.
- [ ] Deleted tickets are gone from every list, count, and job.

**Dark mode**
- [ ] Light, Dark, and System work, persist, and cause no flash.
- [ ] All screens, charts, pills, Kanban columns, and forms are readable (AA contrast).

**Mobile**
- [ ] Bottom navigation, card lists, bottom sheets, swipeable Kanban, and sticky action bars in place.
- [ ] No horizontal page scroll; 44px targets; 16px inputs; camera upload works.
- [ ] Lighthouse mobile targets met.

**Overall**
- [ ] No regressions; all tests pass; README updated.

---

## 10. Rules for the Agent
1. Build mobile-first from the start of this plan; check every screen at 375px before calling it done.
2. All colors come from tokens. The guard test must stay green.
3. Never hard-delete tickets from application code; use `soft_delete`.
4. Always query tickets through `Ticket.objects` unless the code is explicitly Admin trash, restore, or purge.
5. Validate hostel, block, and room on the server. Never trust the dropdowns.
6. Keep selects native on phones; do not build custom pickers there.
7. Logic stays in `services/`; views stay thin; every new service gets tests.
8. Do not add dependencies without asking. If a requirement here conflicts with the earlier plans, this document wins for these four features only.
9. Announce the phase at the start of each task and commit with `feat:`, `fix:`, `style:`, or `test:` prefixes after each phase.
