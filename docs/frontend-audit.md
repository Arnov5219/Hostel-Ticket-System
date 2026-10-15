# Frontend UI/UX Audit (v3) - Phase F0 Inspection

This audit maps every UI component, screen, layout selector, and content string across the application according to `plan/FRONTEND_UI_UX_IMPROVEMENT_PLAN_V3.md`.

---

## 1. File Locations & Architecture Inventory

### Base & Shared Templates
- **Base Shell**: `templates/base.html`
- **Navigation Partials**:
  - `templates/components/_sidebar.html` (Desktop 232px labeled sidebar, collapsible to 64px rail)
  - `templates/components/_topbar.html` (Top navigation bar with breadcrumbs, search, user menu)
  - `templates/components/_bottom_nav.html` (Mobile bottom bar with 5 slots max + More sheet)
  - `templates/components/_page_header.html` (Page title + subtitle + single primary action)
- **Component Partials**:
  - `templates/components/_status_pill.html`
  - `templates/components/_priority_dot.html`
  - `templates/components/_empty_state.html`
  - `templates/components/_pagination.html`
- **Page Templates**:
  - `templates/accounts/login.html` (Bare auth layout, login form)
  - `templates/accounts/register.html` (Create account form)
  - `templates/dashboard/hosteler.html` (Hosteler home portal)
  - `templates/dashboard/staff.html` (Admin / Warden operational dashboard)
  - `templates/tickets/create.html` (Raise ticket intake form)
  - `templates/tickets/detail.html` (Ticket details, SLA progress, updates thread, audit timeline)
  - `templates/tickets/list.html` & `templates/tickets/_list_table.html` (Ticket list table & mobile cards)
  - `templates/tickets/kanban.html` & `templates/tickets/_kanban_card.html` (Kanban triage board)
  - `templates/accounts/profile.html` (User profile & theme settings)
  - `templates/core/ui_kit.html` (Design tokens & component gallery)

### CSS Files & Load Order
1. `static/css/tokens.css` (Design tokens: `--primary`, `--bg-app`, status & priority colors, radii, shadows)
2. `static/css/base.css` (Resets, base typography Inter 13px, form element defaults)
3. `static/css/layout.css` (App container, sidebar 232px/64px, topbar, mobile bottom bar, grid wrappers)
4. `static/css/components.css` (Cards, panels, stat cards, tables, status pills, buttons, modals, dropdowns)
5. `static/css/dashboard.css` (Dashboard widgets, notice rails, emergency box)
6. `static/css/kanban.css` (Kanban columns, cards, status strip, mobile drag)

### JS Entry Points
- `static/vendor/htmx.min.js` (HTMX for partial swaps and live updates)
- `static/vendor/alpine.min.js` (Client-side toggles, dropdowns, modal state)
- `static/vendor/lucide.min.js` (Consistent monochrome outline icons)
- `static/vendor/chart.min.js` (Chart.js for operational analytics)
- `static/js/app.js` (Theme switching, search shortcut, command palette, toast auto-dismiss)
- `static/js/charts.js` (Chart.js configuration: Inter font, zero baseline, `--chart-*` palette)
- `static/js/kanban.js` (Drag-and-drop, touch long-press 200ms, "Move to..." action sheet)

### Navigation Source of Truth
- `apps/core/navigation.py`: `nav_for(user)` drives sidebar, tablet rail, mobile bar, and More sheet.

---

## 2. Horizontal Overflow Offenders (G-02)

| Screen / Component | Element / Current Selector | Root Cause of Overflow at 375px | Required Fix |
|---|---|---|---|
| **All Review Pages** | `.review-nav-bar` | Fixed `white-space: nowrap` links row stretching >750px | Remove completely from product (G-01). |
| **Hosteler Dashboard** | Two-column grid (`2.4fr 1fr`) | Desktop column ratio doesn't stack on phone | Stack to 1 column below 1024px; `min-width: 0` on children. |
| **Hosteler Dashboard** | Recent tickets `.data-table` | 7 table columns requiring 700px+ width | 5-column table with scroll wrapper on desktop; transform to card list on mobile (<768px). |
| **Hosteler Dashboard** | Summary Stat cards | 4-column grid (`repeat(4, 1fr)`) | 2×2 grid on mobile (<768px) with compact padding. |
| **Create Ticket** | Form + Guidelines Grid (`2.5fr 1fr`) | Desktop grid doesn't collapse | Single column on phones; guidelines stack below form. |
| **Create Ticket** | Category Grid | Cards with fixed min-width causing single-column 7-row stretch | 2 columns on phones (`grid-template-columns: repeat(2, 1fr)`). |
| **Ticket Details** | Detail Grid (`2.4fr 1.1fr`) | Desktop two-column grid pushes sidebar offscreen | Single column on phones: Header → SLA → Description → Authority → Updates → History. |
| **Ticket Details** | Ticket Header | `#HTL-2026-00089` wrapping across hyphens | Add `white-space: nowrap; font-family: var(--font-mono);` (D8). |
| **Admin Dashboard** | Filter Toolbar | Flex row with multi-selects and long labels | Collapse to "Filters (n)" button opening bottom sheet on mobile. |
| **Admin Dashboard** | Charts Row (`2fr 1fr`) | Two-column grid doesn't stack | Stack vertically on mobile; Chart canvas `max-width: 100%`. |
| **Admin Dashboard** | Hostel Turnaround Table | 8 table columns | Internal table horizontal scroll or card list on mobile. |
| **Kanban Board** | `.kanban-board` | 5 fixed columns (`repeat(5, 230px+)`) | Flexible `repeat(5, minmax(240px, 1fr))` on desktop; sticky status tab strip + 88vw single column on mobile. |
| **Login Card** | `.login-card` | Missing side padding or fixed min-width | `max-width: 400px; width: 100%; margin: 0 16px; min-height: 100dvh`. |

