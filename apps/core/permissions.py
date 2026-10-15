from enum import StrEnum
from functools import wraps

from django.core.exceptions import PermissionDenied

from apps.accounts.models import Role


class Capability(StrEnum):
    RAISE_TICKET = "RAISE_TICKET"
    VIEW_ASSIGNED_TICKETS = "VIEW_ASSIGNED_TICKETS"
    VIEW_HOSTEL_TICKETS = "VIEW_HOSTEL_TICKETS"
    VIEW_ALL_TICKETS = "VIEW_ALL_TICKETS"
    CHANGE_STATUS = "CHANGE_STATUS"
    ESCALATE = "ESCALATE"
    REASSIGN_TICKET = "REASSIGN_TICKET"
    DELETE_TICKET = "DELETE_TICKET"
    RESTORE_TICKET = "RESTORE_TICKET"
    VIEW_TRASH_ALL = "VIEW_TRASH_ALL"
    VIEW_TRASH_HOSTEL = "VIEW_TRASH_HOSTEL"
    PUBLISH_ANNOUNCEMENT = "PUBLISH_ANNOUNCEMENT"
    MANAGE_STAFF = "MANAGE_STAFF"
    MANAGE_HOSTELS = "MANAGE_HOSTELS"
    MANAGE_RESPONSIBILITY = "MANAGE_RESPONSIBILITY"
    MANAGE_TICKET_SETTINGS = "MANAGE_TICKET_SETTINGS"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"
    VIEW_STAFF_HEALTH = "VIEW_STAFF_HEALTH"
    VIEW_CAMPUS_ANALYTICS = "VIEW_CAMPUS_ANALYTICS"
    VIEW_KANBAN = "VIEW_KANBAN"
    ADD_INTERNAL_NOTE = "ADD_INTERNAL_NOTE"
    EXPORT_CSV = "EXPORT_CSV"


# Single frozen set for admin-only controls (Section 3.2)
ADMIN_ONLY_CAPABILITIES = frozenset({
    Capability.MANAGE_STAFF,
    Capability.MANAGE_HOSTELS,
    Capability.MANAGE_RESPONSIBILITY,
    Capability.MANAGE_TICKET_SETTINGS,
    Capability.RESTORE_TICKET,
    Capability.VIEW_TRASH_ALL,
    Capability.VIEW_AUDIT_LOG,
})

# Admin: system role (accounts, hostels, settings, data hygiene). Not a ticket handler.
ADMIN_CAPABILITIES = frozenset({
    Capability.RAISE_TICKET,
    Capability.VIEW_ASSIGNED_TICKETS,
    Capability.VIEW_HOSTEL_TICKETS,
    Capability.VIEW_ALL_TICKETS,
    Capability.REASSIGN_TICKET,
    Capability.DELETE_TICKET,
    Capability.RESTORE_TICKET,
    Capability.VIEW_TRASH_ALL,
    Capability.PUBLISH_ANNOUNCEMENT,
    Capability.VIEW_CAMPUS_ANALYTICS,
    Capability.EXPORT_CSV,
    Capability.MANAGE_STAFF,
    Capability.MANAGE_HOSTELS,
    Capability.MANAGE_RESPONSIBILITY,
    Capability.MANAGE_TICKET_SETTINGS,
    Capability.VIEW_AUDIT_LOG,
    Capability.VIEW_STAFF_HEALTH,
})

# Dean: Level 4 final escalation and campus authority (no admin controls, no escalate up)
DEAN_CAPABILITIES = frozenset({
    Capability.VIEW_ASSIGNED_TICKETS,
    Capability.VIEW_HOSTEL_TICKETS,
    Capability.VIEW_ALL_TICKETS,
    Capability.CHANGE_STATUS,
    Capability.REASSIGN_TICKET,
    Capability.DELETE_TICKET,
    Capability.PUBLISH_ANNOUNCEMENT,
    Capability.VIEW_CAMPUS_ANALYTICS,
    Capability.EXPORT_CSV,
    Capability.VIEW_KANBAN,
    Capability.ADD_INTERNAL_NOTE,
})

# Chief Warden: Level 3 campus oversight (no admin controls)
CHIEF_WARDEN_CAPABILITIES = frozenset({
    Capability.VIEW_ASSIGNED_TICKETS,
    Capability.VIEW_HOSTEL_TICKETS,
    Capability.VIEW_ALL_TICKETS,
    Capability.CHANGE_STATUS,
    Capability.ESCALATE,
    Capability.REASSIGN_TICKET,
    Capability.DELETE_TICKET,
    Capability.PUBLISH_ANNOUNCEMENT,
    Capability.VIEW_CAMPUS_ANALYTICS,
    Capability.EXPORT_CSV,
    Capability.VIEW_KANBAN,
    Capability.ADD_INTERNAL_NOTE,
})

# Warden: Level 2 hostel accountability
WARDEN_CAPABILITIES = frozenset({
    Capability.VIEW_ASSIGNED_TICKETS,
    Capability.VIEW_HOSTEL_TICKETS,
    Capability.CHANGE_STATUS,
    Capability.ESCALATE,
    Capability.REASSIGN_TICKET,
    Capability.DELETE_TICKET,
    Capability.PUBLISH_ANNOUNCEMENT,
    Capability.EXPORT_CSV,
    Capability.VIEW_KANBAN,
    Capability.ADD_INTERNAL_NOTE,
})

