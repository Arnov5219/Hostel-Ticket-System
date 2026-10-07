# Hostel Ticket System: UI/UX Improvement Plan (v2)

> **For Antigravity.** This plan is based on 17 screenshots of the running app and **supersedes `UI_POLISH_PLAN.md`**. `ui-polish.css` can still be used as a starting draft for the background and card layer, but every item below comes from something actually visible in the current UI.
>
> **Work order:** Phase 0 → 9. Finish each phase's "Done when" checks before moving on. Commit after each phase with a `style:` or `fix:` prefix.

---

## 1. Hard Constraints (never violate)

- Do **not** change Django models, views' business logic, URLs, routing, auth, escalation, or database.
- No new UI framework (no React, Tailwind, Bootstrap, Material UI). Keep Django Templates + HTMX + Alpine.js + the existing custom CSS and Chart.js.
- Do not break any `hx-*` or `x-*` attribute, form field name, `{% url %}` target, CSRF token, or the `Ctrl/⌘ + K` shortcut.
- Allowed template edits: wrappers, class names, `data-*` attributes, presentational blocks (breadcrumb, page subtitle), and small presentational template filters (for example turning `IN_PROGRESS` into "In progress"). Nothing that changes what data is queried or saved.
- Colors, radii, shadows, and font sizes come from `tokens.css`. No inline styles. No color literals elsewhere.
- Chart changes are limited to Chart.js **options** (ticks, colors, bar thickness, tooltips), never to the data endpoints.
- If a fix needs a backend change, **do not do it**. Add it to `docs/backend-followups.md` and move on.

---

## 2. What the Screenshots Show

### 2.1 What already works (keep)
- ERPNext-style identity: white surfaces, thin borders, black primary button, blue logo tile, narrow icon sidebar, Inter font.
- Kanban pastel columns and compact ticket cards.
- Status/level/priority chips are consistent in concept.
- The black "segmented" tab for Routing Rules / SLA Policies / Categories / Tags is a good pattern.
- Page-level action buttons sit consistently at the top right.

### 2.2 Problems found (prioritized)

**P0: Bugs that look broken**

| ID | Screen | Problem | Fix |
|---|---|---|---|
| B-01 | Hosteler "My Helpdesk" | The *Recent Tickets* table is broken: headers are bold and larger than other tables, columns are squeezed to the left and misaligned, "Cleaning / Housekeeping" wraps, and more than half the card is empty. It is not using the shared table component. | Use the same `.data-table` markup and styles as the Ticket List; give it the full width and proper column sizing. |
| B-02 | Hostels Management (admin) | Sidebar tooltip ("Dashboard") renders over the page title, far from the icon it belongs to. | Anchor tooltips to their own icon (`position: absolute` inside a `position: relative` item, or fixed with computed coordinates). Show only on hover/focus. Make sure no parent `overflow: hidden` clips or displaces it. |
| B-03 | Hostels Management | "Total rooms" shows `10 10` instead of `10` (the value is printed twice). | Fix the template so the value is output once. |
| B-04 | Login page | The full app shell (sidebar with Dashboard/Tickets/Notifications icons, "Home" breadcrumb, search bar, "Raise Ticket" button) shows to someone who is **not signed in**. | Use a bare auth layout: no sidebar, no search, no Raise Ticket. Only the card on the background. |
| B-05 | Dashboard | Charts show decimal Y-axis ticks (`0.1, 0.2 … 1.0`) for counts. Counts must be whole numbers. | Chart.js: `scales.y.ticks.precision = 0`, `beginAtZero`, `stepSize` auto-integer. |
| B-06 | Notifications | Raw enum text shown to users: "Status: IN_PROGRESS", "changed status to CLOSED". | Presentational filter to humanize (`In progress`, `Closed`). |
| B-07 | Kanban | "just now left" is wrong copy. Resolved cards still show "5d left" SLA countdowns, which make no sense for finished tickets. | Show "Due in 3h", "Due now", "Overdue 2d" for active tickets; "Resolved 2d ago" for resolved ones. |
| B-08 | Hosteler dashboard | Two buttons do the same thing: **Raise Ticket** (header) and **New Complaint** (welcome strip). | One primary CTA per page (see 5.4). |
| B-09 | Toasts | The dark toast ("Welcome back…") sits on top of page content at the bottom right and covers data (for example the Critical Overdue list). | Toast stack: auto-dismiss in 4s, dismiss on click, `pointer-events` only on the toast, offset from corner, never overlapping the page's primary actions. |

