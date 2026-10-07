# UI Component & Screen Audit

This document maps each UI element to its current CSS selector and template file across the application.

| UI Element / Component | Current CSS Selector | Primary File / Template | Notes & Improvements Needed |
|---|---|---|---|
| **App Shell & Background** | `body`, `.app-shell`, `.app-main` | `templates/base.html`, `static/css/layout.css` | Needs `.app-background` layered mesh/glow base. |
| **Sidebar Rail** | `.app-rail`, `.rail-item`, `.rail-logo` | `templates/components/_sidebar.html`, `static/css/layout.css` | Fix B-02 tooltip positioning. Group navigation with dividers. |
| **Top Navigation Bar** | `.app-topbar`, `.topbar-search`, `.user-avatar` | `templates/components/_top_bar.html`, `static/css/layout.css` | Add real breadcrumbs, user menu dropdown, role hint. |
| **Toast Notifications** | `.toast`, `.toast-container` | `templates/base.html`, `static/css/components.css` | Fix B-09: stack at bottom-right, auto-dismiss in 4s, no overlap. |
| **Tooltip** | `.rail-tooltip` | `templates/components/_sidebar.html`, `static/css/layout.css` | Unify into global `[data-tooltip]` pattern anchored properly. |
| **Data Tables** | `.app-table`, `.table-container` | `templates/tickets/_list_table.html`, `static/css/components.css` | 12px sentence-case headers, 44-46px row heights, sticky headers. |
| **Recent Tickets (Hosteler)** | `.app-table` inside card | `templates/dashboard/hosteler.html` | Fix B-01: use full width `.data-table`, fix misalignment and wrapping. |
| **Hosteler Header / Welcome** | `.card` inline flex | `templates/dashboard/hosteler.html` | Fix B-08: single primary CTA "Raise ticket", clean meta line. |
| **Stat Cards** | `.stat-card`, `.stat-value`, `.stat-label` | `templates/dashboard/staff.html`, `static/css/dashboard.css` | 28px numbers, sentence case, contextual icon chip, clean hint. |
| **Dashboard Charts** | `canvas#trendChart`, `canvas#categoryChart` | `templates/dashboard/staff.html`, `static/js/dashboard.js` | Fix B-05 (integer ticks), Fix U-13 (slate/blue, no brown bars). |
| **Status Pill** | `.status-pill` | `apps/core/templatetags/ui.py`, `static/css/components.css` | Add 6px leading dot, 11.5px typography, rounded pill. |
| **Level Chip** | `.level-badge`, `.role-badge` | `apps/core/templatetags/ui.py`, `static/css/components.css` | Consistent shape L1 blue, L2 amber, L3 orange, L4 red-pink. |
| **Priority Marker** | `.priority-dot` | `apps/core/templatetags/ui.py`, `static/css/components.css` | Dot + label (Urgent red, High orange, Medium blue, Low gray). |
| **SLA Indicator** | `.sla-bar-container`, `.sla-bar` | `templates/tickets/_list_table.html`, `static/css/components.css` | Fix U-07: thin bar for active tickets, checkmark for resolved/closed. |
| **Kanban Board** | `.kanban-board`, `.kanban-col`, `.kanban-card` | `templates/tickets/kanban.html`, `static/css/kanban.css` | Fix B-07 (due copy), Fix U-16 (filter bar, dashed unassigned avatar). |
| **Notification Center** | `.card`, `.notification-item` | `templates/notifications/list.html`, `static/css/components.css` | Fix B-06 (humanize status), Fix U-15 (narrow centered container). |
| **Admin Sub-navigation** | None (ad-hoc buttons) | `templates/hostels/*.html`, `templates/tickets/manage_routing.html` | Fix U-09: shared black-active segmented pill navigation bar. |
| **Hostel Management** | `.app-table`, modal forms | `templates/hostels/manage_hostels.html` | Fix B-03 (clean single values), quiet actions, 1200px container. |
| **Staff Management** | `.app-table`, modals | `templates/hostels/manage_staff.html` | Fix U-11/U-12: quiet deactivation, neutral active ticket counts. |
| **Hostel Responsibility** | `.app-table`, info card | `templates/hostels/manage_responsibility.html` | Shared info callout, 1200px max-width container. |
| **Routing & SLA Policies** | `.segmented-nav`, tables | `templates/tickets/manage_routing.html` | Fix U-10 (grouped by hostel with `<details>`, quiet trash icon). |
| **Auth / Login Page** | Form on app-shell | `templates/accounts/login.html` | Fix B-04: bare layout without sidebar/topbar. Fix U-18 autofill. |
| **Ticket Create Page** | Form in `.card` | `templates/tickets/create.html` | Centered 640px card, styled selects, drag-drop attachment styling. |
| **Ticket Detail Page** | 2-column detail grid | `templates/tickets/detail.html` | Conversation layout, staff action panel, metadata card with SLA. |
| **User Profile Page** | Form in `.card` | `templates/accounts/profile.html` | Centered card, avatar preview, tabbed profile/password sections. |
| **Error Pages (403, 404, 500)** | Custom error views | `templates/core/403.html`, `404.html`, `500.html` | Bare auth layout, muted large code, clean return button. |
