# Hostel Ticket System: Project Plan

> **Purpose of this file:** Single source of truth for building the Hostel Ticket System in Django. Follow the phases in order. Do not skip ahead. After each phase, run the checks listed under "Done when" before moving on.

---

## 1. Project Overview

Hostelers face recurring problems (water, electricity, internet, cleanliness, furniture, mess, security, etc.). This system lets a hosteler **raise a ticket**, which is automatically routed to the **first responsible person in a hierarchy**. If the issue is not resolved within a set time (SLA), the ticket **escalates** to the next level up.

### Goals
- Hostelers raise, track, comment on, and close tickets.
- Tickets route automatically by category and hostel to the correct staff member.
- Unresolved tickets escalate up the hierarchy on a timer.
- Staff see work in a **List view**, **Kanban board**, and **Dashboard**.
- Every action is logged (full audit trail).

### Non-goals (v1)
- Mobile app, payments, SMS/WhatsApp integration, multi-tenant (multiple colleges).

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | **Django 5.x** (Python 3.11+) | Class-based views, Django ORM |
| Database | SQLite (dev), PostgreSQL (prod) | Settings split by environment |
| Frontend | Django templates + **HTMX** + **Alpine.js** | No SPA, no React |
| Styling | **Custom CSS with design tokens** (no Bootstrap) | See Section 4 |
| Charts | **Chart.js** | Dashboard |
| Kanban drag/drop | **SortableJS** + HTMX POST | Status change on drop |
| Icons | **Lucide** (SVG sprite) | Thin outline icons, matches reference |
| Font | **Inter** | Self-host or Google Fonts |
| Background jobs | Management command + cron first; Celery + Redis optional later | For escalation + reminders |
| Auth | Django auth, custom User model | Login by Roll No / Employee ID |
| Env config | `django-environ` | `.env` file |
| Testing | `pytest-django`, `factory_boy` | |
| Code quality | `ruff`, `black`, `pre-commit` | |

---

## 3. Roles and Escalation Hierarchy

### 3.1 Roles

| Role | Code | Description |
|---|---|---|
| Hosteler | `HOSTELER` | Student living in a hostel. Raises tickets. |
| Staff L1: Caretaker / Technician | `CARETAKER` | First responder. Fixes or assigns work. |
| Staff L2: Hostel Warden | `WARDEN` | Handles escalations for one hostel. |
| Staff L3: Chief Warden | `CHIEF_WARDEN` | Handles escalations across all hostels. |
| Staff L4: Admin / Dean | `ADMIN` | Final escalation. Full system access. |

### 3.2 Hierarchy Rules
- Each staff user has an **`escalation_level`** (1 to 4).
- A ticket starts at **Level 1** and is **auto-assigned** using routing rules (Section 5.6).
- Each level has an **SLA** (hours) before the ticket escalates to the next level.
- Staff can also **manually escalate** or **reassign** (with a required note).
- When the ticket reaches Level 4 and the SLA is breached, it is flagged **"Critical Overdue"** and shown on the Admin dashboard.

### 3.3 Default SLA table (editable in Admin)

| Priority | L1 SLA | L2 SLA | L3 SLA | L4 SLA |
|---|---|---|---|---|
| Urgent | 2h | 2h | 4h | 4h |
| High | 8h | 8h | 12h | 12h |
| Medium | 24h | 24h | 24h | 24h |
| Low | 48h | 48h | 48h | 48h |

### 3.4 Permission Matrix

| Action | Hosteler | Caretaker | Warden | Chief Warden | Admin |
|---|---|---|---|---|---|
| Raise ticket | Yes | No | No | No | Yes (on behalf) |
| View own tickets | Yes | n/a | n/a | n/a | n/a |
| View tickets assigned to them | n/a | Yes | Yes | Yes | Yes |
| View all tickets of own hostel | No | No | Yes | Yes | Yes |
| View all tickets, all hostels | No | No | No | Yes | Yes |
| Change status | Close/Reopen own | Yes | Yes | Yes | Yes |
| Reassign / Escalate | No | Escalate up | Yes | Yes | Yes |
| Comment | Yes | Yes | Yes | Yes | Yes |
| Internal (staff-only) note | No | Yes | Yes | Yes | Yes |
| Manage hostels, rooms, categories, SLA | No | No | No | No | Yes |
| View analytics dashboard | No | Own scope | Hostel scope | All | All |