**P1: UX and hierarchy**

| ID | Problem |
|---|---|
| U-01 | **Page titles are tiny** (about 14px). Hierarchy between title, card title, and table text is weak. |
| U-02 | **Breadcrumb always says only "Home"** on every page. It tells the user nothing. |
| U-03 | **Wide screens stretch tables edge to edge** (Rooms, Routing, Staff). Columns end up 400px apart and rows are hard to scan. |
| U-04 | **Large empty gray areas** under short tables (Hostel Responsibility, Staff, Hostels, Notifications, Hosteler home). Pages feel unfinished. |
| U-05 | **ALL-CAPS 11px table headers** with wide tracking are hard to read and heavy. ERPNext itself uses sentence case. |
| U-06 | **Native `<select>` controls** in the Ticket List filter sidebar and sort control (big, default OS chevrons, inconsistent with the rest of the UI). |
| U-07 | **Ticket List: SLA bar is green for closed/resolved tickets**, so it carries no information. Ticket IDs are tiny (about 9px) monospace and unreadable. |
| U-08 | **Avatars are plain letters** ("CA", "WA", "AD") with no circle, so people look like text labels. |
| U-09 | **Admin pages are an unconnected set of screens.** Each page has different ad-hoc buttons at the top (Hostels / Staff Management / Hostel Responsibility / Blocks / Rooms). There is no consistent admin navigation. |
| U-10 | **Routing & SLA lists 27 near-identical rows** (3 hostels × 9 categories) with a red trash icon on every row. High noise, high risk of accidental delete. |
| U-11 | **Destructive actions are loud**: red "Deactivate" text on every Staff row, red trash on every Routing row. |
| U-12 | **Staff "Active tickets" numbers use brown/orange** text, which looks like a warning even when the count is normal. |
| U-13 | **Dashboard charts are visually heavy**: huge solid brown (Tickets by Category) and purple (Avg Resolution) bars, extremely wide, with nothing to anchor them. Brown is the "In progress" status color reused as a category color. |
| U-14 | **Sidebar has 8+ icons in one flat list** with no grouping, and no labels unless hovering. |
| U-15 | **Notifications card is narrow and left-aligned** with the rest of the page empty. No icon per event type. |
| U-16 | **Kanban**: no filter bar (hostel, category, assignee), unassigned cards show a "?" avatar, columns don't use the available width on large screens. |
| U-17 | **Rooms Management** has no row actions, no search, no pagination, no filter. 100+ rooms in one scroll. |
| U-18 | **Login**: browser autofill paints the inputs a hard blue; the "Quick demo fill" block is always shown. |

**P2: Data and copy issues (not UI bugs, report only)**
- Hostel names differ between screens ("Boys Hostel 1/2", "Girls Hostel 1" vs "Boys Hostel A", "Girls Hostel B"). "Boys Hostel A" appears twice with different codes (`HOSTEL_A`, `BH-A`).
- "Dr. Ramesh Verma" appears twice with different usernames (`warden_a`, `warden_bha`).
- Record these in `docs/backend-followups.md`. They come from seed data, not from the UI.

---

## 3. Design Direction

**Product feel:** calm, dense, professional. A university-grade helpdesk. ERPNext/Linear-like, not a marketing page.

**One memorable thing:** the layered background plus quiet cards. Everything else stays disciplined.

