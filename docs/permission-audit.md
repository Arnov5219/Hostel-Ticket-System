# Permission & Role-Name Audit (Phase X0)

## 1. Role-Name & Direct Role Check Audit
Direct checks on `user.role`, `is_admin`, `is_warden`, `is_chief_warden`, `is_hosteler` were identified in:
- `apps/core/permissions.py`: `can_raise_ticket`, `can_view_kanban`, `can_manage_config`, `can_view_ticket`, `can_moderate_community`, `can_publish_announcements`, etc.
- `apps/core/mixins.py`: `RoleRequiredMixin` checking `request.user.role in self.allowed_roles`.
- `apps/tickets/querysets.py`: `visible_to`, `can_see_history`.
- `apps/tickets/services/community.py`: staff checks on community comment actions.
- `apps/tickets/services/deletion.py`: `can_delete`, `restore_ticket`.
- `apps/tickets/views/deletion.py`: trash and restore views.
- `apps/announcements/views.py` & `services.py`: publication scoping.
- `apps/hostels/views.py`: scoping for management views.

## 2. Refactoring Target
Replace role-name checks with `Capability` enum checks via `has_capability(user, Capability.X)` or `user.can(Capability.X)` and `CapabilityRequiredMixin`.
Chief Warden will inherit all administrative capabilities equal to Admin (with the exception of peer account management policy `can_manage_user` and superuser Django-admin).
Community access will be restricted exclusively to `Capability.COMMUNITY_ACCESS` (Hostelers only).
