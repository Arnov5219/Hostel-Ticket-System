# Repository State Audit (Phase X0)

**Date**: 2026-10-09  
**Branch**: `feature/access-cleanup`

## 1. Feature Status Inventory
- **Community Feed & Reposts**: Implemented across `/community/` and `/tickets/<no>/repost/`, but currently accessible to staff and hostelers. Needs restriction to hostelers only (403 for staff).
- **Hostel & Room Structure**: 12 Hostels implemented. Room management (`manage_rooms`), room generator, room dropdown options, room fields in forms (registration, onboarding, profile, raise ticket) exist. Must be removed from UI, forms, and routes; database columns preserved as deprecated data.
- **Routing & SLA Admin Screen**: `/manage/routing/` exists with Routing Rules, SLA Policies, Categories, Tags. Must be removed from UI and routes; Categories, Tags, and Criticality rules move to `/manage/settings/` (Ticket Settings); routing and escalation logic preserved.
- **Resident Management Screen**: `/manage/residents/` exists. Must be completely removed from UI, navigation, and routes (404); resident accounts, login, and registration preserved with instant verified access.
- **Role Permissions**: Role-name based checks (`role == Role.ADMIN`, etc.) used in views and templates. Must be refactored into capability-based permission system (`Capability` enum and `user.can(...)`). Chief Warden must receive full Admin parity with distinct identity.
- **Staff Management**: Basic list existed at `/manage/staff/`. Must be upgraded to full staff lifecycle management (create, edit, login ID change, password reset, hostel assignment, safe deactivate/archive with active ticket reassignment).
