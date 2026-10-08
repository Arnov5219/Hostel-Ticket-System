# Hostel Ticket System: Real Hostel Structure, Block & Subcategory Removal, Self-Registration

> **For Antigravity.** Feature addendum that **corrects the data model to match the real college** and adds **new-user registration**. Read together with `HOSTEL_TICKET_SYSTEM_PLAN.md`, `UI_UX_IMPROVEMENT_PLAN.md`, `COMMUNITY_FEED_AND_ANNOUNCEMENTS_PLAN.md`, and `DELETE_DARKMODE_MOBILE_RESIDENCE_PLAN.md`.
>
> **Where this document conflicts with those, this document wins.** The "Supersedes" table in Section 2 lists every earlier statement that changes.
>
> Backend changes are allowed. Standing rules: logic in `services/`, permissions in querysets, tokens-only styling, mobile-first, no new dependency without asking, tests for every service.

---

## 1. The Real Structure

- **12 boys hostels:** `BH-1` to `BH-12`.
- Each hostel has **3 floors**.
- Each floor has **40 rooms**, so 120 rooms per hostel and **1,440 rooms** in total.
- **There are no blocks.** The hierarchy is simply **Hostel → Floor → Room**.
- **Subcategories do not exist.** A ticket has one Category only.

### 1.1 Assumptions (defaults: tell me if any are wrong)

| # | Assumption | Default |
|---|---|---|
| A1 | Floors are numbered **1, 2, 3**. | Yes (if you use Ground/1st/2nd, run the seed with `--first-floor 0` and the label shows "Ground") |
| A2 | Room numbers are `floor × 100 + n`, with n from 1 to 40: **101–140, 201–240, 301–340**. Unique within a hostel. | Yes |
| A3 | Room capacity (beds) is **2**, editable per room. | Yes (seed option `--capacity`) |
| A4 | There are no girls' hostels right now. The `gender_type` field stays, so `GH-n` hostels can be added later from Admin. | Yes |
| A5 | **One Caretaker (L1) and one Warden (L2) per hostel**, plus one Chief Warden and one Admin for the campus. A staff user belongs to one hostel. | Yes |
| A6 | Students sign in with their **Roll Number**. | Yes |
| A7 | UI shows the hostel by its **code** (`BH-4`) everywhere. The long name "Boys Hostel 4" is only used in Admin forms. | Yes |

---

## 2. Supersedes (what changes in the earlier plans)

| Earlier statement | New rule |
|---|---|
| `Block` model; `Room.block` FK; Blocks screens and button; "Blocks" column on Hostels | **Removed.** `Room` belongs directly to `Hostel` and has an integer `floor`. |
| Residence = Hostel → Block → Room | Residence = **Hostel → Floor → Room** (floor is a filter step, not a stored model). |
| Chain validation `room.block.hostel == hostel` | `room.hostel == hostel` (and `room.floor == selected floor` for the UI step). |
| `GET /hostels/options/blocks/`, `/hostels/options/rooms/?block=` | `/hostels/options/floors/?hostel=` and `/hostels/options/rooms/?hostel=&floor=` |
| Admin sub-nav: Hostels · **Blocks** · Rooms · Staff · Responsibility · Routing & SLA | Hostels · Rooms · Staff · **Residents** · Responsibility · Routing & SLA |
| Community feed label "A hosteler · Block 2" | "A hosteler · **BH-4 · Floor 2**" (room is still never shown to other hostelers) |
| Raise-ticket location chip `Boys Hostel 1 · Block 2 · Room 204` | `BH-4 · Floor 2 · Room 204` |
| `SubCategory` model, `Ticket.sub_category`, "Sub-issue (optional)" field | **Removed.** |
| Seed: 3 demo hostels (Boys Hostel 1/2/A, Girls…) with duplicates | Seed: exactly the 12 real hostels. Old demo hostels are removed. |
| Seed: routing rule for every Hostel × Category (27 rows) | **No per-category rules by default.** Each hostel just has its L1 default responsible staff. Category rules are exceptions only (Section 4.5). |
| Login: sign in only; accounts created by Admin | Login page also offers **Create account** for new hostelers (Section 6). |

---

## 3. Data Model Changes

