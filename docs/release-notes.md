# Release Notes: Access Cleanup & Staff Management Architecture

## 1. Overview & Architectural Principles

This release introduces comprehensive access control enforcement, operational boundary cleanup, and a unified staff management lifecycle while maintaining database schema stability.

Key Architectural Guarantees:
- **Preserve Data, Restrict Surface**: No database columns or tables dropped. Deprecated legacy entities (`Room`, `Block`, `User.room`, `Ticket.room`, `ResidenceHistory.room`) remain in database schema marked `@deprecated` for data integrity and backwards analytics compatibility.
- **Backend-Enforced Security**: Permissions are strictly enforced via capability helpers (`has_capability`, `require_capability`), querysets, services, and forms—never relying solely on UI concealment.
- **Strict Community Boundary**: `/community/*` and community ticket APIs are hosteler-only. Staff and administrative roles cannot access, repost, or comment on community feeds.
- **Administrative Parity**: Chief Warden has full administrative parity with Administrator, with clear role boundaries (Chief Warden remains Level 3 in escalation hierarchies and cannot modify Administrator users).
- **Hostel-Only Residence**: Residence onboarding and ticket creation require only Hostel selection. All floor, room, and capacity UI dependencies have been cleanly severed.

---

## 2. Capability Matrix & Role Permissions

A centralized capability engine is implemented in `apps/core/permissions.py` with standard capability mappings:

| Capability | Hosteler | Caretaker | Warden | Chief Warden | Admin |
|---|:---:|:---:|:---:|:---:|:---:|
| `community_access` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `manage_staff` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `manage_ticket_settings` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `view_all_tickets` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `triage_tickets` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `resolve_tickets` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `reassign_tickets` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `escalate_tickets` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `export_data` | ❌ | ❌ | ✅ | ✅ | ✅ |

### Chief Warden / Admin Peer Invariant
Chief Wardens have administrative capabilities across staff management and ticket settings, but **cannot edit, deactivate, or reset passwords for users with the `ADMIN` role**.

---

## 3. Route Removal & Replacements

Deprecated administrative screens have been decommissioned and cleanly return `HTTP 404`:

| Decommissioned Route | Status | Replacement / Handling |
|---|---|---|
| `/manage/rooms/*` | `404 Not Found` | Simplified to hostel-only residence. |
| `/manage/residents/*` | `404 Not Found` | Replaced by CLI operators: `reset_user_password`, `import_allowed_roll_numbers`. |
| `/manage/routing/*` | `404 Not Found` | Fallback routing preserved in backend; settings managed at `/manage/settings/`. |
| `/hostels/options/floors/` | `404 Not Found` | Removed floor selection. |
| `/hostels/options/rooms/` | `404 Not Found` | Removed room selection. |

### New Administrative Endpoints:
- `/manage/staff/`: Full staff directory with filtering, creation modal, and audit log links.
- `/manage/staff/<id>/edit/`: Staff profile, assigned hostel, and active status update.
- `/manage/staff/<id>/change-login-id/`: Safe login ID modification with audit trail.
- `/manage/staff/<id>/reset-password/`: Re-authentication required one-time temp password generator.
- `/manage/staff/<id>/deactivate/`: Guarded deactivation with active ticket reassignment check.
- `/manage/staff/<id>/audit/`: Staff action audit history view.
- `/manage/settings/`: Streamlined category, tag, and criticality rules configuration.

---

## 4. Community Lockdown & Self-Moderation

1. **Staff Exclusion**: Staff attempts to access `/community/` or submit comments/reposts receive an immediate `HTTP 403 Forbidden`.
2. **Student Self-Moderation**:
   - Hostelers can flag abusive comments via `POST /community/comments/<id>/report/`.
   - Any comment reaching **3 distinct reports** (`REPORT_THRESHOLD = 3`) is automatically hidden (`is_hidden=True`) from community feeds without staff involvement.
   - Comment authors can delete their own comments via `POST /community/comments/<id>/delete/`.
   - Operators can review or clear reports via the `moderate_comment` CLI command.

---

## 5. Staff Lifecycle Management & Safety Guardrails

- **One-Time Temporary Passwords**: When an administrator or Chief Warden resets a staff member's password, the operator must re-enter their own password. A cryptographically random temporary password is generated and displayed once with an automatic copy button.
- **Deactivation Blocker**: A staff member cannot be deactivated if they are currently assigned active tickets (`is_closed=False`, `is_deleted=False`). The system blocks deactivation and displays active ticket counts with a direct reassignment prompt.
- **Audit Logging**: Every staff creation, profile edit, login ID change, password reset, and deactivation is logged in `StaffAuditLog` with actor, target, timestamp, IP address, and metadata.

---

## 6. SLA Fallbacks & Seeding

- Routing rules no longer require complex UI configuration. Fallback SLA logic in `apps/tickets/services/sla.py` guarantees deterministic resolution deadlines across priority and escalation levels:
  - `URGENT`: 2h (L1), 4h (L2), 8h (L3), 12h (L4)
  - `HIGH`: 8h (L1), 16h (L2), 24h (L3), 48h (L4)
  - `MEDIUM`: 24h (L1), 48h (L2), 72h (L3), 96h (L4)
  - `LOW`: 48h (L1), 72h (L2), 96h (L3), 120h (L4)
- Run `python manage.py seed_sla_defaults` to seed baseline rules into the database.

---

## 7. Operator CLI Commands

Four dedicated management commands provide command-line operations for system maintenance:

1. **Seed Default SLA Matrices**:
   ```bash
   python manage.py seed_sla_defaults
   ```
2. **Reset User Password**:
   ```bash
   python manage.py reset_user_password <login_id> [--password <new_pwd>]
   ```
3. **Import Allowed Roll Numbers**:
   ```bash
   python manage.py import_allowed_roll_numbers path/to/roll_numbers.csv
   ```
4. **Moderate Community Comments**:
   ```bash
   python manage.py moderate_comment list-reported
   python manage.py moderate_comment hide <comment_id>
   python manage.py moderate_comment unhide <comment_id>
   python manage.py moderate_comment clear-reports <comment_id>
   ```

---

## 8. Database Backup & Restore Runbook

To safely backup and restore the SQLite database during operational maintenance:

```bash
# Backup current database snapshot
cp db.sqlite3 db.sqlite3.bak-$(date +%Y%m%d%H%M%S)

# Restore from backup snapshot
cp db.sqlite3.bak db.sqlite3
python manage.py migrate --check
```
