# 🔑 Demo Quick Login Credentials (L0..L5)

This document lists the standardized demo accounts available for quick testing, role verification, and presentations in the **Hostel Ticket System**.

> **⚡ Quick Login Shortcut:**
> When opening the login page at [`/accounts/login/`](http://127.0.0.1:8000/accounts/login/) (in development/demo mode), the **"Demo accounts"** grid displays clickable chips for **L0** through **L5**. Clicking any chip automatically fills the login form.

---

## 🚀 1. Primary Standardized Demo Matrix (L0..L5)

All demo accounts share the uniform default password: **`me1234`**

| ID | Role | Escalation Level | Display Name | Scope / Hostel | Password | Key Capabilities & Purpose |
|:---:|---|:---:|---|---|:---:|---|
| **L0** | **Hosteler** | — | Aarav Sharma (Demo) | Mandakini Hostel (MH-101) | `me1234` | Report personal tickets, status chips, 8s undo deletion |
| **L1** | **Caretaker** | **L1** | Mukesh Caretaker (Demo) | Mandakini Hostel | `me1234` | Frontline triage, change status, add internal notes, kanban |
| **L2** | **Hostel Warden** | **L2** | Dr. Ramesh Warden (Demo) | Mandakini Hostel | `me1234` | Hostel overview, reassign tickets, escalate to Chief Warden, kanban |
| **L3** | **Chief Warden** | **L3** | Prof. Sunita Chief Warden (Demo) | Campus-wide | `me1234` | Cross-hostel comparison, category breakdown, escalate to Dean, kanban |
| **L4** | **Dean** | **L4** | Dr. K. V. Dean (Demo) | Campus Authority | `me1234` | Final escalation queue, campus compliance, SLA health, kanban |
| **L5** | **Admin** | — | System Administrator (Demo) | System | `me1234` | Manage staff, hostels, responsibility, settings, trash restore, audit log |

---

## 🔒 2. Role Boundaries & Separation of Powers

1. **Dean (L4)**:
   - Holds campus-wide authority and handles top-tier escalations (Level 4).
   - Operational workflow user: views kanban, changes ticket status, reassigns tickets.
   - **Does NOT hold administrative controls** (`/manage/*` is blocked with 403).

2. **Admin (L5)**:
   - System administrator: manages staff, hostels, room allocation, ticket SLA settings, and restores soft-deleted tickets.
   - **Does NOT participate in ticket resolution**: cannot change status, post comments, or escalate tickets.
   - Outside the operational escalation chain (`escalation_level = None`).
   - Does not have Kanban in the navigation bar.

3. **Chief Warden (L3)**:
   - Campus-wide escalation authority (Level 3).
   - Operational workflow user: views kanban, escalates to Dean.
   - **Does NOT hold administrative controls** (`/manage/*` is blocked with 403).

4. **Warden (L2)**:
   - Hostel supervisor for assigned hostel (Level 2).
   - Can soft-delete tickets within own hostel (with mandatory reason).
   - **Does NOT have access to Trash view or ticket restoration** (Trash is Admin-only).

---

## 🛠️ 3. Managing Demo Accounts

### Seeding Demo Accounts
```bash
# Seeds or resets L0..L5 accounts with password 'me1234'
# Requires DEBUG=True or ENABLE_DEMO_ACCOUNTS=1
python manage.py seed_demo_accounts
```

### Full Demo Dataset Seeding
```bash
# Seeds 12 hostels, rooms, L0..L5 accounts, and realistic tickets
python manage.py seed_demo_data
```

### Purging Demo Accounts Before Production
```bash
# Dry run: inspect demo accounts without deleting
python manage.py purge_demo_accounts

# Permanent purge: removes all is_demo=True accounts safely
python manage.py purge_demo_accounts --confirm
```

---

## 🛡️ 4. Production Security Safeguard

A Django system check (`accounts.E001`) automatically protects production deployments:
- When running `python manage.py check --deploy` with `DEBUG=False`, the check scans for any `is_demo=True` accounts with known passwords in the database.
- If demo accounts exist, the deployment check halts with an error.
- To bypass only in staging environments, set `ALLOW_DEMO_ACCOUNTS=1`.
