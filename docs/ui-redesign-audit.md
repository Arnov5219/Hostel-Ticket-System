# HostelFlow UI Redesign Audit & Mapping

> Phase U0: Comprehensive mapping of the 6 HostelFlow mockups to Django templates, selectors, data models, and implementation status.

| Mockup Screen | Component / Element | Current Template / View | Data Source / Selector | Status / Implementation Note |
|---|---|---|---|---|
| **Global Shell** | Brand & Logo | `templates/base.html`, `templates/includes/sidebar.html` | `settings.SITE_NAME = "HostelFlow"`, Building Lucide icon | Active; standardized across all roles |
| **Global Shell** | Bottom Navigation Bar | `templates/base.html`, `apps/core/navigation.py` | `nav_for(user).mobile_bar_items` | Active; raised circular FAB for hosteler |
| **Global Shell** | Sidebar & Topbar | `templates/base.html`, `layout.css` | `nav_for(user).sidebar_items` | Active; desktop collapsible labeled sidebar |
| **Mockup 1: Hosteler Home** | Brand Header (Avatar, Bell, Hostel code) | `templates/core/dashboard.html` | `request.user`, `request.user.hostel` | Hosteler greeting + hostel code pill |
| **Mockup 1: Hosteler Home** | "Raise new ticket" Hero CTA | `templates/core/dashboard.html` | Link to `tickets:create` | Large 52px primary button with glow |
| **Mockup 1: Hosteler Home** | Latest Notice Banner | `templates/core/dashboard.html` | `Announcement.objects.active()` | Severity-tinted card; urgent first |
| **Mockup 1: Hosteler Home** | 2×2 KPI Grid | `templates/core/dashboard.html` | `Ticket.objects.filter(reporter=user)` | Total, Open, In Progress, Resolved |
| **Mockup 1: Hosteler Home** | Caretaker Card | `templates/core/dashboard.html` | `user.hostel.caretaker` (`Responsibility`) | Caretaker name, avatar, `tel:` call button |
| **Mockup 1: Hosteler Home** | Recent Tickets List & Filter Chips | `templates/core/dashboard.html` | Recent 5 tickets + HTMX status filters | Status chips + full-width ticket cards |
| **Mockup 2: Login & Register** | Gradient Hero Card & Tabs | `templates/accounts/login.html` | Frontend toggle (Resident / Staff) | Segmented tab switch, filled input fields |
| **Mockup 2: Login & Register** | Demo Accounts Disclosure | `templates/accounts/login.html` | Development mode demo chips (`L0`..`L5`) | Preserved for testability |
| **Mockup 2: Login & Register** | Register Form | `templates/accounts/register.html` | `RegistrationForm` | Name, roll, password, hostel select |
| **Mockup 3: User Profile** | Profile Info Card | `templates/accounts/profile.html` | `User` model, role chip, initials avatar | Full name, email, phone with validation |
| **Mockup 3: User Profile** | Change Password Card | `templates/accounts/profile.html` | `PasswordChangeForm` | Current, new, confirm password + tips |
| **Mockup 3: User Profile** | Residence Details Card | `templates/accounts/profile.html` | `user.hostel` | Hostel name, code, change modal |
| **Mockup 3: User Profile** | Theme Selector | `templates/accounts/profile.html` | Alpine / local storage / `Theme` model | Light, Dark, System selector |
| **Mockup 4: Staff Dashboard** | Immediate Action Alert | `templates/dashboard/*.html` | Overdue / escalated ticket count | Red alert banner with link to escalated list |
| **Mockup 4: Staff Dashboard** | 2×2 KPI Cards | `templates/dashboard/*.html` | Role-filtered tickets | Semantic colored labels, large 28px numbers |
| **Mockup 4: Staff Dashboard** | Category Breakdown | `templates/dashboard/*.html` | Category counts by hostel/campus | Segmented flex bar + legend |
| **Mockup 4: Staff Dashboard** | Hostel Performance Cards | `templates/dashboard/*.html` | Multi-hostel queryset (Dean / Chief Warden) | SLA pill, Total, Active, Overdue stats |
| **Mockup 5: Raise Ticket** | Hostel Card | `templates/tickets/create.html` | `user.hostel` with different hostel switch | Hostel code & change option |
| **Mockup 5: Raise Ticket** | Category Selector | `templates/tickets/create.html` | `Category.objects.all()` | Scrolling chips with icons |
| **Mockup 5: Raise Ticket** | Urgency Radio Cards | `templates/tickets/create.html` | Low, Medium, High, Urgent | 2×2 grid with SLA deadline indicator |
| **Mockup 5: Raise Ticket** | Description & Tip Callout | `templates/tickets/create.html` | Form field + character counter | Tip callout with icon |
| **Mockup 5: Raise Ticket** | Attachment Tiles | `templates/tickets/create.html` | Multi-file dropzone + camera capture | Photo thumbnails + remove button |
| **Mockup 6: Ticket Detail** | SLA Hero Card | `templates/tickets/detail.html` | `ticket.due_at`, `ticket.sla_status` | Tabular countdown + progress bar |
| **Mockup 6: Ticket Detail** | 4-step Lifecycle Stepper | `templates/tickets/detail.html` | Step 1 (Created), 2 (Assigned), 3 (Progress), 4 (Resolved) | Vertical stepper with checkmarks & active pulse |
| **Mockup 6: Ticket Detail** | Assigned Personnel Card | `templates/tickets/detail.html` | `ticket.assigned_to` | Avatar, role, call button |
| **Mockup 6: Ticket Detail** | Description & Evidence Lightbox | `templates/tickets/detail.html` | `ticket.description`, `ticket.attachments` | Clean card + attachment gallery |
| **Mockup 6: Ticket Detail** | Updates & Activity Stream | `templates/tickets/detail.html`, `_activity.html` | `Comment.objects.filter(ticket=ticket)` | Private notes vs hosteler updates |
| **Mockup 6: Ticket Detail** | Role Action Bottom Bar / Bar | `templates/tickets/detail.html` | Hosteler close/reopen; Staff status/escalate | Sticky responsive action bar |
