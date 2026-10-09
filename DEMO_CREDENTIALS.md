# 🔑 Demo Quick Login Credentials

This document lists the pre-seeded demo accounts available for quick testing and review across all system roles in the **Hostel Ticket System**.

> **⚡ Quick Login Shortcut:**
> When opening the login page at [`/accounts/login/`](http://127.0.0.1:8000/accounts/login/), expand the **"Quick demo accounts ▾"** section below the sign-in form to fill in credentials with a single click.

---

## 🚀 1. Primary Quick Login Accounts

These are the primary accounts mapped to the quick login shortcuts on the login screen:

| Role | Escalation Level | Login ID | Password | Name / Scope | Permissions & Focus |
|---|:---:|---|---|---|---|
| **System Administrator** | **Level 4** | `admin` | `admin123` | System Administrator (Campus-wide) | Full system configuration, SLA settings, user directory, manage hostels/rooms/staff, audit logs |
| **Chief Warden** | **Level 3** | `chief_warden` | `pass1234` | Prof. S. K. Sharma (All 12 Hostels) | Campus-wide oversight, L3 ticket escalations, campus announcements, hostel performance metrics |
| **Warden** | **Level 2** | `warden_bha` | `pass1234` | Dr. Ramesh Verma (BH-1) | L2 ticket escalations, hostel announcements, resident directory, student password resets |
| **Caretaker** | **Level 1** | `caretaker_bha1` | `pass1234` | Mukesh Kumar (BH-1 Maintenance) | Frontline ticket triage, assignment, in-progress resolution, work orders, kanban board |
| **Hosteler (Resident)** | **Resident** | `student_01` | `pass1234` | Hosteler 1 (BH-1, Room 101) | Raise complaints, track tickets, community feed discussions, upvote/repost issues, change residence |

---

## 🏢 2. All Hostel Staff Accounts (BH-1 to BH-12)

Every hostel has dedicated Level 1 (Caretaker) and Level 2 (Warden) accounts. All passwords are set to `pass1234`.

| Hostel | Caretaker (Level 1) | Warden (Level 2) | Default Password |
|---|---|---|---|
| **BH-1** (Boys Hostel 1) | `caretaker_bh1` / `caretaker_bha1` | `warden_bh1` / `warden_bha` | `pass1234` |
| **BH-2** (Girls Hostel 2) | `caretaker_bh2` / `caretaker_ghb1` | `warden_bh2` / `warden_ghb` | `pass1234` |
| **BH-3** | `caretaker_bh3` | `warden_bh3` | `pass1234` |
| **BH-4** | `caretaker_bh4` | `warden_bh4` | `pass1234` |
| **BH-5** | `caretaker_bh5` | `warden_bh5` | `pass1234` |
| **BH-6** | `caretaker_bh6` | `warden_bh6` | `pass1234` |
| **BH-7** | `caretaker_bh7` | `warden_bh7` | `pass1234` |
| **BH-8** | `caretaker_bh8` | `warden_bh8` | `pass1234` |
| **BH-9** | `caretaker_bh9` | `warden_bh9` | `pass1234` |
| **BH-10** | `caretaker_bh10` | `warden_bh10` | `pass1234` |
| **BH-11** | `caretaker_bh11` | `warden_bh11` | `pass1234` |
| **BH-12** | `caretaker_bh12` | `warden_bh12` | `pass1234` |

---

## 🎓 3. Sample Student (Hosteler) Accounts

All demo student accounts have the password set to `pass1234`.

| Login ID | Password | Hostel Assignment | Room Number | Test Purpose |
|---|---|---|:---:|---|
| `student_01` | `pass1234` | **BH-1** | 101 | Standard active resident (Boys Hostel 1) |
| `student_02` | `pass1234` | **BH-1** | 102 | Community feed comments & repost testing |
| `student_03` | `pass1234` | **BH-1** | 103 | Multi-ticket reporter |
| `student_09` | `pass1234` | **BH-1** | 109 | Active resident |
| `student_14` | `pass1234` | *None (Unassigned)* | — | **Onboarding Gate Test**: Redirects to room selection upon login |
| `student_15` | `pass1234` | **BH-2** | 101 | Standard active resident (Girls Hostel 2) |
| `student_16` | `pass1234` | **BH-2** | 102 | Active resident |
| `student_22` | `pass1234` | *None (Unassigned)* | — | **Onboarding Gate Test**: Unassigned resident flow |

---

## 💡 4. How to Sign In

1. Open **`/accounts/login/`** in your browser.
2. Either:
   - Click **"Quick demo accounts ▾"** and tap any role button (`Admin`, `Chief Warden`, `Warden`, `Caretaker`, `Hosteler`) to auto-fill the form, **OR**
   - Enter any **Login ID** (or registered **Email Address**) and **Password** manually from the tables above.
3. Click **Sign In**.

---

## 🔄 5. Managing Demo & Test Data

### To clean and remove all fake/test data at any time:
```bash
# Wipes all tickets, fake students, announcements, and notifications
# Preserves all 12 Hostels, 1,440 rooms, and Staff/Admin accounts
python manage.py clear_demo_data
```

### To reseed demo data (for presentations or mock testing):
```bash
# Seed 12 hostels and 1,440 rooms
python manage.py seed_hostels

# Seed full demo environment (users, routing rules, announcements, 60+ tickets)
python manage.py seed_demo_data
```
