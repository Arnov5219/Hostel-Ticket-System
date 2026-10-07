# Hostel Ticket System — Revised Hostel & Staff Management Plan

## Purpose

This document revises the Hostel and Staff Management portion of the Hostel Ticket System.

The revised design reflects the actual college structure:

- Each hostel has **one block**.
- Room numbers are **not maintained by the system**.
- Floor numbers are **not maintained by the system**.
- Bed capacity is **not maintained by the system**.
- A hostel normally has **one Level 1 staff member responsible for all issue categories**.
- Admin can add, edit, activate/deactivate hostels.
- Admin can view staff and change their hostel assignments.
- Ticket routing at Level 1 is based on the hostel's responsible staff, not on ticket category.

The existing ticket escalation hierarchy remains:

**Level 1 → Level 2 → Level 3 → Level 4**

---

# 1. Hostel Management

Admin must have a dedicated **Hostel Management** section.

Admin can:

- Add a hostel
- Edit a hostel
- Activate/deactivate a hostel
- Assign or change the responsible Level 1 staff member
- View all hostels

## Hostel Fields

Each hostel contains:

| Field | Description |
|---|---|
| Hostel Name | Name displayed throughout the system |
| Hostel Code | Unique short code |
| Hostel Type | Boys / Girls / Co-ed |
| Address | Hostel location/address |
| Responsible Staff | Primary Level 1 staff member responsible for the hostel |
| Status | Active / Inactive |

## Do Not Include

The system must **not** maintain:

- Block number/name
- Number of blocks
- Room number
- Floor number
- Bed capacity
- Total rooms

The college structure is treated as:

```text
Hostel
   |
   └── Responsible Level 1 Staff
```

There is no separate Block or Room hierarchy in v1.

---

# 2. Hostel Management Screen

The Hostel Management table should contain:

| Hostel Name | Code | Type | Responsible Staff | Status |
|---|---|---|---|---|
| Boys Hostel A | BH-A | Boys | Mukesh Kumar (L1) | Active |
| Girls Hostel B | GH-B | Girls | Anita Devi (L1) | Active |

Do not display:

- Blocks
- Total Rooms
- Room Numbers
- Floors
- Bed Capacity

## Actions

Each hostel should provide actions such as:

- Edit
- Change Responsible Staff
- Activate / Deactivate

If a hostel already has tickets or historical records, do **not** hard-delete it. Mark it as **Inactive** instead.

Historical tickets must remain accessible.

---

# 3. Add Hostel

The Admin should have a:

**+ Add Hostel**

button.

The form should contain:

```text
Add Hostel

Hostel Name *
[________________________]

Hostel Code *
[________________________]

Hostel Type *
[ Boys / Girls / Co-ed ]

Address
[________________________]
[________________________]

Responsible Staff *
[ Select Staff ▼ ]

Status
[ Active ]

             Cancel    Save Hostel
```

## Validation

- Hostel name is required.
- Hostel code is required and unique.
- Hostel type is required.
- Responsible Level 1 staff should be selected.
- Duplicate hostel codes must not be allowed.

---

# 4. Edit Hostel

Admin can edit:

- Hostel name
- Hostel code
- Hostel type
- Address
- Responsible staff
- Active/inactive status

Editing a hostel must not modify the historical hostel information stored on existing tickets.

---

# 5. Staff Management

Add a dedicated **Staff Management** section.

The purpose is to allow Admin to:

- View all staff
- View their roles
- View their escalation level
- View their assigned hostel
- View their current workload
- Change their hostel assignment
- Activate/deactivate staff accounts where appropriate

## Staff Table

Example:

| Name | Role | Level | Assigned Hostel | Active Tickets | Status |
|---|---|---:|---|---:|---|
| Mukesh Kumar | Caretaker | L1 | Boys Hostel A | 5 | Active |
| Anita Devi | Caretaker | L1 | Girls Hostel B | 3 | Active |
| Rajesh Kumar | Warden | L2 | Boys Hostel A | 8 | Active |
| Priya Sharma | Warden | L2 | Girls Hostel B | 4 | Active |
| Amit Das | Chief Warden | L3 | All Hostels | 12 | Active |

---

# 6. Change Staff Assignment

Admin must be able to change the hostel assigned to a staff member.

Example:

```text
Staff:
Mukesh Kumar

Role:
Caretaker

Current Hostel:
Boys Hostel A

Change Assignment:
[ Girls Hostel B ▼ ]

              Cancel    Save Assignment
```

After saving:

```text
Mukesh Kumar
        ↓
Girls Hostel B
```

The new assignment should immediately be used for new Level 1 ticket routing.

---

# 7. Level 1 Hostel Responsibility

