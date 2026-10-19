# Repository State Audit (Phase A5: Final Implementation State)

**Date**: 2026-10-15  
**Branch**: `feature/role-separation`  
**Status**: Fully Implemented & Verified

---

## 1. Role System Architecture (`apps/accounts/models.py`)

The role system defines 6 explicit roles with complete separation between operational campus escalation and system administration:

| Role Identifier | Role Display Name | Level | Scope & Purpose |
|-----------------|-------------------|-------|-----------------|
| `HOSTELER` (`L0`) | Hosteler | 0 | Ticket creator (room/hostel issues) |
| `CARETAKER` (`L1`) | Caretaker (L1) | 1 | Operational ticket handler (hostel level) |
| `WARDEN` (`L2`) | Hostel Warden (L2) | 2 | Operational supervisor (hostel level) |
| `CHIEF_WARDEN` (`L3`)| Chief Warden (L3) | 3 | Operational authority (campus-wide) |
| `DEAN` (`L4`) | Dean (L4) | 4 | Final operational escalation authority (campus-wide) |
| `ADMIN` (`L5`) | Admin | None | System administrator (user hygiene, configuration, audit, trash) |

`ROLE_TO_LEVEL`:
- `Role.HOSTELER: 0`
- `Role.CARETAKER: 1`
- `Role.WARDEN: 2`
- `Role.CHIEF_WARDEN: 3`
- `Role.DEAN: 4`
- `Role.ADMIN: None` (outside ticket escalation hierarchy)

---

## 2. Capability Matrix & Permissions (`apps/core/permissions.py`)

- **Admin-Only Capabilities**:
  - `MANAGE_STAFF`
  - `MANAGE_HOSTELS`
  - `MANAGE_RESPONSIBILITY`
  - `MANAGE_TICKET_SETTINGS`
  - `RESTORE_TICKET`
  - `VIEW_TRASH_ALL`
  - `VIEW_AUDIT_LOG`
- **Chief Warden & Dean**:
  - Pure operational roles; stripped of all administrative capabilities.
  - Can view, review, reassign, close tickets, and manage announcements.
  - Dean is the Level 4 operational authority (cannot escalate further as L4 is top of ladder).
- **Admin Operational Restrictions**:
  - Admin cannot change ticket status, add comments, move tickets on Kanban, or manually escalate tickets.
  - Admin cannot access `/tickets/kanban/`.

---

## 3. Escalation Resolver (`apps/tickets/services/escalation.py`)

- Escalations to Level 4 resolve to an active `Role.DEAN` user.
- If no active Dean is found, escalation falls back to active `Role.ADMIN` with a `LEVEL4_FALLBACK` audit log entry in `TicketActivity`.
- A warning banner appears on the Admin dashboard when no active Dean exists.

---

## 4. Navigation & Route Security

- **Admin Sidebar & Mobile Nav**:
  - Dashboard (`/dashboard/`)
  - Tickets (`/tickets/`)
  - Announcements (`/announcements/`)
  - Hostels (`/manage/hostels/`)
  - Staff (`/manage/staff/`)
  - Responsibility Matrix (`/manage/responsibility/`)
  - Ticket Settings (`/manage/settings/`)
  - Trash (`/manage/trash/`)
  - Notifications (`/notifications/`)
- **Operational Staff (L1–L4)**:
  - Dashboard, Tickets, Kanban, Announcements, Notifications.
  - No access to `/manage/*` routes or Trash/Restore.
- **Hosteler (L0)**:
  - Dashboard, My Tickets, Raise Ticket, Community, Announcements, Notifications.

---

## 5. Demo Accounts & Production Safeguards

- Standard demo credentials:
  - `L0` (Hosteler): `me1234`
  - `L1` (Caretaker): `me1234`
  - `L2` (Warden): `me1234`
  - `L3` (Chief Warden): `me1234`
  - `L4` (Dean): `me1234`
  - `L5` (Admin): `me1234`
- Flag: All demo users have `is_demo=True`.
- **Management Commands**:
  - `python manage.py seed_demo_accounts`: Idempotently creates or updates L0..L5 accounts. Blocked in non-DEBUG environments unless `ENABLE_DEMO_ACCOUNTS=1`.
  - `python manage.py purge_demo_accounts --confirm`: Safely purges demo accounts. Dry-run by default without `--confirm`.
- **Production Guard (`accounts.E001`)**:
  - Deploy check in `apps/accounts/apps.py` triggers an error during `python manage.py check --deploy` if any `is_demo=True` account exists and `ALLOW_DEMO_ACCOUNTS=1` is not explicitly set.
