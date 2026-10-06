from apps.accounts.models import Role


def can_raise_ticket(user):
    """Hostelers and Admins can raise tickets."""
    if not user.is_authenticated:
        return False
    return user.role in [Role.HOSTELER, Role.ADMIN]


def can_view_kanban(user):
    """Staff members can view Kanban board; hostelers cannot."""
    if not user.is_authenticated:
        return False
    return user.role in [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]


def can_manage_config(user):
    """Only Admins can manage hostels, rooms, categories, routing, SLA."""
    if not user.is_authenticated:
        return False
    return user.role == Role.ADMIN or user.is_superuser


def can_add_internal_note(user):
    """Only staff members can add internal notes."""
    if not user.is_authenticated:
        return False
    return user.is_staff_member


def can_view_ticket(user, ticket):
    """Check if a user has permission to view a specific ticket."""
    if not user.is_authenticated:
        return False

    if user.is_admin or user.is_chief_warden:
        return True

    if user.is_warden:
        return ticket.hostel == user.hostel

    if user.is_caretaker:
        # Caretaker can view if assigned to them or in their hostel
        return ticket.assigned_to_id == user.id or ticket.hostel == user.hostel

    if user.is_hosteler:
        return ticket.reporter_id == user.id

    return False


def can_change_status(user, ticket, new_status):
    """Check if user can transition ticket to new_status."""
    if not user.is_authenticated:
        return False

    # Hosteler can only close or reopen their own tickets
    if user.is_hosteler:
        if ticket.reporter_id != user.id:
            return False
        return new_status in ["CLOSED", "IN_PROGRESS"]

    # Staff can update status if they can view the ticket
    return can_view_ticket(user, ticket)


def can_reassign_or_escalate(user, ticket):
    """Caretaker can escalate up; Warden, Chief Warden, Admin can reassign/escalate."""
    if not user.is_authenticated:
        return False
    if user.is_hosteler:
        return False
    return can_view_ticket(user, ticket)
