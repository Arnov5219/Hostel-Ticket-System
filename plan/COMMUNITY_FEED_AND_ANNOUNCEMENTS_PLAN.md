# Hostel Ticket System: Community Feed, Reposts & Announcements

> **For Antigravity.** This is a **feature addendum** to `HOSTEL_TICKET_SYSTEM_PLAN.md` and `UI_UX_IMPROVEMENT_PLAN.md`. It adds two things to the hosteler experience:
>
> 1. **Community feed:** hostelers see recent issues raised by other hostelers in their hostel, can **repost** ("I'm facing this too"), and can **comment**. **More reposts = a more critical issue**, which automatically raises priority and shortens the SLA.
> 2. **Announcements:** higher authorities (Warden, Chief Warden, Admin) can **publish news** to hostelers.
>
> **Unlike the UI plans, this one DOES change backend** (models, services, views, URLs). Everything else from the earlier plans still applies: service-layer logic, permission checks in querysets, no new UI frameworks, tokens-only styling, tests for every service.
>
> **Build order:** do this **after Phase 2 (shared components)** of `UI_UX_IMPROVEMENT_PLAN.md`, so the feed and announcement screens reuse the new table, pill, avatar, chip, toast, and empty-state components.

---

## 1. Decisions Made (defaults: change here if you disagree)

| # | Decision | Default | Why |
|---|---|---|---|
| D1 | A repost **does not create a new ticket.** It attaches the reposter to the original ticket. | Yes | Prevents 20 duplicate tickets for one broken water pump, and gives one clean `repost_count`. |
| D2 | Button label | **Repost** (tooltip: "I'm facing this too") | Matches your wording; the tooltip explains it. |
| D3 | Feed scope | **Same hostel only** | A hosteler in Girls Hostel 1 cannot see or repost issues of Boys Hostel 2. Configurable later. |
| D4 | Who sees a ticket in the feed | Only tickets the reporter marked **"Share with my hostel"**. Categories flagged *sensitive* (Security, Other) are **always private**. | Complaints can be personal or safety related. |
| D5 | Reporter identity in the feed | **Hidden by default**: shown as "A hosteler · Block 2". Room number is never shown to other hostelers. Reporter can opt in to show their name. Staff always see real identities. | Reduces social friction and retaliation risk. |
| D6 | Commenter identity | **First name + last initial** ("Arnov R."). Staff always see full identity. | Accountability and moderation. |
| D7 | Who can repost | Hostelers of the same hostel, **once per ticket**, not on their own ticket, only while the ticket is active (Open, Assigned, In Progress, On Hold). | Anti-abuse. |
| D8 | Criticality | Priority is auto-raised by repost thresholds (Section 4.3). Never auto-lowered below what staff set. | "More reposts, more critical". |
| D9 | Who can publish announcements | **Warden** (own hostel only), **Chief Warden** (any hostel or all), **Admin** (all). Caretakers cannot. | "Higher authority". |
| D10 | Announcement format | Plain text with line breaks and auto-linked URLs. **No rich-text editor, no new dependency.** | Keeps it safe and simple. |
| D11 | Staff in the community | Staff can read all feed posts in their scope and post comments tagged with a role badge ("Caretaker", "Warden") as **official replies**. | Transparency; fewer "any update?" repeats. |

---

## 2. User Stories

**Hosteler**
- As a hosteler, I see the latest open issues in my hostel so I know what's already reported.
- When I raise a ticket, I'm shown similar existing issues first and can repost one instead of creating a duplicate.
- I can repost an issue I'm also facing, undo it, and follow its progress.
- I can comment on an issue (add details, ask for updates).
- I see announcements from my Warden/Chief Warden, and urgent ones are impossible to miss.

**Warden / Chief Warden / Admin**
- I can see which issues affect the most hostelers, and priority rises automatically.
- I can publish, schedule, pin, edit, and archive announcements for my hostel (Warden) or any hostel (Chief Warden/Admin).
- I can hide an inappropriate comment or remove a post from the community feed.

**Caretaker**
- I see the "affected" count on my tickets and can post an official reply on a community ticket.

