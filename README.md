# Hostel Ticket System 🏢🎫

A production-grade, enterprise-dense web application for campus hostel ticket, maintenance, and grievance management built with **Django 5.x**, **HTMX**, **Alpine.js**, and an aesthetic design system inspired by **Frappe / ERPNext**.

---

## 🌟 Key Features

- **Multi-Tier SLA Escalation Engine**: Automated hierarchical escalation across 4 operational levels (`L1 Caretaker` → `L2 Hostel Warden` → `L3 Chief Warden` → `L4 Admin / Dean`) with overdue countdowns and alert triggers.
- **Strict Role-Based Access Control**:
  - **Hostelers**: Submit tickets with attachments, track status, add comments, confirm resolution, and rate service (internal notes are strictly masked).
  - **Caretakers (L1)**: Triage, update status, add public/internal notes, assign, and resolve within their hostel.
  - **Wardens (L2)**: Handle L1 escalations, monitor hostel-wide maintenance, reassign, and override statuses.
  - **Chief Warden (L3)**: Campus-wide operational oversight across all hostels, handle L2 escalations.
  - **Administrators (L4)**: System configuration, routing rules, SLA matrices, user management, and critical overdue escalations.
- **Interactive Kanban Board**: Drag-and-drop ticket status transitions powered by SortableJS with server-side validation, error snap-back, and activity auditing.
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
# Run all 35 test cases
pytest

# Code formatting and linting
ruff check .
black --check .
```

All 35 tests cover:
- Authentication & custom user role permissions.
- Race-condition safe sequential ticket numbering (`HTL-YYYY-00001`).
- SLA policy lookup and fallback routing rules.
- Status workflow matrix with illegal transition rejection.
- Automated and manual multi-tier escalation hierarchy.
- Notification dispatch and polling endpoints.
- Analytics selectors and Chart.js JSON APIs.
- Filtered CSV exports, quick search, and staff bulk actions.
- Custom error page handlers.

---

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
