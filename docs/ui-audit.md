# UI Component & Screen Audit (Completed v2)

This document maps each UI element to its CSS selector, template file, and status across the application. All phases (0 through 9) are fully implemented and verified on branch `ui/v2`.

| UI Element / Component | Current CSS Selector | Primary File / Template | Resolution & Implementation Status |
|---|---|---|---|
| **App Shell & Background** | `.app-background`, `.app-shell`, `.app-main` | `templates/base.html`, `static/css/layout.css` | **Completed**: Layered dot-grid mesh + subtle radial glows, glass surface containers. |
| **Sidebar Rail** | `.app-rail`, `.rail-item`, `.rail-logo` | `templates/components/_sidebar.html`, `static/css/layout.css` | **Completed (Fix B-02)**: Anchored tooltip positioning, clean navigation dividers. |
| **Top Navigation Bar** | `.top-bar`, `.breadcrumbs`, `.user-menu` | `templates/base.html`, `static/css/layout.css` | **Completed (Fix U-02)**: Breadcrumb slot blocks in base layout, user-menu dropdown with role/logout. |
| **Toast Notifications** | `.toast-container`, `.toast` | `templates/base.html`, `static/css/layout.css` | **Completed (Fix B-09)**: Fixed bottom-right toast stack with 4s auto-dismiss, no overlay blocking. |
| **Data Tables** | `.app-table`, `.table-container` | `templates/tickets/_list_table.html`, `static/css/components.css` | **Completed**: Sentence-case headers, 12px tabular IDs, subtle row hover tint, sticky headers. |
| **Recent Tickets (Hosteler)** | `.app-table` | `templates/dashboard/hosteler.html` | **Completed (Fix B-01)**: Full-width data table, aligned columns, no awkward wrapping. |
| **Hosteler Header / Welcome** | Glass card + primary button | `templates/dashboard/hosteler.html` | **Completed (Fix B-08)**: Single primary CTA "Raise ticket", clean meta line, clickable stat cards. |
| **Stat Cards** | `.stat-card`, `.stat-value`, `.stat-label` | `templates/dashboard/staff.html`, `static/css/components.css` | **Completed**: 28px numbers, sentence case, contextual icon chip, clean hint, hover lift. |
| **Dashboard Charts** | `canvas#chart-trend`, `canvas#chart-category` | `templates/dashboard/staff.html`, `static/js/charts.js` | **Completed (Fix B-05, U-13)**: Integer ticks only (`precision: 0`), blue-slate category series (no brown). |
| **Status Pill** | `.status-pill` | `apps/core/templatetags/ui.py`, `static/css/components.css` | **Completed**: 6px leading dot, 11.5px typography, rounded pill tokens. |
| **Level Chip** | `.level-chip`, `.level-badge` | `apps/core/templatetags/ui.py`, `static/css/components.css` | **Completed**: Compact L1–L4 chips with clear hierarchical color progression. |
| **Priority Marker** | `.priority-dot`, `.prio-dot` | `apps/core/templatetags/ui.py`, `static/css/components.css` | **Completed**: Dot + label (Urgent red, High orange, Medium blue, Low gray). |
| **SLA Indicator** | `.sla-bar-container`, `.sla-done` | `templates/tickets/_list_table.html`, `static/css/components.css` | **Completed (Fix U-07)**: Thin bar for active tickets, checkmark for resolved/closed (no green bar). |
| **Kanban Board** | `.kanban-board`, `.kanban-column`, `.kanban-card` | `templates/tickets/kanban.html`, `static/css/kanban.css` | **Completed (Fix B-07, U-16)**: Flexible columns (`flex: 1 1 260px`), `kanban_time_copy`, dashed circle unassigned avatar. |
| **Notification Center** | Glass card, `.empty-state` | `templates/notifications/list.html` | **Completed (Fix B-06, U-15)**: Centered 760px container, event icons, `humanize_status` for verbs. |
| **Admin Sub-navigation** | `.admin-subnav`, `.admin-subnav__item` | `templates/components/_admin_subnav.html`, `static/css/components.css` | **Completed (Fix U-09)**: Segmented dark-active navigation across Hostels, Staff, Responsibility, Routing. |
| **Hostel Management** | `.app-table`, `.page--narrow` | `templates/hostels/manage_hostels.html` | **Completed (Fix B-03, U-11)**: 1200px container, clean code chips, quiet row actions. |
| **Staff Management** | `.app-table`, `.page--narrow` | `templates/hostels/manage_staff.html` | **Completed (Fix U-11, U-12)**: Danger-ghost deactivation, neutral active ticket numbers (amber only if >=6). |
| **Hostel Responsibility** | `.info-callout`, `.page--narrow` | `templates/hostels/manage_responsibility.html` | **Completed**: Shared info callout component, 1200px max-width container. |
| **Routing & SLA Policies** | `.segmented-nav`, `<details>` groups | `templates/tickets/manage_routing.html` | **Completed (Fix U-10)**: 4-step inline assignment order flow, collapsible hostel groups, quiet trash icon. |
| **Auth / Login Page** | Bare auth card layout | `templates/accounts/login.html` | **Completed (Fix B-04, U-18)**: No sidebar/topbar shell, show/hide password toggle, autofill fix, collapsed demo accounts. |
| **Ticket Create Page** | Centered 640px card | `templates/tickets/create.html` | **Completed**: Segmented priority control with colored active state, file dropzone counter. |
| **Ticket Detail Page** | 2-column detail grid | `templates/tickets/detail.html` | **Completed**: Conversation layout, staff actions, metadata card with SLA and L1–L4 tier path. |
| **Error Pages (403, 404, 500)** | Custom error views | `templates/core/403.html`, `404.html`, `500.html` | **Completed**: Bare auth layout inheritance, clean return button. |
| **Responsive & Accessibility** | CSS Media queries, `:focus-visible` | `static/css/layout.css` | **Completed**: 1440/1024/768/375px responsive adaptations, `prefers-reduced-motion` support. |

## Verification Summary
- **Django Check:** `python manage.py check` reports 0 issues.
- **PyTest Suite:** All 44 tests pass.
- **Backend Integrity:** `git diff main..ui/v2` confirms 0 changes to database models, business logic, URLs, routing, or migrations.
