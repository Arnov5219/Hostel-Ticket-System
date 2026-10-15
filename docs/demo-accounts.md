# Demo Accounts and Security Strategy

## Overview
This document specifies the standard test accounts (`L0` through `L5`), the uniform credential strategy (`me1234`), and the production security guards enforced by the application.

## Account Matrix

| Login ID | Display Name | Role | Level | Password | Notes |
|:---:|---|---|:---:|:---:|---|
| `L0` | Aarav Sharma (Demo) | Hosteler | — | `me1234` | Resident of Mandakini Hostel (MH-101). |
| `L1` | Mukesh Caretaker (Demo) | Caretaker | L1 | `me1234` | Responsible caretaker for Mandakini Hostel. |
| `L2` | Dr. Ramesh Warden (Demo) | Hostel Warden | L2 | `me1234` | Warden for Mandakini Hostel. |
| `L3` | Prof. Sunita Chief Warden (Demo) | Chief Warden | L3 | `me1234` | Campus-wide supervisory authority. |
| `L4` | Dr. K. V. Dean (Demo) | Dean | L4 | `me1234` | Top-tier escalation and campus compliance authority. |
| `L5` | System Administrator (Demo) | Admin | — | `me1234` | System administrator. Not in ticket escalation hierarchy. |

## Management Commands

### `seed_demo_accounts`
- **Location**: `apps/accounts/management/commands/seed_demo_accounts.py`
- **Safety Guard**: Fails immediately unless `settings.DEBUG is True` or `os.environ.get("ENABLE_DEMO_ACCOUNTS") == "1"`.
- **Idempotency**: Safely re-runs at any time to recreate or reset L0..L5 accounts and refresh their passwords to `me1234`.
- **Legacy Support**: Also tags legacy demo usernames (`student1`, `caretaker1`, `warden1`, `chief_warden`, `admin`) with `is_demo=True` and sets their password to `me1234`.

### `purge_demo_accounts`
- **Location**: `apps/accounts/management/commands/purge_demo_accounts.py`
- **Safety Guard**: Executes a dry run by default. Requires `--confirm` to delete.
- **Cascade Safety**: Disassociates tickets, hostel responsible staff pointers, and notifications before deleting `is_demo=True` records.

## Production Safeguards

1. **System Check (`accounts.E001`)**:
   Registered with `Tags.security` and `deploy=True`. When `check --deploy` runs in production (`DEBUG=False`), an error is raised if any `is_demo=True` records exist in the database.
2. **Environment Variable**:
   In staging or testing environments with `DEBUG=False`, set `ALLOW_DEMO_ACCOUNTS=1` to allow demo accounts to exist.
3. **Audit Log Hygiene**:
   Passwords and credentials are never stored or logged in `StaffAuditLog`, `TicketActivity`, or standard logs.