### 3.1 `hostels` app
- **Delete** the `Block` model and everything that references it (admin, forms, views, URLs, templates, serializers, tests, seed).
- **`Hostel`**: keep `name`, `code` (unique, for example `BH-4`), `gender_type`, `address`, `is_active`. Remove any block-related counters. Add derived properties (not stored): `floors` (distinct `Room.floor` values), `room_count`, `resident_count`.
- **`Room`** new shape:

| Field | Type | Notes |
|---|---|---|
| `hostel` | FK Hostel, `related_name="rooms"` | Required |
| `floor` | PositiveSmallInt | 1 to N (0 allowed for ground) |
| `room_number` | CharField(10) | `101` … `340` |
| `capacity` | PositiveSmallInt, default 2 | |
| `is_active` | Bool, default True | Inactive rooms are not selectable |

  `UniqueConstraint(hostel, room_number)`, and an index on `(hostel, floor)`. Validation: `room_number` starts with the floor digit when using the default scheme (warn only, do not block, so unusual numbering still works).
- **Service `hostels/services.py`**
  - `generate_rooms(hostel, floors=3, rooms_per_floor=40, capacity=2, first_floor=1)`: creates missing rooms only (idempotent), returns a count.
  - `room_options(hostel, floor)`: active rooms with `resident_count` annotation (used by the room picker).

### 3.2 `tickets` app
- **Delete** `SubCategory` and the `Ticket.sub_category` field. Remove the field from forms, filters, list/detail templates, CSV export, admin inline, serializers, and tests.
- Before dropping the column, the migration logs how many tickets had a sub-category value (print only; nothing is migrated).
- `Ticket.hostel` and `Ticket.room` remain required for new tickets. `Ticket.room` is validated with `room.hostel == ticket.hostel`.

### 3.3 `accounts` app (for registration, Section 6)
Add to `User`:

| Field | Type | Notes |
|---|---|---|
| `is_verified` | Bool, default **False** for self-registered, **True** for Admin-created/seeded/imported | Warden verifies residents |
| `verified_by` | FK User, null | |
| `verified_at` | DateTime, null | |
| `registration_source` | choices `SELF`, `ADMIN`, `IMPORT` | |
| `rejected_reason` | CharField(200), blank | If a registration is rejected |

`login_id` (roll number) is stored **uppercased and trimmed**, with a case-insensitive unique check.

Optional (only if `REGISTRATION_MODE = ALLOWLIST`): **`AllowedRollNumber`** (`roll_no` unique, `name` blank, `hostel` FK null, `used_by` FK null, `used_at` null), with an Admin CSV import screen.

### 3.4 Migrations and existing data
1. **Preferred path (the DB currently holds demo data):** back up, drop, migrate from scratch, then run `seed_hostels` and `seed_demo_data`. This removes the duplicate "Boys Hostel A" rows and the `10 10` oddities for good.
2. **Safe path (if any real data exists):** write the migrations so they work on a populated database:
   - (a) add `Room.hostel` as nullable and copy `block.hostel`;
   - (b) check for duplicate `(hostel, room_number)` pairs and stop with a clear error listing them;
   - (c) make `Room.hostel` non-null and add the unique constraint;
   - (d) drop `Room.block`, delete `Block`;
   - (e) drop `Ticket.sub_category` and delete `SubCategory`.
   Test on a copy of the database before running it for real.

---

## 4. Hostel Administration (admin screens, 12 hostels, 1,440 rooms)

### 4.1 Seed command `python manage.py seed_hostels`
- Options: `--hostels 12 --prefix BH --floors 3 --rooms-per-floor 40 --capacity 2 --first-floor 1`.
- Idempotent (`get_or_create`). Prints a summary: `12 hostels, 36 floors, 1440 rooms`.
- `--remove-demo` deletes the old demo hostels **only if they have no tickets**, otherwise it lists them and stops.
- `seed_demo_data` is updated: one Caretaker and one Warden per hostel (`caretaker_bh1`… `warden_bh1`…), one Chief Warden, one Admin, 3 to 5 hostelers per hostel with valid rooms, and tickets spread across hostels.