### 3.1 Typography (Inter)
| Role | Size / weight |
|---|---|
| Page title | 20px / 650 |
| Page subtitle | 13px / 400, muted |
| Card / section title | 14px / 600 |
| Table header | 12px / 600, **sentence case**, no tracking |
| Body / table cell | 13px / 400 |
| Metadata | 11.5 to 12px, muted |
| Stat numbers | 26 to 28px / 650, tabular numerals |
| IDs (ticket no., usernames) | 12px, `font-variant-numeric: tabular-nums` (monospace optional but never below 12px) |

### 3.2 Color balance
About 75% neutral/white · 15% gray · 8% blue accent · 2% status colors. No rainbow. Status colors stay: Open red · Assigned blue · In Progress orange · On Hold purple · Resolved green · Closed gray · Escalated pink.
**Do not reuse status colors as category colors** (the brown bars are the example of what not to do).

### 3.3 Layout rules
- **Page container:** management, notifications, detail, and form pages use `max-width: 1200px`, left-aligned with the page header. List, Kanban, and Dashboard use full width.
- **Page header:** 64px tall, title 20px, optional one-line subtitle under it, actions at the right.
- **Real breadcrumbs:** `Administration / Hostels`, `Tickets / HTL-2026-00061`, `Dashboard`. Provide a `{% block breadcrumb %}` in `base.html`; each page fills it.
- **Spacing scale:** 4 / 8 / 12 / 16 / 24 / 32. Cards padded 16px; page gutter 24px (16px on mobile).

### 3.4 Background and depth (reusable layer)
One fixed `.app-background` element as the first child of `<body>`:
1. Off-white base.
2. Very faint dot grid and thin diagonal lines, masked so they fade toward the center.
3. Two very soft glows (blue top-left, violet bottom-right).
4. Cards: white at about 86% opacity (solid fallback without `backdrop-filter`), 1px soft border, layered shadow, 12px radius.

Rules: opacity very low, no animation, no images, never reduces text contrast. This directly addresses U-04.

---

## 4. Shared Components (build once, reuse everywhere)

Create or update in `components.css` with partials in `templates/components/`.

| Component | Spec |
|---|---|
| **Page header** | Breadcrumb in the top bar, title + subtitle, right-aligned actions. |
| **Admin sub-navigation** (U-09) | Segmented tabs under the page header for all admin pages: **Hostels · Blocks · Rooms · Staff · Responsibility · Routing & SLA**. Same black-active-pill style as the existing Routing tabs. Replaces the ad-hoc button clusters. Shown only to roles that can access those pages. |
| **Data table** | Header 12px sentence case on a faint gray band; rows 44 to 46px; hairline row dividers only; hover tint; tabular numerals; numeric columns right-aligned; sticky header; footer with count and pagination. Column widths set so no column is wider than needed (Title flexes, the rest are fixed). |
| **Avatar** (U-08) | 28px circle, initials, soft tinted background chosen from a small neutral/blue token palette by hashing the name (consistent per person). Optional 24px size for tables, 20px for Kanban. Unassigned = dashed circle with a user-plus icon and tooltip "Unassigned". |
| **Status pill** | Keep colors; add a 6px leading dot; 11.5px, 18px line height. |
| **Level chip** | `L1` blue, `L2` amber, `L3` orange, `L4` red-pink, all 11px with the same shape. Used in the table, Kanban, Staff, Routing, and Dashboard. |
| **Priority marker** | Dot + label (Urgent red, High orange, Medium blue, Low gray). |
| **SLA indicator** (U-07) | Active tickets: thin bar plus text on hover ("5h left"), bar color green → amber → red as time runs out. Resolved/Closed: a muted check icon and "Met" or "Breached"; **no bar**. |
| **Select** (U-06) | Styled `appearance: none` select, 32px high, 13px, custom chevron, same border and focus ring as inputs. Applies to every native select in the app. |
| **Input / search** | 32 to 34px high, `--bg-subtle` fill, blue focus ring. Autofill override (U-18): `:-webkit-autofill { box-shadow: 0 0 0 100px var(--surface) inset; }`. |
| **Buttons** | Primary (black), Secondary (white, 1px border), Ghost, **Danger-ghost** (muted until hover, then red text on a faint red tint). Sizes sm (28px) and md (34px). |
| **Row actions** (U-11) | Icon or text actions at 55% opacity, 100% on row hover. Destructive actions never red by default. Keep any existing confirm step. |
| **Empty state** | Small line icon, one-sentence explanation, one primary action. For example "No tickets match these filters. Clear filters". |
| **Toast** (B-09) | Bottom-right stack, 4s auto-dismiss, close button, `role="status"`, slide-up 200ms, offset 24px, max 3 stacked. |
| **Tooltip** (B-02) | One CSS tooltip pattern (`data-tooltip`), anchored to the trigger, 120ms fade. |
| **Stat card** | Label (12px, sentence case) · value (28px) · hint (11.5px) · optional 28px icon chip · thin accent rule. Only the value takes a status color. |
| **Info callout** | One style: faint blue tint, 1px border, small info icon, 13px text. Used for the "Level 1 Hostel Responsibility Model" note. |

