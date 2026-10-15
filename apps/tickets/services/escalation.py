from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.tickets.models import (
    ActivityAction,
    Status,
    Ticket,
    TicketActivity,
)
from apps.tickets.services.sla import hours_for


def find_escalation_assignee(ticket: Ticket, next_level: int) -> User | None:
    """Finds next-level assignee in the hierarchy, skipping inactive or archived staff."""
    active_staff_qs = User.objects.filter(is_active=True, archived_at__isnull=True)

    if next_level == 2:
        # Hostel Warden for the same hostel
        warden = active_staff_qs.filter(hostel=ticket.hostel, role=Role.WARDEN).first()
        if warden:
            return warden
    elif next_level == 3:
        # Chief Warden across all hostels
        cw = active_staff_qs.filter(role=Role.CHIEF_WARDEN).first()
        if cw:
            return cw
    elif next_level == 4:
        # Admin / Dean
        admin_user = active_staff_qs.filter(role=Role.ADMIN).first()
        if admin_user:
            return admin_user

    # Fallback to any user at that level or admin
    return (
        active_staff_qs.filter(escalation_level=next_level).first()
        or active_staff_qs.filter(role=Role.ADMIN).first()
    )


def escalate(ticket: Ticket, actor=None, reason: str = "") -> Ticket:
    """Escalates ticket to the next tier up, updates SLA deadline, and notifies."""
    if ticket.current_level >= 4:
        ticket.is_overdue = True
        ticket.save()
        return ticket

    next_level = ticket.current_level + 1
    new_assignee = find_escalation_assignee(ticket, next_level)
    old_assignee = ticket.assigned_to

    # Compute new due date from SLA policy or fallback
    hours = hours_for(ticket.priority, next_level)

    now = timezone.now()
    ticket.current_level = next_level
    ticket.level_started_at = now
    ticket.last_activity_at = now
    if new_assignee:
        ticket.assigned_to = new_assignee
    ticket.due_at = now + timedelta(hours=hours)
    ticket.is_overdue = False
    ticket.save()

    actor_label = actor.login_id if actor else "Automated SLA Timer"
    note_msg = (
        f"Escalated from L{next_level - 1} to L{next_level} by {actor_label}. {reason}".strip()
    )

    TicketActivity.objects.create(
        ticket=ticket,
        actor=actor,
        action=ActivityAction.ESCALATED,
        from_value=f"L{next_level - 1}",
        to_value=f"L{next_level}",
        note=note_msg,
    )

    # Notify new assignee
    if new_assignee:
        Notification.objects.create(
            recipient=new_assignee,
            ticket=ticket,
            verb=f"Escalated to Level {next_level}",
            message=f"Ticket {ticket.ticket_no} has escalated to you: {ticket.title}.",
        )

    # Notify old assignee
    if old_assignee and old_assignee != new_assignee:
        Notification.objects.create(
            recipient=old_assignee,
            ticket=ticket,
            verb="Ticket Escalated",
            message=f"Ticket {ticket.ticket_no} has been escalated to L{next_level}.",
        )

    # Notify reporter
    if ticket.reporter:
        Notification.objects.create(
            recipient=ticket.reporter,
            ticket=ticket,
            verb="Ticket Escalated",
            message=f"Your ticket {ticket.ticket_no} was escalated to Level {next_level} ({new_assignee.get_role_display() if new_assignee else 'Higher Authority'}).",
        )

    return ticket


def check_overdue() -> int:
    """Checks all active tickets and escalates breached SLAs or flags Critical Overdue."""
    now = timezone.now()
    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    overdue_tickets = Ticket.objects.filter(status__in=active_statuses, due_at__lt=now)

    count = 0
    for ticket in overdue_tickets:
        if ticket.current_level < 4:
            escalate(ticket, actor=None, reason="Automated escalation due to SLA deadline breach.")
            count += 1
        else:
            if not ticket.is_overdue:
                ticket.is_overdue = True
                ticket.save()
                count += 1
    return count