# Caretaker: Level 1 frontline maintenance
CARETAKER_CAPABILITIES = frozenset({
    Capability.VIEW_ASSIGNED_TICKETS,
    Capability.CHANGE_STATUS,
    Capability.ESCALATE,
    Capability.VIEW_KANBAN,
    Capability.ADD_INTERNAL_NOTE,
})

# Hosteler: Resident
HOSTELER_CAPABILITIES = frozenset({
    Capability.RAISE_TICKET,
    Capability.CHANGE_STATUS,
    Capability.DELETE_TICKET,
})

ROLE_CAPABILITIES = {
    Role.ADMIN: ADMIN_CAPABILITIES,
    Role.DEAN: DEAN_CAPABILITIES,
    Role.CHIEF_WARDEN: CHIEF_WARDEN_CAPABILITIES,
    Role.WARDEN: WARDEN_CAPABILITIES,
    Role.CARETAKER: CARETAKER_CAPABILITIES,
    Role.HOSTELER: HOSTELER_CAPABILITIES,
}


def has_capability(user, capability: Capability | str) -> bool:
    """Check if user has given capability."""
    if not user or not user.is_authenticated or not getattr(user, "is_active", False):
        return False

    user_role = getattr(user, "role", None)
    caps = ROLE_CAPABILITIES.get(user_role, frozenset())

    # Admin role explicitly does not have ticket handler capabilities (status change, escalate, kanban)
    if user_role == Role.ADMIN:
        return capability in caps

    if user.is_superuser:
        return True

    return capability in caps


def can_manage_user(actor, target=None) -> bool:
    """
    Safety policy: determine whether actor may manage target staff user.
    Admin only has MANAGE_STAFF capability.
    Chief Warden and Dean do NOT get staff management controls.
    Nobody can manage/delete themselves, nor deactivate the last active Admin.
    """
    if not actor or not actor.is_authenticated or not getattr(actor, "is_active", False):
        return False
    if not has_capability(actor, Capability.MANAGE_STAFF):
        return False
    if target is None:
        return True  # Creating a new staff account

    # Cannot manage hostelers via staff management
    if getattr(target, "role", None) == Role.HOSTELER:
        return False

    # Never self-manage (deactivate/delete/reset oneself)
    if actor.id == target.id:
        return False

    return True


# Helper functions driven by capabilities for backwards compatibility
def can_raise_ticket(user):
    return has_capability(user, Capability.RAISE_TICKET)


def can_view_kanban(user):
    return has_capability(user, Capability.VIEW_KANBAN)


def can_manage_config(user):
    return has_capability(user, Capability.MANAGE_HOSTELS)


def can_add_internal_note(user):
    return has_capability(user, Capability.ADD_INTERNAL_NOTE)


def can_view_ticket(user, ticket):
    """Check if user has permission to view ticket."""
    if not user.is_authenticated:
        return False

    if has_capability(user, Capability.VIEW_ALL_TICKETS):
        return True

    if has_capability(user, Capability.VIEW_HOSTEL_TICKETS):
        return ticket.hostel_id == getattr(user, "hostel_id", None)

    if has_capability(user, Capability.VIEW_ASSIGNED_TICKETS):
        return ticket.assigned_to_id == user.id or ticket.hostel_id == getattr(user, "hostel_id", None)

    if getattr(user, "role", None) == Role.HOSTELER:
        return ticket.reporter_id == user.id

    return False


def can_change_status(user, ticket, new_status):
    """Check if user can transition ticket to new_status."""
    if not user.is_authenticated:
        return False

    if getattr(user, "role", None) == Role.HOSTELER:
        if ticket.reporter_id != user.id:
            return False
        return new_status in ["CLOSED", "IN_PROGRESS"]

    return can_view_ticket(user, ticket) and has_capability(user, Capability.CHANGE_STATUS)


def can_reassign_or_escalate(user, ticket):
    """Staff can escalate or reassign if they have capability and view access."""
    if not user.is_authenticated or getattr(user, "role", None) == Role.HOSTELER:
        return False
    return can_view_ticket(user, ticket) and (
        has_capability(user, Capability.REASSIGN_TICKET) or has_capability(user, Capability.ESCALATE)
    )


def can_publish_announcements(user, targeted_hostels=None):
    """
    Warden can publish only to own hostel.
    Chief Warden and Admin can publish to any/all hostels.
    """
    if not user.is_authenticated or not has_capability(user, Capability.PUBLISH_ANNOUNCEMENT):
        return False

    if getattr(user, "role", None) == Role.WARDEN:
        if not getattr(user, "hostel_id", None):
            return False
        if targeted_hostels is not None:
            for h in targeted_hostels:
                h_id = h.id if hasattr(h, "id") else h
                if h_id != user.hostel_id:
                    return False
        return True

    return True


def can_verify_residents(user):
    return False


def require_capability(capability: Capability | str):
    """Decorator requiring specific capability."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if not has_capability(request.user, capability):
                raise PermissionDenied(f"Permission denied: missing {capability} capability.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