---

## 5. Screen-by-Screen Specification

### 5.1 Global shell
- **Sidebar (stays 56px).** Group with hairline dividers:
  1. Dashboard · Tickets · Kanban
  2. *(admin only)* Hostels · Staff · Responsibility · Routing & SLA
  3. Notifications
  4. *(bottom)* Profile
  - Active: white chip, blue icon, 3px left indicator. Hover: tinted background and 1px icon nudge. Labels appear as tooltips (B-02 fix).
- **Top bar.** Breadcrumb (left) · command-style search with `⌘K` badge · notification bell with unread dot · avatar with ring. Add a user-menu dropdown (name, role, hostel, Profile, Log out) using the existing logout link.
- **Role hint.** Small role label under or next to the avatar on desktop ("Chief Warden"), hidden on mobile.
- **Toasts, tooltips, focus rings** per section 4.

### 5.2 Login (B-04, U-18)
```
            [ soft background, no sidebar, no top bar ]

                    ┌───────────────────────┐
                    │          [H]          │
                    │  Hostel Ticket System │
                    │  Sign in with Roll No │
                    │  or Employee ID       │
                    │  [ Roll No / ID     ] │
                    │  [ Password      👁 ] │
                    │  [      Sign in     ] │
                    │  ─────────────────    │
                    │  Demo accounts  ▾     │
                    └───────────────────────┘
```
- Auth layout without the app shell.
- Show/hide password toggle (Alpine, no backend).
- Fix autofill color.
- "Quick demo fill" becomes a collapsed "Demo accounts" disclosure. Recommend showing it only in demo/dev; if that needs `settings.DEBUG` in the template context, add it to `backend-followups.md` instead of changing settings.
- Subtle glow behind the card; card 12px radius with soft shadow.

### 5.3 Staff Dashboard (Operational Dashboard)
- **Title** 20px with subtitle "Live ticket health across your hostels". Right side: **Tickets** and **Kanban** as secondary buttons (unchanged).
- **Stat cards (4):** Created this month · Resolved · Open / in progress · Overdue SLA breaches. Sentence-case labels, 28px numbers, hint lines kept, icon chips. Overdue shows red only when above zero.
- **Chart cards:**
  - Header: title 14px, subtitle muted, right-aligned small controls area (kept even if empty so alignment is stable).
  - **B-05:** integer ticks only.
  - **Created / Resolved / Overdue:** blue `--accent`, green, red. Bars rounded (4px top), `maxBarThickness: 36`, `categoryPercentage` about 0.7, light dashed gridlines, legend with round markers, styled tooltip (white, border, shadow).
  - **Tickets by Category (U-13):** single muted blue-slate series, **not brown**. Horizontal bars if more than 5 categories. `maxBarThickness: 40`.
  - **Avg Resolution Time:** single muted indigo/slate series, value labels above bars, unit "h" on the axis.
  - Chart height capped (about 280px). Empty-data state: "No data for this period yet".