Enforce with a central `permissions.py` helper plus a `TicketQuerySet.visible_to(user)` method. Never rely on hiding buttons alone.

---

## 4. UI / UX Design Specification

**Reference style:** ERPNext / Frappe desk UI. Clean, light, dense, enterprise-style, with soft pastel status pills, thin borders, small type, and a black primary button. The three reference screens map to our three main staff views:

| Reference screen | Our screen |
|---|---|
| Purchase Order list view (filter sidebar + table) | **Ticket List View** |
| Accounts Dashboard (number cards + bar charts) | **Analytics Dashboard** |
| Job Card Kanban (pastel columns + cards) | **Ticket Kanban Board** |

### 4.1 Design Tokens (put in `static/css/tokens.css`)

```css
:root {
  /* Surfaces */
  --bg-app:        #F4F5F6;   /* page background */
  --bg-surface:    #FFFFFF;   /* cards, tables */
  --bg-subtle:     #F3F3F3;   /* inputs, hover rows, filter chips */
  --border:        #E5E7EB;
  --border-strong: #D1D5DB;

  /* Text */
  --text-primary:   #171717;
  --text-secondary: #525252;
  --text-muted:     #8D8D8D;

  /* Brand / actions */
  --primary:        #171717;  /* black "+ Add" button, like reference */
  --primary-text:   #FFFFFF;
  --accent:         #2490EF;  /* links, focus ring, logo tile */

  /* Status pills: bg / text */
  --st-open-bg:     #FDE8E8;  --st-open-fg:     #C53030;  /* red-ish */
  --st-assigned-bg: #E8F1FD;  --st-assigned-fg: #1D5FB4;  /* blue */
  --st-progress-bg: #FFF3E0;  --st-progress-fg: #B45309;  /* orange */
  --st-hold-bg:     #EFE7FB;  --st-hold-fg:     #6B3FA0;  /* purple */
  --st-resolved-bg: #E3F5EA;  --st-resolved-fg: #1F7A4D;  /* green */
  --st-closed-bg:   #EDEDED;  --st-closed-fg:   #525252;  /* grey */
  --st-escalated-bg:#FFE4EC;  --st-escalated-fg:#B4234F;  /* pink */

  /* Kanban column tints (very light) */
  --col-open:      #FBECEC;
  --col-assigned:  #EAF1FB;
  --col-progress:  #FDF2E4;
  --col-hold:      #F1ECFA;
  --col-resolved:  #E8F5EC;

  /* Priority dots */
  --prio-urgent: #E03E3E;
  --prio-high:   #F08C00;
  --prio-medium: #2490EF;
  --prio-low:    #8D8D8D;

  /* Shape and spacing */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-card: 0 1px 2px rgba(0,0,0,.05);
  --shadow-pop:  0 8px 24px rgba(0,0,0,.12);

  /* Type */
  --font: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --fs-xs: 11px; --fs-sm: 12px; --fs-base: 13px; --fs-md: 14px; --fs-lg: 18px; --fs-xl: 22px;
}
```

**Rules**
- Base font-size is **13px** (dense, like the reference). Headings are semibold, never huge.
- Borders are 1px `--border`. Avoid heavy shadows. Cards use `--shadow-card` only.
- Primary button = **black**, white text, 6px radius, small icon `+` on the left (e.g. "+ Raise Ticket").
- Secondary buttons = white/`--bg-subtle` with 1px border.
- Status shown as **pill badges** (see tokens), 11 to 12px, medium weight, 4px 8px padding, fully rounded.
- Support dark mode later via `[data-theme="dark"]` token overrides. Not in v1, but do not hardcode colours anywhere outside `tokens.css`.

### 4.2 Global Layout (`templates/base.html`)

```
┌────┬──────────────────────────────────────────────────────────┐
│    │ Breadcrumb: Tickets > List        [Search ⌘K]  🔔  Help ▾  (avatar)│
│ ◻  ├──────────────────────────────────────────────────────────┤
│ ◻  │ Page title                   [List View ▾] [⟳] [⋯] [+ Raise Ticket]│
│ ◻  ├──────────────────────────────────────────────────────────┤
│ ◻  │                                                          │
│ ◻  │                   Page content                           │
│    │                                                          │
└────┴──────────────────────────────────────────────────────────┘
 ↑ narrow icon rail (56px), logo tile at the top
```