### 4.2 Hostels page
Columns: **Hostel** (`BH-4`, with the name muted) · **Floors** · **Rooms** · **Residents** (count and occupancy bar) · **Level 1 staff** · **Status** · Actions (Edit, Change staff, Deactivate). 12 rows fit one page. Buttons: **Rooms**, **+ Add Hostel**. The **Blocks** button and column are removed.
- **Add Hostel form:** name, code, type, plus an optional **"Generate rooms now"** section (floors, rooms per floor, capacity, first floor) that calls `generate_rooms`.

### 4.3 Rooms page (1,440 rows: needs real list controls)
- Server-side pagination (50 per page), **filters:** Hostel (12), Floor, Status, Occupancy (Empty / Partial / Full); **search** by room number.
- Columns: Room · Hostel · Floor · Capacity · Residents · Status · Actions (Edit, Deactivate). Remove the Block column.
- Mobile: card list (per `DELETE_DARKMODE_MOBILE_RESIDENCE_PLAN.md`).

### 4.4 Responsibility page
12 rows: Hostel (`BH-n`) · Level 1 responsible staff · Level 2 Warden · Status · Change staff. Add a **"Missing staff"** badge (amber) when a hostel has no Caretaker or no Warden, because with 12 hostels gaps are easy to miss. The dashboard (Admin) shows a small "Hostels without a Caretaker" alert if any.

### 4.5 Routing & SLA page
- Routing resolution order stays: (Hostel + Category) → (Hostel only) → Hostel Level 1 default → Warden fallback. The **Hostel Level 1 default is now the normal case**. The Routing Rules tab lists **exceptions only** (for example "Internet / Wi-Fi in all hostels → campus network technician"). Show an info callout explaining that.
- With 12 hostels the table can grow, so keep it **grouped by hostel** (collapsible) and add a hostel filter.

### 4.6 Other places that list hostels
- Ticket list, Kanban, dashboard, and Announcement audience pickers: the Hostel filter now has 12 options (`BH-1`…`BH-12`), sorted naturally (BH-2 before BH-10). Provide a `natural_sort` helper.
- **Announcement audience:** besides "All hostels" and multi-select, add quick actions **"Select all"** and **"Select range (BH-1 to BH-4)"** to avoid 12 manual clicks.
- Dashboard charts with 12 hostels (for example Avg Resolution Time): use **horizontal bars**, sorted, with the label `BH-n`.

---

## 5. Removing Subcategories (checklist)
- [ ] Delete `SubCategory` model, admin inline, and migration steps.
- [ ] Remove the "Sub-issue" select from the Raise Ticket form (desktop and mobile) and its HTMX dependency.
- [ ] Remove from ticket detail, list columns, filters, CSV export, search, notifications text, and tests/factories.
- [ ] Categories admin tab shows only: name, icon, default priority, **allow in community**, active.
- [ ] Final category set (9): Electrical · Plumbing / Water · Internet / Wi-Fi · Cleaning / Housekeeping · Furniture · Mess / Food · Security · Maintenance · Other. Security and Other keep `allow_community=False`.
- [ ] `grep -ri "subcategor\|sub_categor\|sub-issue"` returns nothing in `apps/`, `templates/`, `static/`, and `tests/`.

---

## 6. New Hosteler Registration

### 6.1 Rules
- Anyone can create a **Hosteler** account from the login page. The role is **always** `HOSTELER` on the server. A `role` value in the POST is ignored.
- Registration collects **residence** (Hostel, Floor, Room), so the onboarding gate is not needed afterwards. The gate stays only for older accounts that lack residence.
- Self-registered accounts start **unverified**. A Warden verifies them. This stops fake accounts from spamming the community feed.

**Unverified residents can:** sign in, raise tickets (kept private; staff see an "Unverified" chip), see announcements.
**Unverified residents cannot:** share tickets to the community feed, repost, or post community comments. A banner explains: "Your room is waiting for your Warden's verification."

### 6.2 Settings

