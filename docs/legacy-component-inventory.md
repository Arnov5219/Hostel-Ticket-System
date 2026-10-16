# Legacy Component and Template Inventory (Phase F0)

This inventory audits templates across the application, identifying legacy classes, inline styling anti-patterns, and mapping them to standardized components.

---

## 1. Templates Audit & Component Mapping

| Template | Current Issues & Legacy Patterns | Replacement Component & Plan Section |
|---|---|---|
| `templates/base.html` | Hard-coded theme segmented control in dropdown with "Auto" label; duplicate `Raise Ticket` action in page header default block; desktop breadcrumbs & `⌘K` badge visible on mobile viewports; inline script for theme. | `theme_switcher.html` partial (5.1/5.2); clean single mobile header without breadcrumbs/`⌘K`; move theme controller to `static/js/theme.js`. |
| `templates/components/_bottom_nav.html` | Ad-hoc theme segmented control labeled "Auto"; active states checking both `is_kanban` and `current_section == 'tickets'`; hardcoded inline styles; missing safe-area padding; hosteler has "My Tickets", "News", "More" instead of Home, Tickets, Raise, Notices, Profile. | Standard bottom bar (4, 5.2); `theme_switcher.html` in sheet; strictly single `nav_section` active state; D1/D2 navigation matrix. |
| `templates/components/_sidebar.html` | Uses legacy `--accent` tokens; some labels out of sync with D1/D2. | Standardized navigation items and tokens (`--primary`). |
| `templates/accounts/login.html` | Native checkbox; default button styles for tabs; separate inline theme toggle button; no shared theme switcher; demo disclosure could have better contrast in dark mode. | Segmented control for tabs (5.7); styled checkbox component; hero brand card; standard theme toggle; compact demo account chips. |
| `templates/accounts/profile.html` | Avatar initials white-on-white; default browser button styling for Appearance cards; missing "Log out" button on mobile/desktop; Django default form field labels ("Old password"); unstyled button corners. | Shared `theme_switcher.html` (5.5); avatar component with legible tints; standardized filled inputs; danger-ghost Log Out button; correct password form labels. |
| `templates/tickets/create.html` | `raise-submit-bar` sticky position overlaps description field; category chips look like raised native buttons with scrollbars; urgency cards flat with low contrast; duplicate Raise Ticket in header. | Inline form submit button (D4, 5.6); category choice chips pill component; 2x2 option cards with contrast pills; remove header CTA. |
| `templates/tickets/kanban.html` | Active status tab invisible on dark mode (white on white); tabs not two-way synced with horizontal scroll; drag hint displayed on touch screens; no empty state when column count is 0; search input icon overlaps text. | Sync status chips with `IntersectionObserver` (5.4); input with inset icon; empty state component per column; hide drag hint on mobile; clean snap scroll. |
| `templates/tickets/list.html` | Desktop table vs mobile card list duplication; filter chips need consistent styling in both themes. | Standard filter chips and unified responsive ticket cards. |
| `templates/tickets/detail.html` | Action buttons have varied radii; status timeline and comment inputs need dark mode surface review. | Standardized buttons, filled textarea, and dark mode tokens for timeline badges. |
| `templates/announcements/list.html` | Title is "Announcements" instead of "Notices"; unstyled tab buttons; empty state needs standard component. | Title "Notices" (D3, 5.8); segmented tabs `All | Unread | Pinned`; standard empty state. |
| `templates/announcements/detail.html` | Severity banner tokens need full dark mode verification. | Standard notice severity tokens (`--notice-*`). |
| `templates/notifications/list.html` | Notification items need standard event icons and clear unread tint. | Notification list component (5.8). |
| `templates/dashboard/hosteler.html` | KPI cards and SLA hero card need dark mode review. | Standard KPI cards and `--primary-soft` dark tokens. |
| `templates/dashboard/staff.html` | Dashboard charts must dynamically rebuild on `themechange`. | `charts.js` token resolution with updated `#2F6FEB` / `#2563EB` brand colors. |

---

## 2. Token Replacements

| Legacy / Deprecated Token | Standard Replacement |
|---|---|
| `--accent` | `--primary` |
| `--accent-hover` | `--primary-hover` |
| `--accent-light` | `--primary-soft` |
| `--accent-glow` | `var(--ring)` or `rgba(37, 99, 235, 0.15)` |
| `--ann-*-*` | `--notice-*-*` |
| `#1D5FB4` (old blue) | `#2563EB` (light) / `#2F6FEB` (dark) |
| `#3B82F6` (dark primary) | `#2F6FEB` (for AA 4.5:1 text contrast) |
| `--white` text on `--ink` | `--text-inverse` or theme-adaptive token |