---

## 3. Data Model Changes

Add to apps: `tickets` (feed, reposts, comments, criticality) and a **new app `announcements`**. Create migrations in the order listed in Section 9.

### 3.1 `hostels.Category` (existing: add field)
| Field | Type | Notes |
|---|---|---|
| `allow_community` | Bool, default True | False for Security and Other (seed). Admin-editable. |

### 3.2 `tickets.Ticket` (existing: add fields)
| Field | Type | Notes |
|---|---|---|
| `visibility` | choices: `PRIVATE`, `HOSTEL` | Default `PRIVATE` unless the reporter shares. Forced `PRIVATE` if `category.allow_community` is False. |
| `show_reporter_name` | Bool, default False | D5. |
| `base_priority` | choices (same as priority) | What the reporter or staff set. |
| `priority` | choices | **Effective** priority = result of `recompute_criticality()`. All existing screens keep reading `priority`. |
| `repost_count` | PositiveInt, default 0, indexed | Denormalized count of reposts (reporter not included). |
| `affected_count` | property | `repost_count + 1` (reporter plus reposters). |
| `level_started_at` | DateTime | When the ticket reached its current level. Needed to recompute `due_at`. |
| `last_activity_at` | DateTime, indexed | Updated on repost, comment, status change. Orders the feed. |
| `community_hidden` | Bool, default False | Staff can remove a ticket from the feed. |
| `last_notified_threshold` | PositiveSmallInt, default 0 | Prevents duplicate "critical" notifications when counts flap. |

Add indexes: `(hostel, visibility, status, last_activity_at)` and `(hostel, repost_count)`.

### 3.3 `tickets.TicketRepost` (new)
| Field | Type | Notes |
|---|---|---|
| `ticket` | FK Ticket, `related_name="reposts"` | |
| `user` | FK User | |
| `note` | CharField(140), blank | Optional ("Same in room 204"). Visible to staff only. |
| `created_at` | DateTime | |

`UniqueConstraint(ticket, user)`. Undo = delete the row. Reposters are automatically added to `ticket.followers`.

### 3.4 `tickets.TicketComment` (existing: change)
Replace the `is_internal` boolean with a **`scope`** field (data migration: `is_internal=True → INTERNAL`, else `PRIVATE`):

| scope | Who can read |
|---|---|
| `INTERNAL` | Staff only (existing internal notes) |
| `PRIVATE` | Reporter and staff (existing behavior) |
| `COMMUNITY` | Everyone who can see the ticket in the feed: hostelers in that hostel and staff |

Also add: `is_hidden` (Bool), `hidden_by` (FK User, null), `hidden_reason` (CharField, blank), `is_official` (Bool: true when authored by staff, drives the role badge).

`COMMUNITY` scope is only allowed when `ticket.visibility == HOSTEL`.

### 3.5 `tickets.CriticalityRule` (new, admin-editable)
| Field | Type | Notes |
|---|---|---|
| `min_reposts` | PositiveInt, unique | Threshold (inclusive). |
| `bump_levels` | PositiveSmallInt | Raise priority by N steps (Low → Medium → High → Urgent). |
| `force_priority` | choices, null | If set, overrides `bump_levels` (for example Urgent). |
| `notify_level` | PositiveSmallInt, null | If set, send an FYI notification to staff at that level when the threshold is first crossed. |

**Seed defaults**

| Reposts | Effect |
|---|---|
| 3 | +1 priority step |
| 6 | +2 priority steps |
| 10 | Force **Urgent**, notify Warden (L2) |

### 3.6 `announcements` app (new)

