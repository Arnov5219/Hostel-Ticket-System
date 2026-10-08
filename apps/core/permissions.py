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


def can_view_community_feed(user):
    """Hostelers, Caretakers, Wardens, Chief Wardens, and Admins can view feed within scope."""
    if not user.is_authenticated:
        return False
    return True


def can_repost_ticket(user, ticket):
    """Only hostelers in the same hostel can repost active community tickets (not their own)."""
    if not user.is_authenticated or not user.is_hosteler:
        return False
    if ticket.reporter_id == user.id:
        return False
    if ticket.hostel_id != getattr(user.hostel, "id", None):
        return False
    if ticket.visibility != "HOSTEL" or ticket.community_hidden:
        return False
    return ticket.status in ["OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD"]


def can_comment_publicly(user, ticket):
    """Hostelers in same hostel or authorized staff can comment on community tickets."""
    if not user.is_authenticated:
        return False
    if ticket.visibility != "HOSTEL":
        return False
    if user.is_hosteler:
        return ticket.hostel_id == getattr(user.hostel, "id", None)
    return can_view_ticket(user, ticket)


def can_moderate_community(user):
    """Warden, Chief Warden, and Admin can moderate comments and posts."""
    if not user.is_authenticated:
        return False
    return user.role in [Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]


def can_view_reposters_and_notes(user, ticket):
    """Staff only can view reposter list and private notes."""
    if not user.is_authenticated or user.is_hosteler:
        return False
    return can_view_ticket(user, ticket)


def can_publish_announcements(user, targeted_hostels=None):
    """
    Warden can publish only to own hostel.
    Chief Warden and Admin can publish to any or all hostels.
    """
    if not user.is_authenticated:
        return False
    if user.role in [Role.ADMIN, Role.CHIEF_WARDEN]:
        return True
    if user.role == Role.WARDEN:
        if not user.hostel:
            return False
        if targeted_hostels is not None:
            # All targeted hostels must match warden's hostel
            for h in targeted_hostels:
                h_id = h.id if hasattr(h, "id") else h
                if h_id != user.hostel_id:
                    return False
        return True
    return False


def can_edit_criticality_rules(user):
    """Only Admin can edit criticality thresholds."""
    if not user.is_authenticated:
        return False
    return user.role == Role.ADMIN or user.is_superuser