| Setting | Values | Default |
|---|---|---|
| `REGISTRATION_MODE` | `OPEN` (instant account, unverified) · `APPROVAL` (account inactive until a Warden approves) · `ALLOWLIST` (roll number must be in the imported list) · `CLOSED` (no registration link) | `OPEN` |
| `ROLL_NO_REGEX` | Regex for valid roll numbers | `^[A-Za-z0-9._-]{4,20}$` (tighten to your college's real format) |
| `REGISTRATION_RATE_LIMIT` | Attempts per IP per hour | 5 |

### 6.3 Form fields
```
Create your account
  Full name *            [                          ]
  Roll number *          [                          ]   (this is your login ID)
  Phone                  [                          ]   (optional, 10 digits)
  Email                  [                          ]   (optional; needed for password reset)
  Password *             [                      👁 ]
  Confirm password *     [                      👁 ]

Where do you stay?
  Hostel *               [ BH-1 ] [ BH-2 ] ... (select)
  Floor *                ( 1 )  ( 2 )  ( 3 )                  ← segmented buttons
  Room *                 ┌────┬────┬────┬────┬────┐
                         │101 │102 │103 │104 │105 │  ... 40 rooms, 5 per row on phones,
                         ├────┼────┼────┼────┼────┤  10 per row on desktop
                         │... │    │    │    │    │
                         └────┴────┴────┴────┴────┘
  ⓘ Room 204 already has 2 residents. (warn-only)

  [x] I confirm these details are correct.
  [            Create account            ]
  Already have an account? Sign in
```
- **Room picker:** radio inputs styled as chips (so it works without extra JS, is keyboard accessible, and has 44px targets). Selected chip = filled accent. Rooms at or over capacity show a small "Full" label but remain selectable (warn-only, per D5 of the previous plan; `ENFORCE_ROOM_CAPACITY` can make it a hard block).
- **Cascade:** choosing a Hostel loads the Floor buttons (HTMX); choosing a Floor loads the 40 room chips. The Room field is disabled until a floor is chosen.
- All fields keep their values after a validation error. Errors appear inline under each field and as a summary at the top for screen readers.
- Password: shown/hidden toggle, Django's password validators (min length, not common, not all digits), live strength hint.

### 6.4 Server-side validation and anti-abuse (`accounts/services/registration.py`)
- `register_hosteler(data, request_meta)` in a single transaction:
  1. Registration mode check (`CLOSED` → 404; `ALLOWLIST` → roll number must exist and be unused).
  2. Normalize roll number (trim, uppercase); regex check; case-insensitive uniqueness.
  3. Validate name (2 to 80 chars), optional phone (digits only, 10), optional email (valid; unique if given), password validators, matching confirmation.
  4. Validate residence: active hostel, active room, `room.hostel == hostel`, `room.floor == floor`.
  5. Create the `User` with `role=HOSTELER`, `registration_source=SELF`, `is_verified=False` (and `is_active=False` in `APPROVAL` mode); call `set_residence(...)` so `ResidenceHistory` is written.
  6. Notify the hostel's Warden and Caretaker ("New resident awaiting verification: Arnov R., BH-4 · Room 204"), batched to one notification per hostel per hour.
  7. Log the user in (except in `APPROVAL` mode) and redirect to Home with a toast.
- **Honeypot** field (hidden, must be empty) and a **time check**: a signed timestamp (`django.core.signing`) rendered in the form; submissions faster than 3 seconds or older than 1 hour are rejected.
- **Rate limit** by IP using Django's cache (no new dependency), applied to both registration and login.
- The same generic error style for everything unexpected; never reveal internals.
- CSRF as usual. No role, `is_staff`, `is_verified`, or `hostel` of staff can be set from the form.
- If a roll number already exists: "This roll number is already registered. Sign in instead." with a link.

### 6.5 Verification workflow (Warden)
- New screen **Residents** (`/manage/residents/`, Warden for their hostel, Chief Warden and Admin for all): table with Name · Roll no. · Hostel · Floor/Room · Phone · Registered · Status (Unverified, Verified, Rejected) · Actions (**Verify**, **Reject**, **Reset password**).
  - Filters: hostel, status, search by name or roll number. Default view: Unverified first.
  - Bulk **Verify selected**. Reject needs a reason (stored in `rejected_reason`) and deactivates the account; at the next login attempt the person sees: "Your registration was not approved. Please contact your Warden."
  - **Reset password** sets a temporary password shown once to the staff user (useful when no email is configured) and forces a change at the next login (`must_change_password` flag, or Django's `set_unusable` plus a reset link when email is enabled).
- Verification notifies the hosteler ("Your room has been verified") and unlocks community features.
- Warden dashboard card: **"Pending residents (N)"** linking to the screen.
- Sidebar: **Residents** item for Warden and above (users-check icon) with a count badge.

### 6.6 Login page changes
```
┌──────────────────────────────┐
│            [H]               │
│     Hostel Ticket System     │
│  [ Sign in | Create account ]│   ← segmented tabs (real links: /accounts/login/ and /accounts/register/)
│  ...form for the active tab  │
└──────────────────────────────┘
```
- Both pages use the bare auth layout (no sidebar, no search) as defined earlier.
- If `REGISTRATION_MODE = CLOSED`, the "Create account" tab is not shown.
- "Forgot password?" link appears only when an email backend is configured (`EMAIL_ENABLED`); otherwise show "Forgot password? Ask your Warden to reset it."
- The registration page is mobile-first: one column, 16px inputs, 44px targets, sticky "Create account" bar on small screens, room chips 5 per row.
- Works in light and dark themes (tokens only).

---

## 7. Impact on Other Features

| Feature | Change |
|---|---|
| Community feed | Scope = same hostel (`BH-n`); label "BH-4 · Floor 2"; unverified users can read but not repost or comment, and their tickets cannot be shared. |
| Announcements | Audience = any subset of the 12 hostels. Warden still restricted to their own hostel. |
| Routing / escalation | Unchanged logic. With default hostel-level L1 and L2 per hostel, escalation walks L1 → L2 (same hostel) → L3 → L4. |
| Raise ticket | Location = Hostel (locked to residence) · Floor · Room chips · optional Location detail; no sub-issue field. |
| Delete ticket | Unchanged. |
| Dashboard | 12-hostel charts as horizontal bars; "Most-reported issues" shows `BH-n`. Admin alert for hostels without staff. |
| Staff list/Kanban filters | Hostel filter with 12 natural-sorted options. |

---

## 8. URL Map (additions and changes)

| URL | Method | Purpose |
|---|---|---|
| `/accounts/register/` | GET / POST | Registration |
| `/hostels/options/floors/?hostel=` | GET | Floor buttons partial |
| `/hostels/options/rooms/?hostel=&floor=` | GET | Room chip grid partial (with resident counts) |
| `/manage/residents/` | GET | Residents list |
| `/manage/residents/<id>/verify/`, `/reject/`, `/reset-password/` | POST | Warden+ actions |
| `/manage/residents/bulk-verify/` | POST | Warden+ |
| `/manage/rooms/` | GET | Filtered and paginated rooms |
| `/manage/hostels/<id>/generate-rooms/` | POST | Admin |
| **Removed** | | `/manage/blocks/*` and `/hostels/options/blocks/` (must return 404) |

---

## 9. Build Phases

### Phase R0: Prepare
- [ ] Branch `feature/real-structure-registration`.
- [ ] Decide DB path (Section 3.4): reset and reseed (preferred) or populated-DB migration.
- [ ] Run a repo-wide search for `Block`, `block`, `SubCategory`, `sub_category` and list every hit in `docs/removal-audit.md`.

### Phase R1: Hostel structure
- [ ] New `Room` model, migrations, `generate_rooms`, `room_options`, `seed_hostels`, updated `seed_demo_data`.
- [ ] Remove Block everywhere (models, admin, forms, views, URLs, templates, tests).
- [ ] Hostels, Rooms (filters, pagination), Responsibility ("Missing staff"), and Routing pages updated; admin sub-nav updated.
- **Done when:** `seed_hostels` produces 12 hostels, 36 floors, 1,440 rooms; no code references blocks; the admin pages work with 1,440 rooms quickly (page load under 500 ms locally).

### Phase R2: Remove subcategories
- [ ] Complete the Section 5 checklist and migrations.
- **Done when:** a ticket can be raised, listed, exported, and edited with no sub-category anywhere, and the grep check is clean.

### Phase R3: Floor-and-room selection
- [ ] Floor and room options partials, the room chip picker component (reusable for onboarding, registration, and the raise-ticket form), natural sort helper.
- [ ] Update onboarding, profile residence, and raise-ticket Location section, and server-side chain validation.
- **Done when:** a hosteler can pick Hostel → Floor → Room on desktop and a 375px phone; a crafted POST with a room from another hostel is rejected.

### Phase R4: Registration
- [ ] User fields and migration, registration service, form, page, login tabs, honeypot, time check, rate limit, password validators.
- [ ] Residents screen (verify, reject, bulk verify, reset password), notifications, restrictions for unverified users, sidebar item and dashboard card.
- [ ] Settings for `REGISTRATION_MODE`, `ROLL_NO_REGEX`, rate limit; optional allowlist import screen if `ALLOWLIST` is wanted now.
- **Done when:** a new student can create an account, land on Home with residence set, raise a ticket, and be verified by their Warden; registration cannot create a staff role under any POST.

### Phase R5: Integration and QA
- [ ] Update the feed labels, announcement audience helpers (select all, range), Kanban/list/dashboard hostel filters, 12-hostel charts.
- [ ] Seed data, README updates (structure, registration modes, seed commands).
- [ ] Full regression, mobile and dark-mode pass on the new screens.

---

## 10. Testing Plan

| Area | Tests |
|---|---|
| Structure | `seed_hostels` creates exactly 12 hostels, 36 floors, 1,440 rooms; idempotent on re-run; room numbers follow 101–140 / 201–240 / 301–340; unique `(hostel, room_number)`; `generate_rooms` adds only missing rooms; natural sort puts BH-2 before BH-10. |
| Block removal | No model, URL, template, or form references to blocks; `/manage/blocks/` and the blocks options endpoint return 404; migration passes on a populated copy; duplicate-room conflict is reported clearly. |
| Subcategory removal | Raise, edit, filter, export, and detail all work without the field; grep guard test in CI. |
| Residence | Room from another hostel rejected; inactive room rejected; floor mismatch rejected; capacity warn-only and the hard-block setting. |
| Registration | Creates `HOSTELER` only, even if `role=ADMIN` is posted; case-insensitive duplicate roll number blocked; regex enforced; password validators; honeypot and too-fast submissions rejected; rate limit returns 429 after the limit; mode `CLOSED` hides the page; mode `APPROVAL` leaves the account inactive; mode `ALLOWLIST` rejects unknown roll numbers; `ResidenceHistory` written; Warden notified once per hour per hostel. |
| Verification | Warden can verify and reject only their hostel; Chief Warden and Admin can act on all; bulk verify; rejected user sees the message at login; unverified users cannot repost, comment publicly, or share to the feed; verified users can. |
| UI | Room chip picker keyboard operation and 44px targets at 375px; login/register tabs; no horizontal overflow; both themes. |
| Regression | Existing community, announcements, delete, escalation, and status workflow tests stay green. |

---

## 11. Acceptance Checklist
- [ ] The system contains exactly BH-1 to BH-12, each with 3 floors and 40 rooms per floor.
- [ ] No block feature remains anywhere (code, UI, URLs, seed, docs).
- [ ] No subcategory remains anywhere.
- [ ] Hostelers choose Hostel → Floor → Room with a mobile-friendly picker, both at registration and when raising a ticket, validated on the server.
- [ ] A new student can register from the login page, is logged in, and has a saved room.
- [ ] Registration cannot create staff accounts, is rate limited, and is protected by honeypot and time checks.
- [ ] Wardens can verify or reject new residents; unverified users have the documented limits.
- [ ] Admin pages cope with 1,440 rooms (filters, search, pagination).
- [ ] Announcements and filters handle 12 hostels with natural sorting and quick-select helpers.
- [ ] All tests pass and the README documents structure, seed commands, and registration modes.

---

## 12. Rules for the Agent
1. Do not reintroduce `Block` or `SubCategory` in any form. If something seems to need them, ask.
2. A registration request may only ever create a `HOSTELER`. Never read role or permission fields from user input.
3. Validate hostel, floor, and room on the server for every form that has a location.
4. Always sort hostels naturally (BH-2 before BH-10).
5. Seed and demo commands must be idempotent.
6. Reuse the room chip picker component; do not build separate versions.
7. Keep everything mobile-first, token-based, and tested in both themes.
8. Do not add dependencies without asking (rate limiting uses Django's cache; the time check uses `django.core.signing`).
9. Announce the phase at the start of each task and commit with `feat:`, `refactor:`, `fix:`, or `test:` prefixes after each phase.
