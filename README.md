# Hostel Ticket System 🏢🎫

A production-grade, enterprise-dense web application for campus hostel ticket, maintenance, and grievance management built with **Django 5.x**, **HTMX**, **Alpine.js**, and an aesthetic design system inspired by **Frappe / ERPNext**.

---

## 🌟 Key Features

- **Hostel-Only Residence Onboarding**:
  - Streamlined onboarding requiring only Hostel selection prior to app usage.
  - Rooms, blocks, and floor pickers deprecated from forms and UI while preserved in the underlying database for historical records.
  - Location prefilled on tickets with optional detail notes and "Outside own hostel" detection.
- **Enterprise Staff Management Lifecycle (`/manage/staff/`)**:
  - Centralized staff directory with live role and hostel filtering.
  - Safe deactivation safeguards: blocks deactivating staff members who have open assigned tickets until reassigned.
  - Login ID modification with unique conflict checks and audit logging.
  - Re-authenticated temporary password reset: admin/Chief Warden must re-verify password to issue a one-time temporary password.
  - Full audit logging (`StaffAuditLog`) tracking actor, target, timestamp, IP, and changes.
- **Capability Matrix & Administrative Parity**:
  - Fine-grained permission system (`apps/core/permissions.py`) with `has_capability(user, cap)` enforcement across views, navigation, and services.
  - **Chief Warden Administrative Parity**: Full management access across staff and ticket settings alongside Administrators, while preserving Level 3 escalation tier and preventing Chief Warden modification of Admin accounts.
- **Streamlined Ticket Operations & Ticket Priority Single Source of Truth**:
  - Ticket priority (`Ticket.priority`) is the single source of truth across all views, triage, assignment, and escalation workflows.
  - Direct private ticket interactions between hostelers and staff with transparent status workflows and SLA tracking.
- **Slim Ticket Settings (`/manage/settings/`) & SLA Fallbacks**:
  - Streamlined administration for Categories and Tags replacing deprecated routing screens.
  - Deterministic SLA fallback lookup table guaranteeing resolution deadlines even when explicit database rules are absent.
  - Seed CLI command (`seed_sla_defaults`) to populate standard SLA targets across all priority tiers.
- **Safe Ticket Soft-Delete & Trash Management**:
  - Soft-delete audit trail preserving SLA reporting and historical ticket numbering.
  - Hosteler D7 delete rules (own tickets only while Open/Assigned, no staff comments) with an **8-second undo countdown toast**.
  - Warden/Admin delete with mandatory reason selection and note.
  - Admin trash bin (`/manage/trash/`) with one-click restore and `purge_deleted` retention pruning command.
- **Dark Mode & Theming**:
  - Zero-flash top-of-head inline script with instant theme switching.
  - Choices: **Light**, **Dark**, and **System** (persisted in DB and `localStorage`).
  - Strict tokens-only design system (`tokens.css`), audited by automated test guards (`test_no_hardcoded_colors.py`).
  - Live Chart.js theme re-render on `themechange` events.
- **Comprehensive Mobile-First Usability**:
  - Responsive bottom navigation bar with raised accent action button and "More" action sheet.
  - Card-list responsive conversions for data tables on phones (< 768px).
  - Touch-friendly swipeable Kanban with status tab quick-jump strip and "Move to..." action menu fallback.
  - Full-screen/bottom-sheet filter and modal drawers.
  - Camera direct capture (`capture="environment"`) and gallery picker for attachments.
  - 44×44px minimum touch targets and 16px input font size to eliminate iOS auto-zoom.
  - Web Application Manifest (`manifest.webmanifest`) and responsive meta viewport.
- **Multi-Tier SLA Escalation Engine**: Automated hierarchical escalation across 4 operational levels (`L1 Caretaker` → `L2 Hostel Warden` → `L3 Chief Warden` → `L4 Admin / Dean`) with overdue countdowns and alert triggers.
- **Interactive Kanban Board**: Drag-and-drop ticket status transitions powered by SortableJS with touch long-press delay, server-side validation, error snap-back, and activity auditing.
- **Real-Time Operational Analytics**:
  - Staff operational dashboard with Chart.js visualization (monthly trends, category distribution, turnaround duration per hostel).
  - Hosteler personalized helpdesk with quick complaint actions.