This is the main change from the previous routing design.

## Previous approach

The previous design allowed routing rules such as:

```text
Hostel + Category → Staff
```

For example:

```text
Boys Hostel A + Electrical → Mukesh Kumar
Boys Hostel A + Plumbing → Mukesh Kumar
Boys Hostel A + Cleaning → Mukesh Kumar
Boys Hostel A + Furniture → Mukesh Kumar
```

This creates unnecessary duplicate routing rules when one person is responsible for all categories.

## New approach

Use:

```text
Hostel → Level 1 Responsible Staff
```

Example:

```text
Boys Hostel A
       ↓
Mukesh Kumar
       ↓
All Categories
```

The category still exists for classification, filtering, reporting, and dashboard analytics, but it does **not** determine the Level 1 assignee.

---

# 8. Revised Hostel Responsibility Screen

Replace the existing category-based Routing Rules screen with a simpler **Hostel Responsibility** screen.

Example:

```text
Hostel Responsibility

Each hostel has one Level 1 responsible staff member.
All ticket categories for that hostel are automatically
assigned to the responsible staff member.

                                      + Assign Staff
```

Table:

| Hostel | Level 1 Responsible Staff | Status | Actions |
|---|---|---|---|
| Boys Hostel A | Mukesh Kumar (Caretaker L1) | Active | Edit |
| Girls Hostel B | Anita Devi (Caretaker L1) | Active | Edit |

There should be no repeated rows for:

- Electrical
- Plumbing
- Cleaning
- Furniture
- Internet
- Mess
- Security
- Other

---

# 9. Ticket Routing

When a hosteler creates a ticket, routing should work as follows:

```text
Hosteler
   ↓
Create Ticket
   ↓
Identify Hosteler's Hostel
   ↓
Find Hostel's Responsible Staff
   ↓
Assign Level 1 Staff
   ↓
Start Level 1 SLA
```

Example:

```text
Hosteler:
Student A

Hostel:
Boys Hostel A

Category:
Plumbing / Water

Problem:
Water leakage
```

The system automatically assigns:

```text
Assigned To:
Mukesh Kumar

Level:
L1

Hostel:
Boys Hostel A
```

The category does not change the Level 1 assignee.

---

# 10. Escalation Hierarchy

Keep the existing four-level escalation model.

```text
L1 — Hostel Responsible Staff
             ↓ SLA breached
L2 — Hostel Warden
             ↓ SLA breached
L3 — Chief Warden
             ↓ SLA breached
L4 — Admin / Dean
```

Example:

```text
Boys Hostel A
      |
      ↓
Mukesh Kumar
Caretaker — L1
      |
      | SLA breached
      ↓
Boys Hostel Warden
L2
      |
      | SLA breached
      ↓
Chief Warden
L3
      |
      | SLA breached
      ↓
Admin / Dean
L4
```

Manual escalation and reassignment should remain available according to the existing permission rules.

---

# 11. Ticket Location

Because room numbers are not maintained, tickets should store the hostel but not a room.

Use:

```text
Ticket
├── Hostel
├── Category
├── Priority
├── Title
└── Description
```

The hosteler can describe the exact physical location inside the description.

Example:

> Water leakage near the washroom on the second floor.

No dedicated room, floor, or bed fields are required.

---

# 12. Revised Data Model

## Hostel

Use:

```text
Hostel
├── id
├── name
├── code
├── gender_type
├── address
├── responsible_staff → User
├── is_active
├── created_at
└── updated_at
```

`responsible_staff` represents the primary Level 1 staff member.

## User

Keep the existing role and escalation fields:

```text
User
├── login_id
├── full_name
├── email
├── phone
├── role
├── escalation_level
├── hostel
├── avatar
└── is_active
```

For Level 1 staff, `hostel` represents the hostel they are assigned to.

---

# 13. Remove Block and Room Models

The previous structure contained:

```text
Hostel
   ↓
Block
   ↓
Room
```

Replace it with:

```text
Hostel
   ↓
Responsible Staff
```

Remove or do not implement:

- Block model
- Room model
- Block management page
- Room management page
- Room number fields
- Floor fields
- Bed capacity fields
- Total room calculations

The Admin sidebar should no longer contain:

```text
Blocks
Rooms
```

---

# 14. Revised Admin Navigation

Recommended Admin navigation:

```text
Dashboard
Tickets
Kanban

HOSTEL MANAGEMENT
├── Hostels
├── Staff
├── Hostel Responsibility
├── Categories
└── SLA Policies

Reports
Notifications
Settings
```

Alternatively, **Hostel Responsibility** can be integrated into the Staff or Hostels page if a smaller navigation is preferred.