- **Bottom row (Escalation tiers · Top staff resolvers · Critical overdue):**
  - Escalation tiers: shared level chips with right-aligned counts.
  - Top resolvers: circular avatars, name, role, "N resolved".
  - Critical overdue: white rows with a 3px red left edge, ticket ID + title, a right-aligned "Overdue 2d" text. Drop the full-pink fill.
- Toast must not cover these cards (B-09).

### 5.4 Hosteler "My Helpdesk" (B-01, B-08)
```
┌──────────────────────────────────────────────────────────────┐
│ (AR) Welcome, Arnov                         [ + Raise ticket ]│
│      Boys Hostel 1 · Room — · student1                        │
│      [subtle corner glow + faint ring shape]                  │
└──────────────────────────────────────────────────────────────┘
┌────────────┐ ┌────────────┐ ┌────────────┐
│ In progress│ │ Resolved   │ │ Closed     │   ← clickable cards
│ 0          │ │ 0          │ │ 1          │     (link to filtered list)
└────────────┘ └────────────┘ └────────────┘
Recent tickets                                      [View all →]
┌──────────────────────────────────────────────────────────────┐
│ Ticket   Title      Category        Priority  Status  Assigned│
│ HTL-…    bulb       Cleaning / …    ● Medium  Closed  Mukesh  │
└──────────────────────────────────────────────────────────────┘
```
- **One primary CTA:** "Raise ticket" lives in the welcome panel (largest). Hide the duplicate header button on this page; remove "New Complaint" wording (use the same label everywhere: **Raise ticket**).
- Welcome panel: avatar, name, hostel, roll/ID as plain meta line (not boxed), glow and ring decoration.
- Stat cards: icon chips; link to `tickets/?status=…` (plain links).
- **Recent tickets table:** uses the shared Data table. Columns: Ticket · Title (flex) · Category (no wrap, ellipsis) · Priority · Status · Assigned to · Raised. Full width. Row click opens the ticket.
- Empty state when zero tickets: "You have not raised any tickets. Raise ticket".
- Optional (frontend-only): if the hosteler has an active ticket, a 4-step tracker (Open → Assigned → In progress → Resolved) above the table, driven by the existing status value.

### 5.5 Ticket List (U-06, U-07)
- Header: title "Tickets" + subtitle "61 total" (remove the floating "61 total" chip), actions: Kanban view, Export CSV, refresh.
- **Filter sidebar:** 220px, sticky, styled selects, "Clear all" link, an active-filter count badge. Collapsible to a drawer under 1024px. Hosteler role: show only Status and Category if the current markup already limits it; otherwise leave the set unchanged.
- **Active filter chips** row above the table (for example `Status: Open ×`). Frontend-only, derived from the current query string.
- **Table:** shared Data table. Column order and widths: checkbox (36) · Title (flex, truncate, tooltip) · Status · Category (icon + text, no wrap) · Priority · Hostel · Level · SLA · Ticket ID (12px, tabular) · Updated · Comments.
- **Category icons:** keep per-category icons if they differ in the data; if every category shares one sparkle icon, use neutral Lucide icons per category (bolt, droplet, wifi, broom, sofa, utensils, shield, wrench).
- **SLA:** per section 4 (no bar for Resolved/Closed).
- **Footer:** "Showing 1 to 20 of 61" plus pagination controls using the existing pagination partial.
- Bulk-action bar appears on selection (existing behavior, restyled as a floating bar).

### 5.6 Kanban (U-16, B-07)
- Header: title "Kanban" with subtitle, **filter bar** (Hostel, Category, Assigned to using the shared select; search), **List view** button, Raise ticket button for roles that already have it. Filters are visual only if the current view does not support server-side filtering. In that case hide cards client-side with Alpine, and keep the data as it is.
- **Columns:** `flex: 1 1 280px; min-width: 260px` so five columns fill wide screens. Column header: dot, name, count badge, `⋯`. Keep pastel tints, slightly lighter.
- **Cards:** ID (12px) and priority on the first line · title (2-line clamp) · location line · footer with avatar, time text, level chip.
  - Time text: "Due in 5d", "Due in 3h", "Due now", "Overdue 2d" (red). Resolved column: "Resolved 2d ago", no countdown.
  - Unassigned: dashed avatar (not "?").
  - Hover: 1px lift and a stronger shadow. Drag state: slight tilt-free shadow and dashed drop-zone highlight in the target column.
