# Permission & Role-Name Audit (Phase A0: Role Separation)

## 1. Places where Chief Warden or Dean is Treated as Admin
- `apps/core/permissions.py`:
  - `CHIEF_WARDEN_CAPABILITIES = frozenset(ADMIN_CAPABILITIES - {Capability.RAISE_TICKET})` -> To be replaced with dedicated non-admin capability sets.
  - `can_manage_user`: Branch checking `actor.role == Role.CHIEF_WARDEN` and `CHIEF_WARDEN_CAN_MANAGE_ADMINS` -> To be deleted; only Admin can manage staff.
- `apps/core/navigation.py`:
  - `is_cw_or_admin = getattr(user, "role", None) in [Role.CHIEF_WARDEN, Role.ADMIN]` -> Replaced with separate navigation definitions for Chief Warden, Dean, and Admin.
- `apps/tickets/views/deletion.py`:
  - `request.user.is_admin or request.user.is_chief_warden` -> Restrict restore & trash view to Admin (`Capability.RESTORE_TICKET`, `Capability.VIEW_TRASH_ALL`).
- `apps/announcements/views.py` & `services.py`:
  - `user.role in [Role.ADMIN, Role.CHIEF_WARDEN]` -> Handled by `Capability.PUBLISH_ANNOUNCEMENT` with role scoping (Warden: own; Chief Warden: any; Dean: all; Admin: system).
- `apps/accounts/services/staff.py`:
  - `role in [Role.CHIEF_WARDEN, Role.ADMIN]` for campus assignment -> Extended to Dean; Admin is system without escalation tier.

## 2. Template Audit for `admin` / `Admin` Literals
- `templates/components/_admin_subnav.html`:
  - Line 1: `{% if request.user.is_authenticated and request.user.is_admin or request.user.is_chief_warden %}` -> Change to Admin only (`request.user.is_admin`).
- `templates/tickets/detail.html`:
  - Admin controls vs Staff controls: Admin does not change status or escalate tickets directly.
- `templates/tickets/kanban.html`:
  - Line 37 & 88: `{% if request.user.is_admin %}` -> Kanban is not a system admin tool; Dean/Warden/Caretaker use Kanban, Admin navigation excludes Kanban.
- `templates/tickets/_list_table.html` & `templates/tickets/list.html`:
  - `{% if request.user.is_hosteler or request.user.is_admin %}` for "Raise ticket" button -> Kept for Admin support / raise on behalf.
- `templates/accounts/login.html`:
  - Demo accounts disclosure: Replace with L0..L5 chips.
- `templates/components/_sidebar.html`:
  - Rendered dynamically through `core/navigation.py` using capability checks.