- **Global Command Palette (`⌘K` / `Ctrl + K`)**: Instant keyboard-driven navigation and live debounced ticket search.
- **Enterprise Utilities**:
  - Filtered CSV exports (`/tickets/export/csv/`).
  - Saved user filter presets.
  - Staff bulk status update and bulk reassignment.
  - Real-time notification badge with 30s HTMX polling.
  - Custom branded 403, 404, and 500 error pages.

---

## 🏗️ Technology Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.12+ / 3.14, Django 5.2.x |
| **Interactivity** | HTMX 1.9.12 (AJAX partial swaps), Alpine.js 3.13.8 (client state) |
| **Styling** | Vanilla CSS with unified Design Tokens (`tokens.css`), 13px base font, Frappe/ERPNext dense aesthetic |
| **Visuals & Charts** | Chart.js 4.4.2, Lucide Icons, SortableJS 1.15.2 |
| **Database** | SQLite (Dev) / PostgreSQL (Production) |
| **Static & Media** | WhiteNoise with compressed manifest storage, Pillow |
| **Testing** | `pytest`, `pytest-django`, `factory_boy`, `freezegun` |

---

## 👥 Demo User Credentials

The seed command creates sample users across all system roles. All passwords for demo accounts are set to `pass1234` (except admin: `admin123`):

| Role | Login ID | Password | Scope | Escalation Level |
|---|---|---|---|---|
| **Admin** | `admin` | `admin123` | Campus-wide & Config | Level 4 |
| **Chief Warden** | `chief_warden` | `pass1234` | All Hostels Oversight | Level 3 |
| **Warden (BH-A)** | `warden_bha` | `pass1234` | Boys Hostel A | Level 2 |
| **Warden (GH-B)** | `warden_ghb` | `pass1234` | Girls Hostel B | Level 2 |
| **Caretaker (BH-A)** | `caretaker_bha1` | `pass1234` | Boys Hostel A Maintenance | Level 1 |
| **Caretaker (BH-A)** | `caretaker_bha2` | `pass1234` | Boys Hostel A Maintenance | Level 1 |
| **Caretaker (GH-B)** | `caretaker_ghb1` | `pass1234` | Girls Hostel B Maintenance | Level 1 |
| **Caretaker (GH-B)** | `caretaker_ghb2` | `pass1234` | Girls Hostel B Maintenance | Level 1 |
| **Hosteler (Boys)** | `student_01` | `pass1234` | Room 1101, BH-A | N/A |
| **Hosteler (Girls)** | `student_09` | `pass1234` | Room 1101, GH-B | N/A |

> **Quick Login Tip**: The login page at `/accounts/login/` features **Quick Demo Login buttons** for one-click access as any role!

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone <repo-url>
cd Hostel-Ticket-System

# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Or on Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements/dev.txt
```

### 2. Environment Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

### 3. Run Migrations & Seed Demo Data

```bash
# Run database migrations
python manage.py migrate

# Populate hostels, rooms, role accounts, and 60 realistic tickets
python manage.py seed_demo_data
```

### 4. Start Development Server

```bash
python manage.py runserver
```

Open your browser at **`http://127.0.0.1:8000/`**.

---

## ⏱️ Background Jobs & Periodic Commands

The system includes management commands designed to be triggered via cron or Celery beat:

1. **Automated SLA Escalation Checker**:
   ```bash
   python manage.py run_escalations
   ```
   Evaluates all active tickets against their SLA deadline, cascades breached tickets to the next tier, notifies assignees, and marks Level 4 breaches as `is_overdue=True`.

2. **Auto-Close Resolved Tickets**:
   ```bash
   python manage.py auto_close_tickets
   ```
   Automatically closes tickets that have been in `RESOLVED` status for more than 72 hours without student reopen.

3. **Purge Soft-Deleted Tickets (Retention Pruning)**:
   ```bash
   python manage.py purge_deleted            # Dry run: previews eligible tickets older than 90 days
   python manage.py purge_deleted --confirm  # Permanently removes soft-deleted tickets past retention
   ```

4. **Publish Scheduled Announcements**:
   ```bash
   python manage.py publish_scheduled_announcements
   ```
   Publishes scheduled announcements that have reached their target publication timestamp.

5. **Seed Default SLA Matrices**:
   ```bash
   python manage.py seed_sla_defaults
   ```
   Populates baseline SLA response and resolution targets for all priorities (Urgent, High, Medium, Low) across operational tiers.