- Inner column scrollbars: slim, only visible on hover.
- SortableJS and the HTMX move request are untouched.

### 5.7 Notifications (B-06, U-15)
- Container `max-width: 760px`, centered under the header. Header: title and "Mark all as read" button (unchanged behavior).
- Each item: small round icon by event (status change, assignment, escalation, comment), bold title, one-line message, relative time on the right, "View ticket" as a quiet link button. Unread: faint blue tint and a 3px blue left edge; read: normal.
- Humanize: "Status changed to In progress", "Ticket HTL-2026-00061 is now Closed".
- Empty state: "You are all caught up."

### 5.8 Staff Management (U-08, U-11, U-12)
- Page header with admin sub-navigation; action buttons only where an action exists.
- Table columns: Name (avatar + name + username in muted tabular text) · Role · Level (chip) · Assigned hostel · Active tickets · Status · Actions.
- **Active tickets:** neutral text for normal values; amber text with a small dot above a threshold token (for example 6 or more); never brown for all values.
- **Actions:** "Assign hostel" as a ghost button with icon; "Deactivate" as danger-ghost (muted until hover). Keep the existing confirmation step.
- Optional (frontend-only): search box and role tabs (All · Caretakers · Wardens · Admin) above the table, filtering rows with Alpine.
- Row of "All hostels (campus-wide)" shown in italic muted text (already done; keep).

### 5.9 Hostel Responsibility
- Replace the large banner with the shared **Info callout** (one or two lines).
- Table: Hostel (name + code and type in muted text) · Level 1 responsible staff (avatar + name + username) · Status · Action. "Change staff" is a small secondary button.
- Container `max-width: 1200px`, which removes the stretched columns.

### 5.10 Hostels, Blocks, Rooms (B-03, U-17)
- **Hostels:** fix `10 10` (B-03). Add row actions (Edit, Change staff, Deactivate) in the same pattern as Staff. Code in a small neutral chip.
- **Rooms:** `max-width: 1200px`; add row actions if the existing routes provide them; otherwise skip. Add a **search input and hostel/block filters** (frontend filter via Alpine or existing query params if present). Add pagination or "Load more" if the template can paginate without backend changes; otherwise report it in `backend-followups.md`. Group by Block using sticky sub-headers ("Block 1", "Block 2") only if the markup allows it without restructuring the data.
- **Blocks:** apply the same table and header treatment (not in the screenshots; inspect first).

### 5.11 Routing & SLA (U-10, U-11)
```
Routing rules  |  SLA policies  |  Categories  |  Tags            [+ Add routing rule]

Assignment order:  ① Hostel + Category → ② Hostel only → ③ Hostel L1 default → ④ Warden fallback

▾ Boys Hostel 2   · Mukesh Kumar (L1) · 9 rules
   Category            Level   Assignee                     
   Cleaning/Housekeeping  L1   Mukesh Kumar                  (🗑 on hover)
   ...
▸ Girls Hostel 1  · Anita Devi (L1) · 9 rules
```
- Show the "order of assignment" as an inline 4-step flow (real sequence, so numbering is justified) instead of tiny gray text.
- **Group rows by hostel** with collapsible sections (`<details>` or Alpine). Default: first group open, the rest collapsed. The groups come from the existing row data in the template via `{% regroup %}`, which is presentational and needs no view change. If `{% regroup %}` is not possible because of the queryset order, group client-side by the Hostel cell text.
- The delete icon appears on row hover only, keeps its existing confirm/HTMX behavior.
- The other tabs (SLA Policies, Categories, Tags) use the same Data table and Empty state.

