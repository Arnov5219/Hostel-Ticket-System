# Repository State Audit (Phase A0: Role Separation)

**Date**: 2026-10-15  
**Branch**: `feature/role-separation`  
**Purpose**: Baseline audit prior to Admin vs Dean role separation and demo account overhaul (L0–L5 with password `me1234`).

## 1. Current Role Values (`apps/accounts/models.py`)
- `Role.HOSTELER = "HOSTELER", "Hosteler"`
- `Role.CARETAKER = "CARETAKER", "Caretaker (L1)"`
- `Role.WARDEN = "WARDEN", "Hostel Warden (L2)"`
- `Role.CHIEF_WARDEN = "CHIEF_WARDEN", "Chief Warden (L3)"`
- `Role.ADMIN = "ADMIN", "Admin / Dean (L4)"` (combined role; to be split into `DEAN` at L4 and `ADMIN` as system role)

Current `ROLE_TO_LEVEL`:
- `Role.CARETAKER: 1`
- `Role.WARDEN: 2`
- `Role.CHIEF_WARDEN: 3`
- `Role.ADMIN: 4`

## 2. Usage of `ADMIN` and `CHIEF_WARDEN`
- **Capabilities (`apps/core/permissions.py`)**: `CHIEF_WARDEN_CAPABILITIES` currently mirrors `ADMIN_CAPABILITIES - {RAISE_TICKET}` under the old parity rule.
- **Safety Policy (`can_manage_user`)**: Checks `settings.CHIEF_WARDEN_CAN_MANAGE_ADMINS` (to be removed; staff management will become Admin-only).
- **Navigation (`apps/core/navigation.py`)**: Groups `is_cw_or_admin = role in [CHIEF_WARDEN, ADMIN]` and displays Hostels, Staff, Responsibility, Ticket settings to both. Under the new model, only `ADMIN` has management items.
- **Trash Access**: Currently visible to Warden, Chief Warden, and Admin. Under the new model, Trash and Restore are Admin-only.

## 3. Existing Seed Commands and Demo Accounts
- `apps/accounts/management/commands/seed_demo_users.py`:
  - `admin` (`admin123`) -> Admin / Dean
  - `chief_warden` (`pass1234`) -> Chief Warden
  - `warden_a` (`pass1234`) -> Warden
  - `caretaker_a1` (`pass1234`) -> Caretaker
  - `student1` (`pass1234`) -> Hosteler
- `apps/tickets/management/commands/seed_demo_data.py`:
  - Seeds full demo environment, multiple students (`student_01`..`student_22`), hostel wardens (`warden_bh1`..`warden_bh12`), caretakers (`caretaker_bh1`..`caretaker_bh12`), `chief_warden`, `admin`.
- Target new standard: L0 (Hosteler), L1 (Caretaker), L2 (Warden), L3 (Chief Warden), L4 (Dean), L5 (Admin) all using password `me1234`.

## 4. Login Page Demo Panel (`templates/accounts/login.html`)
- Currently lists `admin` (L4), `chief_warden` (L3), `warden_bha` (L2), `caretaker_bha1` (L1), and `student_01`.
- Will be updated to chips L0..L5 with `me1234`, visible only in `DEBUG` or `DEMO_MODE=1`.

## 5. Escalation Resolver for Level 4 (`apps/tickets/services/escalation.py`)
- `find_escalation_assignee(ticket, next_level=4)` currently looks for `Role.ADMIN`.
- Will be updated to resolve `Role.DEAN` first; if none active, fallback to active `Role.ADMIN` with a `LEVEL4_FALLBACK` audit activity.