**Announcement**
| Field | Type | Notes |
|---|---|---|
| `title` | CharField(150) | |
| `body` | TextField | Plain text. Rendered with `urlizetrunc` + `linebreaks` and autoescape on. |
| `kind` | choices: `NOTICE`, `MAINTENANCE`, `EMERGENCY`, `EVENT`, `POLICY` | Drives the icon. |
| `severity` | choices: `INFO`, `IMPORTANT`, `URGENT` | Drives color and the banner behavior. |
| `author` | FK User | |
| `all_hostels` | Bool | If true, `hostels` is ignored. |
| `hostels` | M2M Hostel | Audience scope. |
| `status` | choices: `DRAFT`, `SCHEDULED`, `PUBLISHED`, `ARCHIVED` | |
| `is_pinned` | Bool | Pinned items sort first. |
| `publish_at` | DateTime, null | For scheduling. |
| `published_at` | DateTime, null | Set when published. |
| `expires_at` | DateTime, null | Hidden from hostelers after this time. |
| `attachment` | FileField, null | PDF or image, max 5 MB. |
| `related_ticket` | FK Ticket, null | Optional link, for example "Water supply restored". |
| `created_at`, `updated_at` | DateTime | |

**AnnouncementRead**: `announcement` FK, `user` FK, `read_at`. Unique `(announcement, user)`.

Indexes: `(status, published_at)`, `(is_pinned, published_at)`.

### 3.7 `notifications.Notification` (existing: new `verb` values)
`REPOSTED`, `COMMUNITY_COMMENT`, `PRIORITY_RAISED`, `CRITICAL_ISSUE`, `ANNOUNCEMENT`, `ANNOUNCEMENT_URGENT`. Add `announcement` FK (null).

### 3.8 `TicketActivity` (existing: new `action` values)
`REPOSTED`, `REPOST_REMOVED`, `PRIORITY_AUTO_RAISED`, `COMMUNITY_COMMENT`, `COMMENT_HIDDEN`, `VISIBILITY_CHANGED`, `COMMUNITY_HIDDEN`.

---

## 4. Business Logic (all in `services/`, never in views)