### 5.12 Ticket Detail, Raise Ticket, Profile, 403/404/500 (not in screenshots)
Inspect these first (Phase 0), then apply the shared system:
- **Detail:** two columns: main (title, status pill, description, attachments, tabs Comments / Internal notes / History) and a right "Ticket details" card (reporter, hostel/room, category, priority, assigned to with level chip, SLA indicator, escalation path L1 → L4 with the current level highlighted). Action bar uses Primary / Secondary / Danger-ghost buttons.
- **Raise ticket:** centered form card (`max-width: 640px`), styled selects, segmented priority control, drag-and-drop attachment zone with thumbnails.
- **Error pages:** bare auth layout, large muted status code, one sentence, one button.

---

## 6. Interaction and Motion

| Where | Behavior |
|---|---|
| Cards | 160ms border and shadow change on hover |
| Table rows | 120ms background tint |
| Sidebar items | 120ms background, 1px icon nudge, tooltip fade |
| Buttons | 120ms color/shadow; primary lifts 0.5px on active |
| Dropdowns / popovers | 160ms pop-in (opacity and 4px translate) |
| Toasts | 200ms slide-up |
| Charts | one 220ms fade-in on first render |
| Skeletons | While HTMX swaps the table or charts, show 3 to 5 shimmer rows (only if the swap target is easy to hook; otherwise use `htmx-indicator`) |

No bouncing, no continuous background motion. `prefers-reduced-motion` disables all of the above except opacity changes.

---

## 7. Responsive and Accessibility

- Verify at 1440, 1024, 768, 375px. Keep the existing breakpoints and navigation behavior (compact sidebar on desktop, reduced on tablet, bottom bar on mobile).
- Below 1024px: filter sidebar becomes a drawer; Kanban scrolls horizontally with snap; stat cards become a 2×2 grid; admin sub-navigation scrolls horizontally.
- Tables scroll horizontally inside their own container; the first column stays sticky where practical.
- Hide the dot grid on small screens; keep the glows at lower opacity.
- Visible 2px focus ring on every interactive element; icon-only buttons get `aria-label`; tooltips also appear on keyboard focus.
- WCAG AA contrast for pill text on pill backgrounds and for text on translucent cards.
- Toasts and notification counts use `aria-live="polite"`.

---

## 8. Build Phases

### Phase 0: Audit and branch
- [ ] Create branch `ui/v2`. Do not touch Python files except to add `docs/`.
- [ ] Write `docs/ui-audit.md`: a table of *element → current selector → file* for every item in sections 4 and 5. Include the pages not in the screenshots (detail, raise ticket, profile, blocks, SLA/Categories/Tags tabs, error pages).
- [ ] Create `docs/backend-followups.md` and add the P2 data issues from section 2.2.
- **Done when:** both docs exist, no code changes.

### Phase 1: Foundations
- [ ] Extend `tokens.css` with the background, border, elevation, radius, motion, and type-scale tokens.
- [ ] Add `.app-background` to `base.html` and the layer CSS.
- [ ] Page container classes (`.page`, `.page--narrow` at 1200px, `.page--full`) and the 64px page header.
- [ ] `{% block breadcrumb %}` plus per-page breadcrumb text (U-02).
- [ ] Tooltip pattern and fix B-02. Toast stack and fix B-09.
- **Done when:** every page shows the new background, real breadcrumbs, correct tooltips, and non-overlapping toasts.

### Phase 2: Shared components
- [ ] Data table, avatar, status pill, level chip, priority marker, SLA indicator, select, input, buttons (including danger-ghost), row actions, empty state, stat card, info callout, admin sub-navigation, segmented tabs.
- [ ] Add the small presentational template filters (`humanize_status`, `time_label`) in `core/templatetags/ui.py`.
- **Done when:** a temporary `/ui-kit/` page (dev only) shows every component and states (hover, focus, disabled, empty). Remove or restrict it in Phase 9.

### Phase 3: Auth layout
- [ ] Auth base layout without the app shell (B-04). Redesign login. Autofill fix, show/hide password, collapsed demo accounts. Apply the same layout to 403/404/500.
- **Done when:** a signed-out user sees no sidebar or search, and login still works for all five roles.