---

## 3. Product Rules & Content Contradictions (G-03)

| In Current UI / Samples | Correct Product Value | Target Template / File |
|---|---|---|
| Rooms, Floors, Blocks ("Room 304", "Floor 3", "Room No. *") | **Hostel only** (`BH-1` to `BH-12`). No room/floor pickers. Helper text: "Say exactly where the problem is (e.g. washroom or corridor)". | `templates/tickets/create.html`, `templates/tickets/detail.html`, `templates/dashboard/hosteler.html` |
| "Issue is in a shared or common area" checkbox | **Removed** (hostel-only residence model). | `templates/tickets/create.html` |
| Old hostel names ("Boys Hostel A (BH-A)", "GH-B") | **Standard codes `BH-1` to `BH-12`**. Filters say "All hostels (12)". | All templates & seed data |
| Sidebar "Hostel Blocks (4)" | **Hostels** | `apps/core/navigation.py`, `templates/components/_sidebar.html` |
| Sidebar "SLA & Categories" | **Ticket settings** (Categories & Tags only) | `apps/core/navigation.py`, `templates/tickets/manage_settings.html` |
| Sidebar "Trash & Purge" | **Trash** (view, restore only; no purge UI button) | `apps/core/navigation.py`, `templates/tickets/trash.html` |
| Warden sidebar "Campus Analytics" | **Hostel dashboard** (scoped to warden's hostel) | `apps/core/navigation.py` |
| 7 categories in picker | **9 agreed categories**: Electrical, Plumbing / Water, Internet / Wi-Fi, Cleaning / Housekeeping, Furniture, Mess / Food, Security, Maintenance, Other. | `templates/tickets/create.html`, `apps/tickets/models.py` |
| Hardcoded SLA hours ("Low 72h, Medium 48h...") | **Shared SLA table**: Urgent 2h, High 8h, Medium 24h, Low 48h (Level 1). | `templates/tickets/create.html`, `templates/tickets/detail.html` |
| Login "Login ID / Email" without sign-up | "Roll number or staff ID", tabs for **Sign in \| Create account**, "Remember me" off by default. | `templates/accounts/login.html` |
| Inconsistent CTA names ("Report an Issue", "Create Ticket", "Log Staff Ticket") | Single CTA: **Raise ticket** everywhere. One primary CTA per page. | All templates |

---

## 4. UI Elements to Selectors & Token Mapping (Sections 4 to 6)

| UI Element | Target Selector | Token / Rule | Target File |
|---|---|---|---|
| **Primary Color** | `.btn-primary`, `.nav-item.active`, `a` | `--primary: #1D5FB4; --primary-hover: #184E96; --primary-soft: #E8F1FD;` | `static/css/tokens.css` |
| **Status Pill** | `.status-pill`, `.status-pill--open`, etc. | 12px pill, 4×10px padding, leading 6px dot, muted pastel background + dark text. | `static/css/components.css` |
| **Priority Marker** | `.priority-dot` | 8px dot + label, 13px sentence case (no box, no uppercase). | `templates/components/_priority_dot.html` |
| **Level Chip** | `.level-chip` | `L1` to `L4`, 12px, `--bg-subtle`, 1px border. | `static/css/components.css` |
| **Ticket Number** | `.ticket-id` | `HTL-2026-00089`, 13px tabular numbers, `white-space: nowrap`. | `static/css/components.css` |
| **Custom Controls** | `.form-select`, `.form-input`, `.form-radio-card` | 40px height (44px touch), custom SVG chevron, `--border-strong`, focus ring `0 0 0 3px rgba(29, 95, 180, 0.25)`. | `static/css/components.css` |
| **Desktop Sidebar** | `.app-sidebar` | 232px labeled sidebar, collapsible to 64px rail, group titles, active primary-soft background. | `static/css/layout.css` |
| **Mobile Bottom Bar** | `.mobile-bottom-bar` | 5 slots max (Home, Tickets, + Raise, News/Alerts, More). Reserves safe area padding. | `templates/components/_bottom_nav.html`, `static/css/layout.css` |
| **Tables** | `.app-table`, `.table-card` | 52px row height, clickable rows, no redundant "View" button, sentence-case headers. | `static/css/components.css` |
| **Charts** | `canvas#chart-volume`, `canvas#chart-category` | Inter font, zero baseline on Y-axis, `--chart-1..6` palette, light dashed gridlines. | `static/js/charts.js` |
| **Kanban Board** | `.kanban-board`, `.kanban-column` | 5 columns (`minmax(240px, 1fr)`), viewport height stretch, mobile status tab strip + "Move to..." menu. | `static/css/kanban.css` |
| **Review Shell & Hub** | `.review-nav-bar`, `frontend_samples/` | **Removed from product**. Dev component gallery kept at `/dev/ui-kit/` under `DEBUG`. | Remove `frontend_samples/` |