6. **Reset User Password (Operator CLI)**:
   ```bash
   python manage.py reset_user_password <login_id> [--password <new_password>]
   ```
   Resets passwords directly from the terminal without web UI dependencies.

7. **Import Allowed Roll Numbers (Operator CLI)**:
   ```bash
   python manage.py import_allowed_roll_numbers <path_to_csv_or_txt>
   ```
   Bulk imports approved student roll numbers into the verification whitelist.


---

## 💾 Database Backup & Restore Runbook

To safely backup and restore the SQLite database during migrations or maintenance:

```bash
# 1. Create a timestamped snapshot
cp db.sqlite3 db.sqlite3.bak-$(date +%Y%m%d%H%M%S)

# 2. Verify snapshot integrity
sqlite3 db.sqlite3.bak "PRAGMA integrity_check;"

# 3. Restore snapshot if needed
cp db.sqlite3.bak db.sqlite3
python manage.py migrate --check
```

---

## 🐳 Docker Deployment

To deploy using Docker Compose with PostgreSQL:

```bash
# Build and start services
docker-compose up --build -d

# View service logs
docker-compose logs -f web
```

The application will be accessible at **`http://localhost:8000/`**.

---

## 🧪 Testing & Code Quality

Run the comprehensive test suite with `pytest`:

```bash
# Run all test suites
pytest

# Run Access Cleanup & Staff Management test suite
pytest tests/test_access_cleanup.py

# Hardcoded color audit test
pytest tests/test_no_hardcoded_colors.py
```

Test suites cover:
- Route permissions and removed route 404 verification across all user roles.
- Chief Warden administrative parity and administrative peer invariant protection.
- Full staff management lifecycle (create, update, login ID change, temp pw reset, active ticket deactivation blocker, audit logging).
- Community removal verification (route matrix, grep guards, legacy data isolation, ticket priority source of truth).
- Slim ticket settings CRUD and SLA fallback determination.
- Hostel-only residence onboarding and ticket creation.
- Safe soft-delete rules (D7 status/comment checks), 8s undo toast tokens, and admin restoration.
- Theme switching persistence, zero-flash top-of-head script, and automated CSS/template color token guards.
- Mobile bottom navigation, card-list table transformations, touch Kanban fallbacks, and photo uploads.
- Race-condition safe sequential ticket numbering (`HTL-YYYY-00001`).
- Multi-tier escalation hierarchy and automated background tasks.

## 📁 Project Structure

```
Hostel-Ticket-System/
├── apps/
│   ├── accounts/         # Custom User model, Roles, authentication views & forms
│   ├── core/             # Base views, templatetags (ui.py), context processors, errors
│   ├── hostels/          # Hostel, Block, Room models and management views
│   ├── tickets/          # Core Ticket engine, Kanban, Escalation, Routing, Actions
│   │   ├── services/     # Pure business logic (escalation.py, routing.py, status.py, numbering.py)
│   │   └── views/        # Thin views (list, detail, create, actions, kanban)
│   ├── dashboard/        # Role-scoped analytics selectors and Chart.js endpoints
│   └── notifications/    # Notification model, badge polling, mark as read
├── config/
│   └── settings/         # Split settings (base.py, dev.py, prod.py)
├── static/
│   ├── css/              # tokens.css, base.css, layout.css, components.css, kanban.css, dashboard.css
│   ├── js/               # app.js, kanban.js, charts.js
│   └── vendor/           # Local vendored HTMX, Alpine.js, Chart.js, Lucide, SortableJS
├── templates/            # Component-driven ERPNext-style UI templates
├── tests/                # 35 Pytest unit and integration tests
├── Dockerfile            # Production container specification
├── docker-compose.yml    # Web + PostgreSQL stack definition
└── manage.py
```

---

## 🔒 Security & Best Practices

- **Zero Template Business Logic**: All business rules reside strictly in `services/`.
- **Internal Note Privacy**: Queries filter `TicketComment` and `TicketActivity` at the database level so internal staff notes never leak into hosteler responses.
- **CSRF Token Injection**: Embedded automatically in all HTMX requests via `hx-headers`.
- **Enterprise Density**: Compact 13px base typography, neutral color schemes, pastel status indicators, and keyboard shortcuts.