### 4.1 `tickets/services/community.py`
- `feed_queryset(user, sort, filters)`: tickets where `hostel == user.hostel`, `visibility == HOSTEL`, `community_hidden == False`, `category.allow_community == True`, and the reporter is not the user (the user's own tickets are shown in "My tickets"). Default statuses: Open, Assigned, In Progress, On Hold, plus Resolved for 7 days (shown with a "Fixed" badge).
  Sorts: **Recent** (`-last_activity_at`), **Trending** (reposts in the last 7 days, then `-repost_count`), **Critical** (`-priority`, then `-repost_count`), **My reposts**.
  Use `select_related` and `prefetch_related`, and annotate `has_reposted` for the current user to avoid N+1 queries.
- `toggle_repost(user, ticket, note="")`: in a transaction, `select_for_update()` on the ticket. Validates D7. If a repost exists, delete it and decrement. Otherwise create it and increment, using `F()` expressions. Updates `last_activity_at`, adds or removes the user from followers, writes activity, then calls `recompute_criticality()`. Returns the new state (`reposted`, `repost_count`, `priority`).
- `add_community_comment(user, ticket, body)`: validates visibility, length (max 500), a simple rate limit (for example 5 comments per minute per user, checked by counting recent rows), sets `scope=COMMUNITY`, sets `is_official` for staff, updates `last_activity_at`, notifies the reporter and followers (batched).
- `hide_comment(staff, comment, reason)` and `set_community_hidden(staff, ticket, hidden, reason)`: staff only, logged.
- `similar_open_tickets(user, title, category)`: same hostel, `visibility == HOSTEL`, active status, same category, ranked by shared words in the title (`icontains` on up to 3 keywords, SQLite compatible). Return at most 3.

### 4.2 `tickets/services/criticality.py`
```
recompute_criticality(ticket):
    rule  = highest CriticalityRule with min_reposts <= ticket.repost_count (or None)
    auto  = base_priority
    if rule:
        auto = rule.force_priority or min(URGENT, base_priority + rule.bump_levels)
    new   = max(base_priority, auto)
    if new != ticket.priority:
        ticket.priority = new
        ticket.due_at = ticket.level_started_at + SLA(new, ticket.current_level)
        # if due_at is already past, the escalation job handles it on its next run
        log PRIORITY_AUTO_RAISED (or lowered when reposts are removed)
        notify reporter, assignee, reposters (once per change)
    if rule and rule.min_reposts > ticket.last_notified_threshold:
        ticket.last_notified_threshold = rule.min_reposts
        if rule.notify_level: notify staff at that level (CRITICAL_ISSUE)
```
Rules: idempotent, never goes above Urgent, never goes below `base_priority`. If staff manually change priority, they edit `base_priority`; the auto part is recalculated on top of it. Only `recompute_criticality` writes `priority`.

### 4.3 Criticality display
Show the effective priority everywhere (list, Kanban, dashboard, detail). Where `priority != base_priority`, show a small "Raised by N reposts" note with a tooltip: "Priority was automatically increased because N hostelers reported this."

### 4.4 `announcements/services.py`
- `audience_users(announcement)`: active hostelers in the targeted hostels (all, if `all_hostels`).
- `can_publish(user, announcement)`: Warden only if every targeted hostel is the user's hostel; Chief Warden and Admin for any hostel. Enforced in the service **and** the form.
- `publish(announcement, actor)`: sets `status=PUBLISHED` and `published_at`, bulk-creates notifications in batches of 500 (`ANNOUNCEMENT`, or `ANNOUNCEMENT_URGENT` when severity is Urgent), writes an audit row.
- `schedule(announcement, when)` and `archive(announcement)`.
- `visible_to(user)` queryset: published, not expired, audience includes the user's hostel. Pinned first, then newest.
- `unread_count(user)` and `mark_read(user, announcement)` (idempotent).
- Management command `publish_scheduled_announcements`: publishes everything where `status=SCHEDULED` and `publish_at <= now`. Safe to run repeatedly. Run it with the existing `run_escalations` cron (every 5 to 10 minutes).

### 4.5 Notification batching
To avoid spam, collapse repost notifications to the reporter: one notification per ticket per hour, updated in place ("3 hostelers reposted your ticket").

---

## 5. Permissions (additions to the matrix)

| Action | Hosteler | Caretaker | Warden | Chief Warden | Admin |
|---|---|---|---|---|---|
| See community feed (own hostel) | Yes | Yes (their hostel) | Yes (own hostel) | Yes (all) | Yes (all) |
| Repost | Yes (D7 rules) | No | No | No | No |
| Comment publicly | Yes | Yes (official) | Yes (official) | Yes (official) | Yes (official) |
| Hide a comment / remove post from feed | No | No | Yes | Yes | Yes |
| View reposter list and notes | No | Yes (own tickets) | Yes | Yes | Yes |
| Edit criticality rules | No | No | No | No | Yes |
| Read announcements | Yes (audience) | Yes | Yes | Yes | Yes |
| Publish / edit / archive announcements | No | No | Own hostel only | Any | Any |

All enforced through querysets and `permissions.py`, not by hiding buttons.

---

## 6. URL Map (additions)

| URL | Method | View | Who |
|---|---|---|---|
| `/community/` | GET | Feed page | Hosteler (staff read-only) |
| `/community/feed/` | GET | HTMX partial: paged cards (`?sort=&category=&status=&page=`) | Same |
| `/community/similar/` | GET | HTMX partial: similar issues while raising a ticket | Hosteler |
| `/tickets/<ticket_no>/repost/` | POST | Toggle repost; returns the updated footer partial | Hosteler |
| `/tickets/<ticket_no>/community-comments/` | GET / POST | List or add community comments (HTMX) | Scoped |
| `/community/comments/<id>/hide/` | POST | Hide comment | Warden+ |
| `/community/<ticket_no>/hide/` | POST | Remove from or restore to the feed | Warden+ |
| `/announcements/` | GET | List (hosteler and staff reading) | All |
| `/announcements/<id>/` | GET | Detail; marks as read | Audience |
| `/announcements/<id>/read/` | POST | Mark as read (also used by banner dismissal) | Audience |
| `/manage/announcements/` | GET | Staff list with status filters | Warden+ |
| `/manage/announcements/new/`, `/<id>/edit/` | GET / POST | Create and edit | Warden+ |
| `/manage/announcements/<id>/publish/`, `/archive/`, `/pin/` | POST | State changes | Warden+ |
| `/manage/criticality/` | GET / POST | Edit rules | Admin |

---

## 7. UI Specification

Follow `UI_UX_IMPROVEMENT_PLAN.md` for tokens, type scale, background, cards, and components. New tokens to add to `tokens.css`:

```css
--crit-low:#8D8D8D; --crit-med:#2490EF; --crit-high:#F08C00; --crit-urgent:#E03E3E;
--ann-info-bg:#E8F1FD;  --ann-info-fg:#1D5FB4;
--ann-imp-bg:#FFF3E0;   --ann-imp-fg:#B45309;
--ann-urg-bg:#FDE8E8;   --ann-urg-fg:#C53030;
```

### 7.1 Hosteler home: new layout
```
┌ Urgent announcement banner (only if an unread URGENT one exists) ─────┐
Welcome panel (one primary CTA: Raise ticket)
[ In progress ] [ Resolved ] [ Closed ]
┌────────────────────────────────────────┐ ┌───────────────────────────┐
│ Hostel feed                            │ │ 📢 Announcements          │
│ [Recent] [Trending] [Critical] [Mine]  │ │  pinned + latest 3        │
│ [Category ▾] [Status ▾]                │ │  [View all →]             │
│ ┌ post card ───────────────────────┐   │ ├───────────────────────────┤
│ │ ...                              │   │ │ 🔥 Trending in your hostel│
│ └──────────────────────────────────┘   │ │  top 3 by reposts         │
│ ┌ post card ───────────────────────┐   │ ├───────────────────────────┤
│ │ ...                              │   │ │ My tickets (recent 3)     │
│ └──────────────────────────────────┘   │ └───────────────────────────┘
│ (infinite scroll)                      │
└────────────────────────────────────────┘
```
- Desktop: 8/4 column grid (`minmax(0,1fr) 340px`). Right rail is sticky.
- Below 1024px: single column in this order: urgent banner, welcome, stats, announcements (horizontal scroll cards), feed, trending, my tickets.
- A full-page version of the feed lives at `/community/` with the same filters and a wider card.
- Sidebar gets two items for hostelers: **Community** (users icon) and **Announcements** (megaphone icon, unread dot). Add them to the group dividers defined in the UI plan.

### 7.2 Post card (`templates/community/_post_card.html`)
```
┌──────────────────────────────────────────────────────────┐
│ (avatar)  A hosteler · Block 2 · 2h ago      [Assigned]  │
│ [⚡ Electrical]                                           │
│ Ceiling fan regulator not working                        │
│ The regulator sparks when turned to max speed...  (2 lines)
│                                                          │
│ Priority ▮▮▮▯  High  · raised by 6 reposts               │
│ 👥 7 hostelers affected                                  │
│ ──────────────────────────────────────────────────────── │
│ [ ⟲ Repost · 6 ]   [ 💬 Comment · 4 ]            View →  │
│ ┌ comments (collapsed; loads on click) ────────────────┐ │
└──────────────────────────────────────────────────────────┘
```
- Card follows the standard card style. Hover raises the border and shadow only.
- **Criticality meter:** four segments, filled by priority, colored by `--crit-*`. Label "High" plus a muted "raised by N reposts" when priority was auto-raised. Urgent shows a red-tinted **"Critical"** pill with an alert-triangle icon. No flashing or pulsing.
- **Affected line:** `affected_count` with a users icon.
- **Repost button states:**
  - Default: secondary button, `repeat` icon, count. Tooltip "I'm facing this too".
  - Reposted: blue-tint fill, check icon, text "Reposted"; click again to undo (no confirm).
  - Own ticket: no button, a muted "Your ticket" chip.
  - Resolved/Closed: disabled, tooltip "This issue is no longer active".
- **Interaction:** `hx-post` to `/tickets/<no>/repost/`, `hx-target` = the card footer, `hx-swap="outerHTML"`. The response also updates the meter and affected line (out-of-band swap). The count change fades in over 160ms. On failure, a toast shows the reason (for example "You can't repost your own ticket").
- **Comments:** clicking Comment expands a thread under the card (`hx-get`, lazy). Shows the latest 3 comments plus "View all N comments". Each comment: small avatar, "Arnov R.", relative time, text. Staff comments show a role badge ("Caretaker", "Warden") and a subtle left accent as **official reply**. Input: single-line textarea that grows, 500-character counter, Enter to send, Shift+Enter for a newline. Own comments can be deleted within 10 minutes. Staff see "Hide" on any comment. A "Report" link on others' comments flags it to the Warden through a notification.
- **Fixed badge:** Resolved posts show a green "Fixed" pill and "Fixed 1d ago", and the Repost button is disabled.
- **Empty feed:** "No shared issues in your hostel right now. When someone shares an issue, you'll see it here." plus a Raise ticket button.
- **Skeleton:** 3 shimmer cards while the first page loads.

### 7.3 Raise-ticket form changes
- New toggle at the bottom: **"Share this with other hostelers in my hostel"** (default on for non-sensitive categories, disabled with a helper line for sensitive ones: "This category is always private").
- When shared: sub-toggle **"Show my name"** (default off).
- **Similar issues panel** appears under the Title field after 3+ characters, debounced 400ms (`hx-get="/community/similar/"`, `hx-trigger="keyup changed delay:400ms"`). Shows up to 3 matches with status, repost count, and a **Repost instead** button. Copy: "Already reported in your hostel. Repost instead of creating a duplicate?" The user can ignore it and submit anyway.

### 7.4 Announcements: hosteler side
- **Right-rail card:** up to 4 items: pinned first, then newest. Each item: kind icon, title (1 line), 2-line preview, author role and date, severity color on the icon chip only (not the whole card). Unread items have a small blue dot and bolder title. "View all" goes to `/announcements/`.
- **List page `/announcements/`:** `max-width: 760px`. Tabs: All · Unread · Pinned. Cards with full title, body clamped to 3 lines with "Read more", author ("Dr. Sunita Patel · Warden · Girls Hostel 1"), audience chip ("Girls Hostel 1" or "All hostels"), date, attachment link, related-ticket chip.
  - Severity styling: Info = blue tint icon chip; Important = amber; **Urgent** = red tint, a 3px red left edge, and a "Urgent" pill.
- **Detail page:** full body, attachment preview, related ticket link. Opening it marks it read.
- **Urgent banner:** if the user has an unread URGENT announcement, a slim banner appears under the top bar on every hosteler page: icon, title, "Read" link, and a dismiss (×) that calls `/announcements/<id>/read/`. Max one banner at a time; if more than one is unread, it says "+2 more".
- **Bell and sidebar:** unread announcements add to the notification dot; the Announcements sidebar item shows an unread dot.

### 7.5 Announcements: staff side (`/manage/announcements/`)
- List table (shared Data table): Title · Type · Severity pill · Audience · Status pill (Draft gray, Scheduled purple, Published green, Archived gray) · Published/Scheduled time · Read count ("142 / 180") · Actions (Edit, Pin, Archive). Filters: status, hostel.
- **Create/Edit form** (`max-width: 880px`, two columns on desktop):
  - Left: Title, Type (select), Severity (segmented: Info · Important · Urgent), Body (textarea, 2000 characters with counter), Attachment (drop zone, PDF/image, 5 MB), Related ticket (search select, optional).
  - Right: **Audience** (Warden: locked to own hostel, shown as a read-only chip; Chief Warden/Admin: "All hostels" toggle or multi-select), **Pin to top** switch, **Schedule** (Publish now · Schedule for later with date-time · Save as draft), **Expires** (optional date-time), and a **live preview** of the hosteler-side announcement card, built with Alpine from the form values.
  - Buttons: **Publish** (primary), **Save draft** (secondary), **Cancel**. Publishing an Urgent announcement shows a confirm dialog: "This will send an urgent alert to N hostelers."
- Staff dashboard gets an optional small widget "Latest announcements" (last 3 with read rates).

### 7.6 Staff-side changes for the repost feature
- **Ticket List:** new sortable **Affected** column (`👥 7`), and a filter "Most affected". Priority column shows the raised-by-reposts note on hover.
- **Kanban card:** small `👥 N` chip next to the level chip when `repost_count > 0`.
- **Ticket detail (staff):** new **Community** panel: affected count, priority history ("Base: Low → Now: High"), reposter list (name, room, note, time), the public comment thread (with Hide), and a "Remove from community feed" button that asks for a reason.
- **Dashboard:** new card **Most-reported issues** (top 5 by `repost_count`: ID, title, hostel, affected count, current priority).
- **Admin → Criticality rules** screen: table of thresholds with inline edit, a short explainer ("At 3 reposts priority increases one step"), and a live example.

---

## 8. Notifications Summary

| Event | Who is notified | Notes |
|---|---|---|
| Someone reposts your ticket | Reporter | Batched, at most one per hour per ticket |
| Priority auto-raised | Reporter, assignee, reposters | Once per change |
| Threshold crossed with `notify_level` | Staff at that level in the hostel | "Critical issue: 10 hostelers affected" |
| Community comment | Reporter and followers (reposters) | Batched |
| Status change on a ticket you reposted | Reposters (they follow it) | Existing flow |
| Announcement published | Audience hostelers | Bulk create, batches of 500 |
| Urgent announcement | Audience hostelers | Also triggers the banner |

---

## 9. Build Phases

### Phase C0: Prerequisites
- [ ] UI plan Phase 2 (shared components) is merged. If not, build the components this feature needs first (card, avatar, chip, pill, empty state, toast, segmented tabs).
- [ ] Branch `feature/community-feed`.

### Phase C1: Data model
- [ ] Migrations in this order: (1) `Category.allow_community` and seed values; (2) new `Ticket` fields, with a data migration setting `base_priority = priority`, `level_started_at = created_at` (or the last assignment time), `last_activity_at = updated_at`; (3) `TicketRepost`; (4) `TicketComment.scope` and related fields, with the `is_internal` data migration; (5) `CriticalityRule` plus seed; (6) `announcements` app; (7) notification and activity choices.
- [ ] Register everything in Django admin as a fallback tool.
- **Done when:** `migrate` runs forward on an existing database with seeded tickets without data loss, and existing screens still show the same priorities.

### Phase C2: Services and permissions
- [ ] `community.py`, `criticality.py`, `announcements/services.py`, the notification batching, and `permissions.py` additions.
- [ ] `TicketQuerySet.community_for(user)` and the comment visibility filter (`scope` aware).
- [ ] Management command `publish_scheduled_announcements`.
- **Done when:** all service tests in Section 10 pass.

### Phase C3: Hosteler feed
- [ ] Post card, feed partial with infinite scroll (`hx-trigger="revealed"`), tabs and filters, repost button and its HTMX swaps, comment thread, similar-issues panel in the raise form, visibility and name toggles.
- [ ] Hosteler home restructured (7.1), Community page, sidebar items.
- **Done when:** two hosteler accounts in the same hostel can raise, see, repost, comment, and undo, and priority rises at the thresholds.

### Phase C4: Announcements
- [ ] Hosteler right rail, list and detail pages, urgent banner, unread indicators.
- [ ] Staff list and the create/edit form with the live preview, publish/schedule/draft/archive/pin actions.
- **Done when:** a Warden publishes to their own hostel and only those hostelers are notified; an Admin publishes to all; a Warden cannot target another hostel even by crafting the POST.

### Phase C5: Staff-side visibility and admin
- [ ] Affected column and filter in the list, Kanban chip, ticket detail Community panel, dashboard widget, criticality rules screen, hide comment/post flows.
- **Done when:** staff can see who is affected and moderate content, and the Admin can change thresholds and see the effect on new reposts.

### Phase C6: Polish, QA, release
- [ ] Skeletons, empty states, error toasts, responsive checks at 1440/1024/768/375, keyboard and screen-reader pass (buttons have `aria-pressed` for Repost state, counts announced with `aria-live="polite"`).
- [ ] Seed demo data: 12 community tickets with 0 to 11 reposts, 25 comments (some official), 5 announcements across severities and statuses.
- [ ] Full regression: `python manage.py check`, test suite, manual run through every role.

---

## 10. Testing Plan

| Area | Tests |
|---|---|
| Repost | Unique per user and ticket; cannot repost own ticket; cannot repost other hostel's ticket; cannot repost inactive ticket; undo works; counter stays correct under concurrent requests (two threads reposting at once); follower added and removed correctly. |
| Criticality | Each threshold (3, 6, 10) gives the expected priority; capped at Urgent; never below `base_priority`; removing reposts lowers only the auto part; `due_at` recomputed from `level_started_at`; threshold notifications sent once; staff manual change of `base_priority` is respected. |
| Visibility | `PRIVATE` tickets never appear in any feed; sensitive categories can never be shared; `community_hidden` removes from the feed; resolved tickets drop out after 7 days. |
| Privacy | The feed HTML and JSON never contain the reporter's name (unless opted in), room number, or internal notes; attachments are not shown in the feed; staff see real identities. |
| Comments | Scope rules (INTERNAL never leaks to hostelers; COMMUNITY only on shared tickets); rate limit; 500-character limit; hide hides for hostelers but stays visible to staff with the reason; official badge only for staff. |
| Announcements | Audience scoping by hostel; Warden cannot publish to another hostel (service and form); scheduled publish is idempotent; expired items hidden; unread counts; mark read idempotent; urgent banner logic; bulk notification count equals audience size. |
| Views | HTMX partials return only the fragment; pagination; sorting (Trending uses the last 7 days); `/community/similar/` returns at most 3 matches in the user's hostel only. |
| Regression | Existing ticket list, Kanban, dashboard, escalation job, and status workflow unchanged (existing tests still green). |

Use `factory_boy` and `freezegun`. Target 85%+ coverage on the new services.

---

## 11. Security, Abuse and Privacy Checklist
- Object-level permission checks in every new view. Never rely on the feed queryset alone for detail or POST endpoints.
- Anti-abuse: one repost per user per ticket; a daily repost cap (for example 30) per user; comment rate limit; a body length limit; strip control characters.
- Escape everything: announcements render with autoescape on; no `|safe`.
- Upload validation for announcement attachments (type, size, renamed file).
- Reporter identity and room are never rendered in feed templates unless the explicit opt-in is set. Add a test that greps the rendered HTML.
- Audit trail for: repost, undo, auto-priority change, hide comment, hide post, publish, archive.
- No author edit of a post's content once it has reposts (the original description must not be changed under people who agreed with it). Staff can still add notes.

---

## 12. Acceptance Checklist
- [ ] A hosteler sees recent shared issues from their own hostel only.
- [ ] Reposting works once per ticket, can be undone, never creates a new ticket, and updates counts instantly via HTMX.
- [ ] Priority rises automatically at 3, 6, and 10 reposts, the SLA deadline updates, and the card shows "raised by N reposts".
- [ ] Hostelers can comment on shared issues; staff replies are clearly marked official; moderation works.
- [ ] Raising a ticket suggests similar open issues and offers "Repost instead".
- [ ] Reporter identity and room are hidden from other hostelers by default.
- [ ] Warden, Chief Warden, and Admin can publish, schedule, pin, and archive announcements within their scope; hostelers get notifications, an unread dot, and an urgent banner.
- [ ] Staff can see affected counts and reposter lists, and the dashboard shows most-reported issues.
- [ ] Existing features still work and all tests pass.
- [ ] The UI matches `UI_UX_IMPROVEMENT_PLAN.md` (tokens, components, responsive behavior).

---

## 13. Rules for the Agent
1. Business logic lives in `services/`. Views stay thin.
2. Counts are changed only with `F()` expressions inside a transaction on a locked ticket row.
3. Only `recompute_criticality()` writes `Ticket.priority`.
4. Do not add a rich-text editor, a markdown library, or any new dependency without asking.
5. Every new model gets a migration, an admin registration, a factory, and tests.
6. Never render reporter identity, room, or internal data in any community template.
7. Announce the phase at the start of each task and commit with `feat:` or `test:` prefixes after each phase.
8. If a requirement here conflicts with the earlier plans, this document wins for the community feed and announcements only.