- **Left icon rail (56px):** logo tile (blue rounded square with letter, like reference) then icons: Dashboard, Tickets (list), Kanban, Hostels/Rooms (admin), Reports, Settings. Active icon gets a subtle grey background. Tooltip with label on hover. Items shown depend on role.
- **Top bar:** breadcrumbs on the left; global search (`⌘/Ctrl + K`) in the centre-right; notification bell with unread dot; Help dropdown; avatar menu (Profile, Logout).
- **Page header:** title on the left; right side holds view switcher (List / Kanban), refresh icon, overflow `⋯` menu, and the black primary button.
- Content area uses `--bg-app`; tables and cards sit on white with rounded corners and 1px border.

Partials to build: `_sidebar.html`, `_topbar.html`, `_page_header.html`, `_status_pill.html`, `_priority_dot.html`, `_avatar.html`, `_empty_state.html`, `_toast.html`, `_pagination.html`.

### 4.3 Screen: Ticket List View (staff + hosteler)
Modelled on the Purchase Order reference.

- **Left filter sidebar (~200px):**
  - "Filter By" section with dropdowns: *Assigned To*, *Created By*, *Hostel*, *Category*, *Priority*.
  - "Edit Filters" link.
  - **Tags** dropdown and "Show Tags".
  - **Save Filter:** text input "Filter Name" with Save. Below it, "Hide Saved" and a list of saved filters as removable chips (`×`).
- **Top filter bar:** inline inputs for *ID*, *Reporter*, *Room*, *Status* (select), plus `Filter` button with `×` clear, and a sort control (`Last Updated On` with direction toggle).
- **Table columns:** checkbox, Title (bold), Status (pill), Category, Priority (dot + label), Hostel/Room, Level (L1 to L4), SLA progress bar (green to amber to red as the deadline nears), Ticket ID (`HTL-2026-00001`), time ago (`8 M`, `9 M`, `1 y`), comment count with bubble icon, like/follow heart.
- **Footer of the table header:** "20 of 37" count and a bulk-actions bar (appears when rows are checked: Assign, Change Status, Escalate).
- Row hover = `--bg-subtle`. Click a row to open the ticket detail page.
- Server-side pagination (20 per page). Filters update the table through **HTMX** without a page reload, and the URL query string stays in sync so views are shareable.
- Hosteler version: same component but with a smaller filter set (Status, Category) and only their own tickets.

### 4.4 Screen: Kanban Board
Modelled on the Job Card reference.

- Page title shows scope, e.g. "Hostel A: Kanban". Header controls: `Filter`, `Select Kanban` (hostel/category), `Kanban View ▾`, refresh, `⋯`, `+ Raise Ticket`.
- **Columns (pastel-tinted, rounded 12px, horizontally scrollable):**
  1. 🔴 **Open**
  2. 🔵 **Assigned**
  3. 🟠 **In Progress**
  4. 🟣 **On Hold**
  5. 🟢 **Resolved**
  - Column header: coloured dot + name + `⋯` menu. Under it a white `+ Add Ticket` ghost button.
- **Card (white, 8px radius, soft shadow):** Title, Ticket ID, Hostel / Room, priority dot, SLA time left (turns red when overdue), small avatar of assignee, heart (follow) at the bottom-left and `+` quick-action at the bottom-right.
- **Drag and drop** (SortableJS) between columns triggers an HTMX `POST` that validates permission, updates status, writes an activity log, and returns the refreshed card. Invalid moves snap back with a toast.
- Closed tickets are not shown on the board (use the list view).
- Hosteler role does **not** get Kanban.

### 4.5 Screen: Analytics Dashboard
Modelled on the Accounts Dashboard reference.

- **Top number-card row** (with thin separators/operators like the reference): *Total Tickets This Month*, *Resolved*, *Open*, *Overdue*. Large value (22px, semibold). Resolved in green, Overdue in red.
- **Wide bar chart:** Tickets Created vs Resolved vs Overdue (grouped bars, pink / blue / green palette like reference), by month.
- **Two charts side by side**, each with a header (title, "Last synced N minutes ago") and controls (filter icon, date-range select, `Weekly/Monthly` select, `⋯`):
  - *Tickets by Category* (bar)
  - *Avg Resolution Time by Hostel* (bar)
