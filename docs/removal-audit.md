# Removal Audit (Phase X0)

## 1. Rooms & Blocks
- **Routes to remove (return 404)**:
  - `/manage/rooms/` (`hostels:manage_rooms`)
  - `/manage/rooms/create/` (`hostels:create_room`)
  - `/manage/rooms/<int:room_id>/edit/` (`hostels:edit_room`)
  - `/manage/rooms/<int:room_id>/toggle/` (`hostels:toggle_room`)
  - `/manage/hostels/<int:hostel_id>/generate-rooms/` (`hostels:generate_rooms`)
  - `/hostels/options/floors/` (`hostels:options_floors`)
  - `/hostels/options/rooms/` (`hostels:options_rooms`)
  - `/hostels/options/blocks/` (deprecated)
- **Forms & UI to clean**:
  - Remove floor & room fields from `HostelerRegistrationForm` (`apps/accounts/forms.py`).
  - Remove floor & room fields from `ResidenceForm` and profile template (`templates/accounts/profile.html`).
  - Remove room/floor fields from `TicketForm` and `templates/tickets/raise.html`.
  - Remove room/floor columns from Ticket lists, Kanban, ticket detail, CSV exports, search, dashboards.
  - Residence is **Hostel only**.
- **Data preserved**:
  - `Room`, `Block` models, `User.room`, `Ticket.room`, `ResidenceHistory.room` stay in database schema as deprecated historical columns.

## 2. Routing & SLA Page
- **Routes to remove (return 404)**:
  - `/manage/routing/` (`tickets:manage_routing`)
  - `/manage/routing/add/` (`tickets:add_routing_rule`)
  - `/manage/routing/<int:rule_id>/edit/`
  - `/manage/routing/<int:rule_id>/delete/`
- **Logic preserved**:
  - Dynamic routing fallback order (`assign_initial` service).
  - SLA computation with `services/sla.py: hours_for(priority, level)` with hardcoded fallback defaults.
  - Category, Tag, and Criticality management moved to new `/manage/settings/` (Ticket Settings).

## 3. Resident Management
- **Routes to remove (return 404)**:
  - `/manage/residents/` (`hostels:manage_residents`)
  - `/manage/residents/<int:resident_id>/verify/`
  - `/manage/residents/<int:resident_id>/reject/`
  - `/manage/residents/<int:resident_id>/reset-password/`
  - `/manage/residents/bulk-verify/`
- **Logic preserved**:
  - All hosteler accounts, logins, ticket creation, and community participation.
  - New management commands added for operators: `reset_user_password <login_id>` and `import_allowed_roll_numbers <file.csv>`.

## 4. Community Staff Access
- Non-hostelers blocked on `/community/*` (HTTP 403).
- Staff ticket detail community panels removed.
- Staff community moderation endpoints (`/community/comments/<id>/hide/`, `/community/<no>/hide/`) removed (404).
- Hosteler self-moderation (owner hide, reporter hide, 3 reports auto-hide) implemented.
