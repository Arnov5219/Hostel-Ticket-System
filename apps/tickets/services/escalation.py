from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.services import notify_ticket_escalated
from apps.tickets.models import (
    ActivityAction,
    Status,
    Ticket,
    TicketActivity,
)
from apps.tickets.services.sla import hours_for


def find_escalation_assignee(ticket: Ticket, next_level: int) -> tuple[User | None, bool]:
    """
    Finds next-level assignee in the hierarchy, skipping inactive or archived staff.
    Returns (assignee, is_admin_fallback).
    """
    active_staff_qs = User.objects.filter(is_active=True, archived_at__isnull=True)

    if next_level == 2:
        # 1. Primary Level 2 Warden configured on the hostel
        if (
            ticket.hostel
            and ticket.hostel.responsible_warden
            and ticket.hostel.responsible_warden.is_active
            and not getattr(ticket.hostel.responsible_warden, "archived_at", None)
        ):
            return ticket.hostel.responsible_warden, False
        # 2. Hostel Warden assigned to the same hostel
        warden = active_staff_qs.filter(hostel=ticket.hostel, role=Role.WARDEN).first()
        if warden:
            return warden, False
    elif next_level == 3:
        # Chief Warden across all hostels
        cw = active_staff_qs.filter(role=Role.CHIEF_WARDEN).first()
        if cw:
            return cw, False
    elif next_level == 4:
        # Dean (final escalation)
        dean = active_staff_qs.filter(role=Role.DEAN).first()
        if dean:
            return dean, False
        # Fallback to active Admin when no active Dean exists (A5)
        admin_user = active_staff_qs.filter(role=Role.ADMIN).first()
        if admin_user:
            return admin_user, True

    # Fallback to any user at that level or admin
    fallback = active_staff_qs.filter(escalation_level=next_level).first()
    if fallback:
        return fallback, False
    if next_level == 4:
        admin_user = active_staff_qs.filter(role=Role.ADMIN).first()
        if admin_user:
            return admin_user, True

    return None, False


def escalate(ticket: Ticket, actor=None, reason: str = "") -> Ticket:
    """Escalates ticket to the next tier up, updates SLA deadline, and notifies."""
    if ticket.current_level >= 4:
        ticket.is_overdue = True
        ticket.save()
        return ticket

    next_level = ticket.current_level + 1
    new_assignee, is_fallback = find_escalation_assignee(ticket, next_level)
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

    if is_fallback:
        TicketActivity.objects.create(
            ticket=ticket,
            actor=actor,
            action=ActivityAction.LEVEL4_FALLBACK,
            from_value="No active Dean",
            to_value=new_assignee.login_id if new_assignee else "None",
            note="No active Dean found; ticket escalated to Admin as fallback.",
        )

    # Notifications via centralized service
    notify_ticket_escalated(ticket, old_assignee, new_assignee, next_level, actor=actor)

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