- Extra widgets (below): *Escalations by Level*, *Top Staff by Resolved Tickets*, *Overdue Tickets* (compact table).
- Data comes from `/dashboard/api/...` JSON endpoints scoped by role (Section 3.4). Charts rendered with Chart.js using token colours.

### 4.6 Screen: Ticket Detail
- **Two-column layout.**
  - **Left (main):** title, status pill, description, image attachments (thumbnail grid with lightbox), then a **tabbed Activity section**: *Comments*, *Internal Notes* (staff only), *History* (timeline of status, assignment, and escalation events).
  - **Right sidebar (card):** Ticket ID, Reporter, Hostel / Room, Category, Priority, Created, **Assigned To (with level badge)**, **SLA countdown + progress bar**, **Escalation path** (L1 → L2 → L3 → L4 with the current level highlighted), Follow (heart) toggle.
- **Action bar (staff):** `Change Status ▾`, `Reassign`, `Escalate`, `Add Note`. Hosteler: `Close ticket` or `Reopen` once resolved, and `Add comment`.

### 4.7 Screen: Raise Ticket (Hosteler)
- Centred card form (max 640px): Category (select), Sub-issue (optional select), Priority (segmented control, default Medium), Title, Description (textarea), Location (auto-filled with the user's hostel/room, editable), Attachments (drag-and-drop, up to 3 images, 5 MB each).
- Inline validation. On submit: success toast, redirect to the ticket detail page.

### 4.8 Screen: Hosteler Home
Clean variant of the dashboard: 3 number cards (My Open, My Resolved, Awaiting My Confirmation), a "Recent tickets" compact table, and a prominent `+ Raise Ticket` button. No Kanban.

### 4.9 Other screens
- **Login:** split or centred card, Roll No / Employee ID + password, logo tile on top.
- **Profile:** name, hostel, room, phone, change password.
- **Notifications page** plus bell dropdown (last 10), mark all as read.
- **Admin management screens** (custom, not just Django admin): Hostels, Blocks and Rooms, Categories, Routing Rules, SLA Policies, Users. Use the same list-view component.
- **Empty states, 403, 404, 500 pages** styled to match.

### 4.10 Interaction and accessibility
- Responsive: icon rail collapses to a bottom bar below 768px; filter sidebar becomes a slide-over drawer; Kanban scrolls horizontally.
- Keyboard: `Ctrl/⌘ + K` opens global search; all controls focusable with a visible 2px `--accent` focus ring.
- Contrast: status pill text/background pairs must meet WCAG AA.
- Toasts for success/error; loading skeletons for list and chart areas; HTMX indicator spinner on actions.

---

## 5. Data Model

Use a custom `User` from day one. Put timestamps on everything via an abstract `TimeStampedModel`.

### 5.1 `accounts.User` (extends `AbstractUser`)
| Field | Type | Notes |
|---|---|---|
| `login_id` | CharField, unique | Roll No or Employee ID (`USERNAME_FIELD`) |
| `full_name` | CharField | |
| `email` | EmailField | optional |
| `phone` | CharField | optional |
| `role` | CharField (choices) | HOSTELER, CARETAKER, WARDEN, CHIEF_WARDEN, ADMIN |
| `escalation_level` | PositiveSmallInt, null | 1 to 4 for staff, null for hostelers |
| `hostel` | FK `hostels.Hostel`, null | Hostel the user belongs to or manages |
| `room` | FK `hostels.Room`, null | Hostelers only |
| `avatar` | ImageField, null | |
| `is_active` | Bool | |

### 5.2 `hostels` app
- **Hostel**: `name`, `code`, `gender_type` (Boys/Girls/Co-ed), `address`, `is_active`.
- **Block**: `hostel` FK, `name`.
- **Room**: `block` FK, `room_number`, `floor`, `capacity`.

### 5.3 `tickets.Category`
`name`, `icon`, `default_priority`, `is_active`. Examples: Electrical, Plumbing/Water, Internet/Wi-Fi, Cleaning/Housekeeping, Furniture, Mess/Food, Security, Maintenance, Other.
Optional **SubCategory** (`category` FK, `name`).

### 5.4 `tickets.Ticket`
| Field | Type | Notes |
|---|---|---|
| `ticket_no` | CharField, unique | `HTL-YYYY-00001`, generated safely |
| `title` | CharField(150) | |
| `description` | TextField | |
| `category` | FK Category | |
| `sub_category` | FK, null | |
| `priority` | choices | URGENT, HIGH, MEDIUM, LOW |
| `status` | choices | OPEN, ASSIGNED, IN_PROGRESS, ON_HOLD, RESOLVED, CLOSED, REJECTED |
| `reporter` | FK User | |
| `hostel`, `room` | FKs | Snapshot at time of creation |
| `assigned_to` | FK User, null | Current owner |
| `current_level` | PositiveSmallInt | 1 to 4 |
| `due_at` | DateTime | Deadline at the current level |
| `is_overdue` | Bool (indexed) | Maintained by the escalation job |
| `resolved_at`, `closed_at` | DateTime, null | |
| `resolution_note` | TextField, blank | |
| `rating` | PositiveSmallInt, null | 1 to 5 hosteler feedback after closing |
| `followers` | M2M User | Heart/follow |
| `tags` | M2M Tag | Filter sidebar "Tags" |

Indexes: `(status, current_level)`, `(hostel, status)`, `(assigned_to, status)`, `due_at`.

### 5.5 Supporting models
- **TicketAttachment**: `ticket` FK, `file` (ImageField), `uploaded_by`.
- **TicketComment**: `ticket` FK, `author` FK, `body`, `is_internal` Bool.
- **TicketActivity** (audit log): `ticket` FK, `actor` FK null (null = system), `action` (CREATED, ASSIGNED, STATUS_CHANGED, ESCALATED, REASSIGNED, COMMENTED, REOPENED, CLOSED), `from_value`, `to_value`, `note`, `created_at`. **Append-only.**
- **Tag**: `name`, `color`.
- **SavedFilter**: `user` FK, `name`, `querystring`, `view` (list or kanban).
- **SLAPolicy**: `priority`, `level` (1 to 4), `hours`. Unique together on `(priority, level)`.
- **RoutingRule**: `hostel` FK, `category` FK, `level` (default 1), `assignee` FK User. Resolution order: (hostel + category) → (hostel only) → hostel's level-1 default → fallback to the Warden.
- **notifications.Notification**: `recipient` FK, `ticket` FK null, `verb`, `message`, `is_read`, `created_at`.

### 5.6 Routing and Escalation Logic (put in `tickets/services/`)
Keep business logic out of views. Create plain Python service modules:

- `routing.py` → `assign_initial(ticket)`: looks up `RoutingRule`, sets `assigned_to`, `current_level=1`, `status=ASSIGNED`, computes `due_at` from `SLAPolicy`, logs activity, sends notification.
- `escalation.py`
  - `escalate(ticket, actor=None, reason="")`: finds the next-level assignee (same hostel for L2, global for L3 and L4), updates `current_level`, `assigned_to`, `due_at`, logs `ESCALATED`, notifies old and new assignee and the reporter.
  - `check_overdue()`: for each active ticket where `due_at < now`: if `current_level < 4` call `escalate()`; else set `is_overdue=True`.
  - Management command `python manage.py run_escalations` calls `check_overdue()` (run every 10 minutes via cron or Celery beat).
- `status.py` → `change_status(ticket, new_status, actor)`: validates allowed transitions and permissions, sets timestamps, logs.
- `numbering.py` → race-safe ticket number generator (use `select_for_update` in a transaction).
- `notifications.py` → create in-app notifications; email hook is stubbed for later.

**Allowed status transitions**
```
OPEN → ASSIGNED → IN_PROGRESS ⇄ ON_HOLD → RESOLVED → CLOSED
                                   RESOLVED → (reporter reopens) → IN_PROGRESS
OPEN/ASSIGNED → REJECTED (staff, reason required)
```
A ticket moves to `CLOSED` when the hosteler confirms it, or automatically 72h after `RESOLVED`.

---

## 6. Project Structure

```
hostel_ticket_system/
├── manage.py
├── .env.example
├── .gitignore
├── README.md
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── pyproject.toml              # ruff / black / pytest config
├── config/                     # Django project package
│   ├── __init__.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       └── prod.py
├── apps/
│   ├── core/                   # shared utilities
│   │   ├── models.py           # TimeStampedModel
│   │   ├── permissions.py
│   │   ├── mixins.py           # RoleRequiredMixin, HtmxMixin
│   │   ├── templatetags/ui.py  # status_pill, priority_dot, time_ago
│   │   └── context_processors.py
│   ├── accounts/               # User, login/logout, profile
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   ├── hostels/                # Hostel, Block, Room + admin screens
│   ├── tickets/
│   │   ├── models.py
│   │   ├── forms.py
│   │   ├── filters.py          # django-filter FilterSets
│   │   ├── querysets.py        # visible_to(user)
│   │   ├── views/
│   │   │   ├── list.py
│   │   │   ├── kanban.py
│   │   │   ├── detail.py
│   │   │   ├── create.py
│   │   │   └── actions.py      # status/assign/escalate/comment (HTMX)
│   │   ├── services/
│   │   │   ├── routing.py
│   │   │   ├── escalation.py
│   │   │   ├── status.py
│   │   │   └── numbering.py
│   │   ├── management/commands/
│   │   │   ├── run_escalations.py
│   │   │   └── seed_demo_data.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   ├── dashboard/              # number cards + chart JSON endpoints
│   │   ├── views.py
│   │   ├── selectors.py        # aggregate queries
│   │   └── urls.py
│   └── notifications/
│       ├── models.py
│       ├── views.py
│       └── urls.py
├── templates/
│   ├── base.html
│   ├── components/             # _sidebar, _topbar, _status_pill, _card ...
│   ├── accounts/               # login.html, profile.html
│   ├── tickets/
│   │   ├── list.html
│   │   ├── _list_table.html    # HTMX partial
│   │   ├── kanban.html
│   │   ├── _kanban_card.html
│   │   ├── detail.html
│   │   ├── create.html
│   │   └── _activity.html
│   ├── dashboard/
│   │   ├── staff.html
│   │   └── hosteler.html
│   ├── hostels/
│   ├── notifications/
│   └── errors/                 # 403, 404, 500
├── static/
│   ├── css/
│   │   ├── tokens.css
│   │   ├── base.css
│   │   ├── components.css      # buttons, pills, tables, cards, forms
│   │   ├── layout.css          # sidebar, topbar, page header
│   │   ├── kanban.css
│   │   └── dashboard.css
│   ├── js/
│   │   ├── app.js              # htmx config, toasts, ⌘K search
│   │   ├── kanban.js           # SortableJS wiring
│   │   └── charts.js           # Chart.js builders
│   ├── img/
│   └── vendor/                 # htmx, alpine, chart.js, sortablejs (pinned, local)
├── media/                      # uploads (gitignored)
└── tests/                      # cross-app / end-to-end tests
```

**Conventions:** fat services, thin views; one responsibility per module; apps live in `apps/` and are registered as `apps.tickets`, etc.; no business logic in templates; no inline styles or colour values outside `tokens.css`.

---

## 7. URL Map

| URL | View | Who |
|---|---|---|
| `/` | Redirect by role (hosteler home or staff dashboard) | All |
| `/accounts/login/`, `/accounts/logout/` | Auth | All |
| `/accounts/profile/` | Profile | All |
| `/tickets/` | List view | All (scoped) |
| `/tickets/kanban/` | Kanban board | Staff |
| `/tickets/new/` | Raise ticket | Hosteler, Admin |
| `/tickets/<ticket_no>/` | Detail | Scoped |
| `/tickets/<ticket_no>/status/` (POST) | Change status | Staff, owner for close/reopen |
| `/tickets/<ticket_no>/assign/` (POST) | Reassign | Warden and above |
| `/tickets/<ticket_no>/escalate/` (POST) | Manual escalate | Staff |
| `/tickets/<ticket_no>/comment/` (POST) | Comment or internal note | Scoped |
| `/tickets/<ticket_no>/follow/` (POST) | Toggle follow | All |
| `/tickets/<ticket_no>/rate/` (POST) | Feedback | Reporter |
| `/tickets/filters/save/` (POST), `/tickets/filters/<id>/delete/` | Saved filters | All |
| `/tickets/bulk/` (POST) | Bulk actions | Staff |
| `/dashboard/` | Dashboard page | Scoped |
| `/dashboard/api/summary/`, `/api/by-category/`, `/api/resolution-time/`, `/api/trend/` | Chart JSON | Scoped |
| `/notifications/`, `/notifications/read/` (POST) | Notifications | All |
| `/manage/hostels/`, `/manage/rooms/`, `/manage/categories/`, `/manage/routing/`, `/manage/sla/`, `/manage/users/` | Admin management | Admin |
| `/admin/` | Django admin (backup tool) | Superuser |

---

## 8. Build Phases

Work through these in order. Each phase ends with a commit.

### Phase 0: Setup
- [ ] Create venv, install Django, `django-environ`, `django-filter`, `Pillow`, `pytest-django`, `factory_boy`, `ruff`, `black`.
- [ ] `django-admin startproject config .`, create `apps/` and generate all apps.
- [ ] Split settings into base/dev/prod; load `.env`.
- [ ] Set `AUTH_USER_MODEL = "accounts.User"` **before the first migration**.
- [ ] Configure static/media, templates dir, timezone `Asia/Kolkata`.
- [ ] Git init, `.gitignore`, pre-commit hooks.
- **Done when:** `runserver` boots and `pytest` runs (even with zero tests).

### Phase 1: Design System and Base Layout
- [ ] Write `tokens.css`, `base.css`, `components.css`, `layout.css` from Section 4.1.
- [ ] Build `base.html` with the icon rail, top bar, page header, breadcrumbs, toast area.
- [ ] Build reusable components: button variants, status pill, priority dot, avatar, card, table, form inputs, empty state, pagination.
- [ ] Create a temporary `/ui-kit/` page showing every component (remove or restrict before release).
- **Done when:** the UI kit page visually matches the reference style (light, dense, pastel pills, black primary button).

### Phase 2: Accounts and Roles
- [ ] Custom User model, migrations, admin registration.
- [ ] Login/logout with Roll No / Employee ID, profile and change-password pages.
- [ ] `RoleRequiredMixin`, `permissions.py`, post-login redirect by role.
- [ ] Management command to create demo users for each role.
- **Done when:** each role can log in and only sees allowed menu items; unauthorized URLs return 403.

### Phase 3: Hostels, Rooms, Categories, Config
- [ ] Models + admin-only management screens (list + create/edit) for Hostel, Block, Room, Category, SLAPolicy, RoutingRule, Tag.
- [ ] Seed default SLA table (Section 3.3) via data migration or seed command.
- **Done when:** an Admin can fully configure a hostel and its routing without touching Django admin.

### Phase 4: Ticket Core (Create, List, Detail)
- [ ] `Ticket`, `TicketAttachment`, `TicketComment`, `TicketActivity` models + migrations.
- [ ] `numbering.py` and `routing.py` services; auto-assign on create.
- [ ] Raise Ticket form (Section 4.7) with image upload validation.
- [ ] `TicketQuerySet.visible_to(user)` and its tests.
- [ ] List view with filter sidebar, top filter bar, sorting, pagination, HTMX partial refresh, URL-synced filters.
- [ ] Detail page with comments, internal notes, history timeline.
- **Done when:** a hosteler raises a ticket, it lands in the caretaker's list, and both can comment.

### Phase 5: Status Workflow and Kanban
- [ ] `status.py` service with transition rules and permission checks.
- [ ] Status-change actions from the detail page.
- [ ] Kanban board with SortableJS drag and drop and HTMX update.
- [ ] Hosteler close, reopen and rating flow; auto-close job after 72h.
- **Done when:** dragging a card changes status, logs activity, and illegal moves are rejected with a toast.

### Phase 6: Escalation Engine
- [ ] `escalation.py` (`escalate`, `check_overdue`) and `run_escalations` command.
- [ ] Manual escalate/reassign with required note.
- [ ] SLA countdown/progress bar component and escalation path widget on the detail page.
- [ ] Overdue flags in list and Kanban.
- **Done when:** a ticket past its SLA moves up a level automatically, the new assignee is notified, and a Level 4 breach is flagged Critical Overdue.

### Phase 7: Notifications
- [ ] `Notification` model, creation hooks in services.
- [ ] Bell dropdown (HTMX polling every 30s), notifications page, mark as read.
- [ ] Email notification stub (console backend in dev).
- **Done when:** assignment, escalation, status change, and new comments each create the right notifications.

### Phase 8: Dashboards
- [ ] `selectors.py` aggregate queries scoped by role.
- [ ] Staff dashboard (number cards, bar charts, tables) per Section 4.5.
- [ ] Hosteler home per Section 4.8.
- [ ] Date range and Weekly/Monthly controls wired to chart endpoints.
- **Done when:** numbers on the dashboard match the list view counts for the same filters.

### Phase 9: Extras and Polish
- [ ] Saved filters, tags, follow/heart, bulk actions.
- [ ] Global search (`⌘/Ctrl + K`) over ticket ID, title, reporter.
- [ ] Responsive layouts, loading skeletons, empty states, custom 403/404/500.
- [ ] CSV export of the filtered list.
- **Done when:** the app is usable end to end on desktop and mobile widths.

### Phase 10: Hardening and Deployment
- [ ] Security pass (Section 10), N+1 query audit with `select_related`/`prefetch_related`.
- [ ] `seed_demo_data` command for demos.
- [ ] Prod settings (PostgreSQL, `DEBUG=False`, `ALLOWED_HOSTS`, static via WhiteNoise or Nginx, media storage).
- [ ] Gunicorn + Nginx config, cron/Celery beat for `run_escalations`.
- [ ] README with setup, env vars, roles, and screenshots.
- **Done when:** deployed (or Docker-composed) instance runs the full flow with demo data.

---

## 9. Testing Plan

| Area | Tests |
|---|---|
| Models | Ticket numbering (including concurrency), SLA lookup, routing fallback order |
| Permissions | `visible_to` for each role; every action URL returns 403 for disallowed roles |
| Services | Status transition matrix (allowed and rejected); `escalate` picks the right next-level user; `check_overdue` is idempotent; Level 4 flagged only |
| Views | List filters and sorting; HTMX partial returns the table only; Kanban move endpoint |
| Dashboard | Aggregates match seeded data; role scoping |
| UI smoke | Login, raise ticket, change status, escalate (Playwright or Django test client) |

Target **80%+ coverage** on `services/`, `querysets.py`, and `permissions.py`. Use `factory_boy` factories for User (all roles), Hostel, Category, Ticket. Freeze time with `freezegun` for escalation tests.

---

## 10. Security and Quality Checklist
- CSRF on all POST (include token in HTMX via `hx-headers`).
- Object-level permission check in **every** detail/action view (never trust the URL).
- Validate uploads: type (images only), size (5 MB), rename files, serve from `media/` only.
- Rate-limit login (`django-axes` or similar); strong password validators.
- Escape all user content; no `|safe` on user text.
- Internal notes never leak to hostelers (filter in the queryset, not the template).
- Audit log (`TicketActivity`) is append-only; no edit/delete UI.
- `DEBUG=False`, secure cookies, HSTS in production.
- Database indexes as listed in Section 5.4; avoid N+1 queries.

---

## 11. Seed / Demo Data (`seed_demo_data`)
- 2 hostels (Boys A, Girls B), 2 blocks each, 20 rooms each.
- Users: 1 Admin, 1 Chief Warden, 1 Warden per hostel, 2 Caretakers per hostel, 15 Hostelers.
- 9 categories with routing rules and the default SLA table.
- 60 tickets across all statuses, priorities, and levels, with comments and activity so the list, Kanban, and dashboard look realistic.

---

## 12. Rules for the AI Coding Agent (Antigravity)
1. Follow the phases in order; announce the phase at the start of each task.
2. Do **not** introduce Bootstrap, Tailwind, React, or any SPA framework. Use the stack in Section 2.
3. All colours, radii, and fonts come from `tokens.css`. Never hardcode them elsewhere.
4. Business logic lives in `services/`; views stay thin; templates have no logic beyond display.
5. Every new model gets a migration, admin registration, and a factory.
6. Every service function gets unit tests in the same PR/commit.
7. UI must match Section 4 (ERPNext-style: light, dense 13px type, pastel status pills, black primary button, icon rail, filter sidebar, pastel Kanban columns).
8. Ask before adding any dependency not listed in Section 2.
9. Keep commits small with clear messages (`feat:`, `fix:`, `test:`, `chore:`).
10. At the end of each phase, run `pytest`, `ruff check`, and `python manage.py check`, and fix everything before continuing.

---

## 13. Definition of Done (v1)
- [ ] Hosteler can raise, track, comment on, close, reopen, and rate tickets.
- [ ] Tickets auto-route to the right Level 1 staff and auto-escalate on SLA breach through all four levels.
- [ ] Staff have List, Kanban, and Dashboard views scoped by role.
- [ ] Full audit history on every ticket.
- [ ] In-app notifications for all key events.
- [ ] UI matches the reference style across all screens and works on mobile widths.
- [ ] Tests pass, security checklist complete, README written, demo data seeds cleanly.
