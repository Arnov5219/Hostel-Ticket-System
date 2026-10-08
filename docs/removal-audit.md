# Removal Audit: Block & SubCategory

This document audits all occurrences of `Block` / `block` and `SubCategory` / `sub_category` across the codebase prior to migration to the real college hostel structure (Hostel → Floor → Room) and single-tier categories.

## 1. SubCategory Audit
- **Models**:
  - `apps/tickets/models.py`: `SubCategory(TimeStampedModel)` model definition.
  - `apps/tickets/models.py`: `Ticket.sub_category` foreign key field (`to='tickets.SubCategory'`, `null=True`, `blank=True`).
- **Forms**:
  - `apps/tickets/forms.py`: `TicketForm` references `sub_category` field, widgets, and dynamic querysets.
- **Admin**:
  - `apps/tickets/admin.py`: `SubCategoryAdmin` registration and import.
- **Views & Templates**:
  - `apps/tickets/views/detail.py`: `select_related("sub_category")`.
  - `templates/tickets/create.html`: Subcategory field select input and label.
- **Plans**:
  - Mentioned in earlier plans (`HOSTEL_TICKET_SYSTEM_PLAN.md`), superseded by `HOSTEL_STRUCTURE_AND_REGISTRATION_PLAN.md`.

## 2. Block Audit
- **Models**:
  - `apps/hostels/models.py`: `Block(TimeStampedModel)` model with `hostel`, `name`, `is_active`.
  - `apps/hostels/models.py`: `Room.block` foreign key (`to='hostels.Block'`).
  - `apps/tickets/models.py`: `Ticket.block` foreign key (`to='hostels.Block'`).
  - `apps/accounts/models.py`: `User.has_residence` checks `self.room.block.hostel_id == self.hostel_id`.
  - `apps/accounts/models.py`: `ResidenceHistory` stores `user`, `hostel`, `room`, `changed_by`.
- **Services**:
  - `apps/accounts/services.py`: `set_residence(user, hostel, block, room)` enforces `block` parameter and validation.
  - `apps/tickets/services/location.py`: `validate_location(hostel_id, block_id, room_id, ...)` validates block chain.
- **Views & URLs**:
  - `apps/hostels/views.py`: `block_options` view (`/hostels/options/blocks/`).
  - `apps/hostels/urls.py`: `path("options/blocks/", ...)` route.
  - `apps/accounts/views.py`: onboarding and profile views handle block selection.
- **Forms**:
  - `apps/accounts/forms.py`: `ResidenceForm` has `block` ModelChoiceField and cascading logic.
  - `apps/tickets/forms.py`: `TicketForm` has `block` field and queryset population.
- **Templates**:
  - `templates/accounts/onboarding.html`: Block select dropdown.
  - `templates/accounts/profile.html`: Block select dropdown and residence summary.
  - `templates/tickets/create.html`: Block select field.
  - `templates/hostels/manage_hostels.html`: Reference to blocks button/column if any.
- **Factories & Tests**:
  - `apps/hostels/factories.py`: `BlockFactory`.
  - `tests/test_residence.py`, `tests/test_mobile.py`, `tests/test_deletion.py`: creation of `Block` fixtures.
- **Seed Commands**:
  - `apps/tickets/management/commands/seed_demo_data.py`: creates `bha_b1`, `bha_b2`, `ghb_b1`, `ghb_b2`.
  - `apps/accounts/management/commands/seed_demo_users.py`: creates blocks.

## 3. Action Plan
1. **Hostels & Rooms**:
   - Update `Room` model to belong directly to `Hostel` with `floor` (PositiveSmallIntegerField), `room_number` (CharField), `capacity` (PositiveSmallIntegerField, default 2), `is_active` (BooleanField, default True), and unique constraint `(hostel, room_number)`.
   - Remove `Block` model and `Ticket.block` field.
   - Implement `generate_rooms` and `room_options` in `apps/hostels/services.py`.
   - Implement `seed_hostels` management command generating BH-1 to BH-12 (3 floors, 40 rooms/floor = 1,440 rooms).
2. **SubCategory Removal**:
   - Drop `SubCategory` model and `Ticket.sub_category`.
   - Remove subcategory references from forms, views, templates, exports, and admin.
3. **Residence & Selection**:
   - Update residence chain to Hostel → Floor → Room.
   - Build floor and room options endpoints (`/hostels/options/floors/` and `/hostels/options/rooms/`).
   - Implement reusable room chip picker.
4. **Self-Registration & Verification**:
   - Add verification fields to `User`: `is_verified`, `verified_by`, `verified_at`, `registration_source`, `rejected_reason`.
   - Implement registration service, form, views, rate limiting, and honeypot/timestamp security checks.
   - Implement `/manage/residents/` verification dashboard and actions.
5. **Testing & Regression**:
   - Write unit and integration tests covering all requirements.
   - Run 100% green test suite.
