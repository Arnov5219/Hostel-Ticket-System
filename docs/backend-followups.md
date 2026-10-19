# Backend Follow-ups

> Issues identified during UI/UX audit and implementation that belong to data, migrations, or backend logic rather than frontend styles/templates.

## 1. Seed Data Inconsistencies (P2)
- **Duplicate / Inconsistent Hostel Names & Codes:**
  - In initial demo seeds, both `HOSTEL_A` and `BH-A` existed with the name "Boys Hostel A".
  - Cleaned up in dev DB and consolidated into `BH-A` and `GH-B`.
- **Duplicate Staff Usernames:**
  - "Dr. Ramesh Verma" was seeded with two different usernames in historical scripts: `warden_a` and `warden_bha`.
  - Recommended fix: standardize seed script and deduplicate users in production migration.

## 2. Server-side Query & Pagination Enhancements
- **Rooms Management:**
  - Currently loads first 100 rooms (`[:100]`) without server-side pagination or search parameters.
  - Future enhancement: add standard paginator `Paginator(qs, 25)` when room management is needed.
- **Kanban Server-side Filters:**
  - Kanban currently filters via client-side Alpine or full page reload. Could benefit from dedicated HTMX partial swapping for filters (`/tickets/kanban/?hostel=...`).

## 3. HostelFlow UI Redesign Deferred Items (Mockup features without backend)
- **OTP-Confirmed Resolution:** Mockup proposed 6-digit OTP confirmation on "Resolved & Verified". Kept as user confirmation button ("Waiting for your confirmation") until OTP service is engineered.
- **SMS & Push Preferences:** Mockup proposed SMS Updates & App Push toggles on raise ticket and settings. Deferred pending SMS gateway/push service integration.
- **In-App Quick Chat:** Mockup showed Quick Chat for tickets. Replaced with real internal notes / comments activity stream.
- **Technician Roster & Availability:** Mockup showed "28 Technicians On-Duty" with Roster button. Omitted as there is no technician duty model.
- **Announcement Event Time:** Mockup showed "Tomorrow, 10 AM" time on announcement banners. Currently announcements track publication timestamps (`created_at`).
- **Campus Residential Hub Photos:** Mockup featured campus photo panels on login/help. Deferred until verified assets and photo storage are provisioned.