### Phase 4: Hosteler experience
- [ ] Rebuild the "My Helpdesk" markup using shared components (B-01, B-08).
- [ ] Ticket List for hosteler with styled filters and the shared table.
- [ ] Raise ticket form and ticket detail styling.
- **Done when:** no duplicated CTA, the recent tickets table aligns with the Ticket List table, and an empty-state hosteler looks intentional.

### Phase 5: Staff core
- [ ] Dashboard: stat cards, Chart.js options (B-05, U-13), bottom row restyle.
- [ ] Ticket List: filter sidebar, chips, SLA indicator, footer pagination (U-06, U-07).
- [ ] Kanban: filter bar, flexible columns, card copy and states (B-07, U-16).
- **Done when:** charts show integer ticks and no brown; the list shows no green bars on closed tickets; the Kanban fills wide screens; drag and drop still works.

### Phase 6: Admin area
- [ ] Admin sub-navigation across Hostels, Blocks, Rooms, Staff, Responsibility, Routing & SLA (U-09).
- [ ] Staff, Responsibility, Hostels (fix B-03), Rooms, Routing (grouped, U-10) per sections 5.8 to 5.11.
- **Done when:** all admin pages share the same header, tabs, table, and action patterns, and destructive actions are quiet by default.

### Phase 7: Notifications
- [ ] Humanized copy, event icons, centered narrow layout, unread styling, empty state (B-06, U-15).

### Phase 8: Responsive, accessibility, polish
- [ ] Run the checks in section 7 at all four widths.
- [ ] Add skeleton/indicator states, reduced-motion support, and focus audit.

### Phase 9: Regression and release
- [ ] `python manage.py check` and the full test suite pass. `git diff --stat` shows **no changes to models, views logic, URLs, or migrations**.
- [ ] Click through as each role (Hosteler, Caretaker, Warden, Chief Warden, Admin): login, raise ticket, list filter and sort, Kanban drag, ticket detail actions, escalate, comment, notifications, dashboard, every admin page, logout.
- [ ] Confirm HTMX swaps keep styling, and the `⌘K` search still opens.
- [ ] Remove `/ui-kit/`, unused CSS, and duplicate rules. Confirm no inline styles and no color literals outside `tokens.css`.
- [ ] Update `docs/ui-audit.md` with "what changed" and list any leftover items in `backend-followups.md`.

---

## 9. Acceptance Checklist

**Bugs fixed**
- [ ] B-01 Recent tickets table aligned and full width
- [ ] B-02 Tooltip anchored to its icon
- [ ] B-03 "10 10" shows "10"
- [ ] B-04 Login has no app shell
- [ ] B-05 Whole-number chart ticks
- [ ] B-06 No raw enum text in notifications
- [ ] B-07 Correct due/resolved copy on Kanban
- [ ] B-08 One primary CTA on the hosteler home
- [ ] B-09 Toasts never cover content

**Quality bar**
- [ ] Every page has the layered background and a real breadcrumb.
- [ ] Page titles at 20px; table headers sentence case; IDs at 12px or larger.
- [ ] Management pages capped at 1200px; list, Kanban, and dashboard full width.
- [ ] Shared components used everywhere (no one-off tables or buttons).
- [ ] Destructive actions are quiet until hover and keep their confirmation.
- [ ] Charts use blue/green/red and neutral single-series colors, never status colors as categories.
- [ ] No backend, URL, HTMX, or Alpine behavior changed; tests pass.
- [ ] Looks right at 1440, 1024, 768, and 375px.

---

## 10. Agent Rules

1. Announce the phase at the start of each task and summarize what changed at the end.
2. Inspect before editing. Never assume a class name; use `docs/ui-audit.md`.
3. Smallest change that achieves the result. Do not rewrite working components.
4. Reference issue IDs (`B-03`, `U-10`) in commit messages.
5. If a goal needs a backend change, stop and log it in `docs/backend-followups.md`.
6. Do not add dependencies. Lucide icons and Chart.js are already available.
7. If something looks heavy, reduce opacity, blur, or size. The right result is subtle.
