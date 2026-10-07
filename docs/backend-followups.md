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