---

# 15. Staff Assignment Rules

Implement these rules:

### Level 1

- One primary responsible staff member per hostel.
- Responsible staff handles all categories for that hostel.
- Category does not determine the assignee.

### Level 2

- Hostel Warden handles escalation for their hostel.

### Level 3

- Chief Warden handles escalations across hostels.

### Level 4

- Admin / Dean handles final escalation.

The existing SLA system continues to control automatic escalation.

---

# 16. Assignment Change Behaviour

When Admin changes the responsible staff for a hostel:

### Existing tickets

Do not automatically change the assignee of existing tickets unless explicitly reassigned.

This prevents historical/work-in-progress tickets from unexpectedly changing ownership.

### New tickets

New tickets created after the assignment change should be assigned to the new responsible staff member.

Example:

```text
Before:

Boys Hostel A
      ↓
Mukesh Kumar

New assignment:

Boys Hostel A
      ↓
Suresh Kumar
```

New tickets → Suresh Kumar.

Existing tickets → remain with their current assignee unless manually reassigned.

---

# 17. Staff Deactivation

If a staff member is deactivated:

- They cannot receive new tickets.
- Their existing tickets remain in the system.
- Admin should be warned if they still have active tickets.
- Admin should be prompted to reassign their active tickets.
- Their historical activity remains unchanged.

If the staff member is the responsible Level 1 staff for a hostel, Admin must assign another active Level 1 staff member before completing the deactivation.

---

# 18. UI Design

Maintain the existing ERPNext/Frappe-inspired design:

- Light background
- Dense tables
- Thin borders
- Small typography
- Pastel status pills
- Black primary buttons
- Inter font
- Lucide icons
- Existing design tokens
- No Bootstrap
- No Tailwind
- No React

The revised screens should remain visually consistent with the existing Hostel Management and Staff Management screens.

---

# 19. Implementation Changes

Update the project according to the following:

### Models

- Simplify `Hostel`.
- Remove Block and Room models from the active v1 design.
- Add/use `responsible_staff` on Hostel.
- Remove room/floor/capacity references from tickets and user location data.

### Routing service

Replace category-based Level 1 routing with:

```python
assign_initial(ticket)
```

Logic:

```text
1. Get ticket.hostel
2. Get hostel.responsible_staff
3. Verify staff is active
4. Assign ticket to responsible staff
5. Set current_level = 1
6. Set status = ASSIGNED
7. Calculate Level 1 SLA
8. Create activity log
9. Create notification
```

### Admin services

Provide functions for:

```text
create_hostel()
update_hostel()
change_hostel_responsible_staff()
assign_staff_to_hostel()
deactivate_staff()
deactivate_hostel()
```

Keep business logic in service modules rather than views.

---

# 20. Validation Rules

The system must prevent:

- Assigning inactive staff as responsible staff.
- Assigning a Level 2/3/4-only user as a Level 1 responsible staff member.
- Duplicate hostel codes.
- Deactivating a hostel without warning about active tickets.
- Deactivating a responsible Level 1 staff member while leaving the hostel without another responsible staff member.
- Creating a new ticket for an inactive hostel.

---

# 21. Revised Phase 3

Update Phase 3 of the original build plan.

## Phase 3: Hostels, Staff, Categories & Configuration

Build:

- Hostel model
- Hostel management page
- Add/edit hostel
- Activate/deactivate hostel
- Staff management page
- Staff assignment page
- Responsible staff assignment
- Category management
- SLA policy management
- Tags

Do **not** build:

- Block management
- Room management
- Room assignment
- Floor management
- Bed capacity management

### Done when

Admin can:

1. Create a hostel.
2. Edit a hostel.
3. Activate/deactivate a hostel.
4. View all staff.
5. View each staff member's current hostel assignment.
6. Change a staff member's hostel assignment.
7. Assign one active Level 1 staff member as the responsible staff for each hostel.
8. Configure categories and SLA policies.
9. Create tickets that can use the hostel's responsible staff for Level 1 routing.

---

# 22. Final System Structure

The revised system should conceptually be:

```text
                         ADMIN
                           |
          ┌────────────────┼────────────────┐
          ↓                ↓                ↓
       Hostels           Staff          Categories
          |                |
          ↓                ↓
 Responsible Staff    Staff Assignment
          |
          ↓
       TICKETS
          |
          ↓
       Level 1
          |
          ↓ SLA
       Level 2
          |
          ↓ SLA
       Level 3
          |
          ↓ SLA
       Level 4
```

## Core Principle

> **The hostel determines who receives a Level 1 ticket. The category only describes what the problem is.**

This is the primary routing rule for the revised Hostel Ticket System.
