from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.permissions import can_change_status
from apps.notifications.models import Notification
from apps.tickets.models import ActivityAction, Status, Ticket, TicketActivity

# Allowed transitions map
ALLOWED_TRANSITIONS = {
    Status.OPEN: [Status.ASSIGNED, Status.REJECTED],
    Status.ASSIGNED: [
        Status.IN_PROGRESS,
        Status.ON_HOLD,
        Status.REJECTED,
        Status.RESOLVED,
    ],
    Status.IN_PROGRESS: [Status.ON_HOLD, Status.RESOLVED, Status.CLOSED],
    Status.ON_HOLD: [Status.IN_PROGRESS, Status.RESOLVED],
    Status.RESOLVED: [Status.CLOSED, Status.IN_PROGRESS],  # In_progress on reopen
    Status.CLOSED: [Status.IN_PROGRESS],  # Reopen
    Status.REJECTED: [],
}


def change_status(ticket: Ticket, new_status: str, actor, note: str = "") -> Ticket:
    """Safely transitions ticket status, validates permission and transitions, and audits."""
    if not can_change_status(actor, ticket, new_status):
        raise ValidationError("You do not have permission to perform this status change.")

    allowed = ALLOWED_TRANSITIONS.get(ticket.status, [])
    # Allow admin / superuser overrides or standard allowed transitions
    if new_status not in allowed and not getattr(actor, "is_admin", False):
        raise ValidationError(
            f"Cannot change status from {ticket.get_status_display()} to {new_status}."
        )

    old_status = ticket.status
    ticket.status = new_status
    now = timezone.now()

    if new_status == Status.RESOLVED:
        ticket.resolved_at = now
        ticket.resolution_note = note
    elif new_status == Status.CLOSED:
        ticket.closed_at = now
    elif new_status == Status.IN_PROGRESS and old_status in [
        Status.RESOLVED,
        Status.CLOSED,
    ]:
        # Reopening ticket
        ticket.resolved_at = None
        ticket.closed_at = None

    ticket.save()

    # Log activity
    action_type = ActivityAction.STATUS_CHANGED
    if new_status == Status.CLOSED:
        action_type = ActivityAction.CLOSED
    elif new_status == Status.IN_PROGRESS and old_status in [
        Status.RESOLVED,
        Status.CLOSED,
    ]:
        action_type = ActivityAction.REOPENED
    elif new_status == Status.REJECTED:
        action_type = ActivityAction.REJECTED

    TicketActivity.objects.create(
        ticket=ticket,
        actor=actor,
        action=action_type,
        from_value=old_status,
        to_value=new_status,
        note=note or f"Status changed from {old_status} to {new_status}",
    )

    # Send notification
    recipient = ticket.assigned_to if actor == ticket.reporter else ticket.reporter
    if recipient:
        Notification.objects.create(
            recipient=recipient,
            ticket=ticket,
            verb=f"Status: {new_status}",
            message=f"Ticket {ticket.ticket_no} changed status to {new_status}.",
        )

    return ticket


def auto_close_resolved_tickets(hours_threshold: int = 72) -> int:
    """Automatically closes tickets that were marked RESOLVED more than 72h ago."""
    threshold = timezone.now() - timedelta(hours=hours_threshold)
    resolved_tickets = Ticket.objects.filter(
        status=Status.RESOLVED,
        resolved_at__lt=threshold,
    )
    count = 0
    for ticket in resolved_tickets:
        ticket.status = Status.CLOSED
        ticket.closed_at = timezone.now()
        ticket.save()

        TicketActivity.objects.create(
            ticket=ticket,
            actor=None,
            action=ActivityAction.CLOSED,
            from_value=Status.RESOLVED,
            to_value=Status.CLOSED,
            note=f"Automatically closed {hours_threshold}h after resolution",
        )
        count += 1
    return count
