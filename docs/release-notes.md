# Release Notes: Removal of Community Feature & Legacy Clean-up

## 1. Overview & Architectural Principles

The Community feature (feed, reposts, community comments, similar issues, repost-driven criticality escalation, and moderation) has been completely removed from the Hostel Ticket System.

### Key Architectural Guarantees:
- **Preserve Data, Restrict Surface**: No database tables or columns have been dropped. Legacy entities and fields (`TicketRepost`, `CriticalityRule`, `Ticket.repost_count`, `Ticket.visibility`, `Ticket.show_reporter_name`, `Ticket.base_priority`, `Ticket.community_hidden`, `Ticket.last_notified_threshold`, `TicketComment.scope/is_hidden/hidden_by/hidden_reason/is_official`, `Category.allow_community`) remain in the database schema annotated with `# DEPRECATED: Community removed, kept for historical data, no UI`. `python manage.py makemigrations --check --dry-run` detects zero changes.
- **Priority as Single Source of Truth**: `Ticket.priority` is the sole source of truth across the entire system. Base priority reading has been discontinued, and new tickets write `base_priority = priority`.
- **Backend-Enforced 404s**: All removed routes return `HTTP 404 Not Found` for all roles (anonymous, hosteler, caretaker, warden, chief warden, admin).
- **Comment Isolation**: Existing `COMMUNITY`-scoped comments remain safely in the database for historical audits but are globally excluded from active querysets across all interfaces (hosteler, staff, exports, admin).
- **Independent Announcements**: Announcements remain completely intact and independent with no shared dependencies.

---

## 2. Inventory of Removed Components

### Decommissioned Routes (All return 404)
| Route Pattern | Method | Former Purpose | Current Status |
|---|---|---|---|
| `/community/` | GET | Community feed redirect / landing | `404 Not Found` |
| `/community/feed/` | GET | Paginated community cards feed | `404 Not Found` |
| `/community/similar-issues/` | GET | Real-time similar issue detector | `404 Not Found` |
| `/community/comments/<id>/report/` | POST | Student comment reporting | `404 Not Found` |
| `/community/comments/<id>/delete/` | POST | Resident comment self-deletion | `404 Not Found` |
| `/tickets/<ticket_no>/repost/` | POST | Repost toggle endpoint | `404 Not Found` |
| `/tickets/<ticket_no>/community-comments/` | POST | Community comment submission | `404 Not Found` |
| `/manage/criticality/` | GET/POST | Repost criticality threshold rules | `404 Not Found` |

### Removed Pages & UI Components
- **Hosteler Community Feed**: Full feed page, post cards, Recent/Trending/Critical/My Reposts tabs, trending rail, infinite scroll.
- **Repost Interactions**: Repost buttons, affected counter chips, "raised by N reposts" notes across list and detail pages.
- **Community Comments**: Comment feeds on ticket cards, author deletion, comment reporting, auto-hide mechanisms.
- **Raise Ticket Form Options**: "Share this with other hostelers" toggle, "Show my name" toggle, and "Similar issues / Repost instead" panel.
- **Staff-side Leftovers**: "Affected" column and filter in ticket lists, Kanban affected count chips, "Most-reported issues" dashboard card, Community tab/panel on ticket detail.
- **Ticket Settings**: Criticality rules tab removed; "Allow in community" field removed from Category form.
- **Navigation**: Community nav items removed from desktop sidebar, tablet rail, mobile bottom bar, and More action sheet.

### Removed Settings & Commands
- **Setting**: `SHOW_AFFECTED_COUNT_TO_STAFF` removed from `config/settings/base.py`.
- **Command**: `apps/tickets/management/commands/moderate_comment.py` removed.

---

## 3. Database Deprecation & Future Column Dropping Runbook

The following models and columns are deprecated and retained exclusively for historical data preservation:
- Models: `TicketRepost`, `CriticalityRule`
- `Ticket` Fields: `repost_count`, `visibility`, `show_reporter_name`, `base_priority`, `community_hidden`, `last_notified_threshold`
- `TicketComment` Fields: `scope`, `is_hidden`, `hidden_by`, `hidden_reason`, `is_official`
- `Category` Field: `allow_community`

### Future Migration Decommissioning Runbook
When historical community records are no longer required for compliance or audits:
1. **Take Database Backup**:
   ```bash
   cp db.sqlite3 db.sqlite3.bak-$(date +%Y%m%d%H%M%S)
   ```
2. **Remove Model Definitions**:
   Delete `TicketRepost` and `CriticalityRule` models from `apps/tickets/models.py`. Remove deprecated fields from `Ticket`, `TicketComment`, and `Category`.
3. **Generate Gated Migration**:
   ```bash
   python manage.py makemigrations tickets --name drop_deprecated_community_columns
   ```
4. **Apply in Planned Maintenance Window**:
   ```bash
   python manage.py migrate
   ```

---

# Release Notes: Access Cleanup & Staff Management Architecture

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
