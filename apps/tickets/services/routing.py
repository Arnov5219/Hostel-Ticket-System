from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.tickets.models import (
    ActivityAction,
    SLAPolicy,
    Status,
    Ticket,
    TicketActivity,
)


def calculate_due_date(priority: str, level: int) -> timezone.datetime:
    """Calculates due date based on priority and escalation level SLA policy."""
    policy = SLAPolicy.objects.filter(priority=priority, level=level).first()
    hours = policy.hours if policy else 24
    return timezone.now() + timedelta(hours=hours)


def find_initial_assignee(ticket: Ticket) -> User | None:
    """
    Finds the responsible Level 1 staff assignee for the ticket.
    Rule: The hostel determines who receives a Level 1 ticket.
    The category only describes what the problem is.
    """
    if not ticket.hostel:
        return User.objects.filter(role__in=[Role.CHIEF_WARDEN, Role.ADMIN], is_active=True).first()

    # 1. Primary Level 1 staff member configured on the hostel
    if ticket.hostel.responsible_staff and ticket.hostel.responsible_staff.is_active:
        return ticket.hostel.responsible_staff

    # 2. Caretaker assigned to that hostel
    caretaker = User.objects.filter(
        hostel=ticket.hostel, role=Role.CARETAKER, is_active=True
    ).first()
    if caretaker:
        return caretaker

    # 3. Warden in that hostel
    warden = User.objects.filter(hostel=ticket.hostel, role=Role.WARDEN, is_active=True).first()
    if warden:
        return warden

    # 4. Global fallback: Chief Warden or Admin
    fallback = User.objects.filter(role__in=[Role.CHIEF_WARDEN, Role.ADMIN], is_active=True).first()
    return fallback


def assign_initial(ticket: Ticket, actor: User | None = None) -> Ticket:
    """Performs initial routing assignment, SLA deadline calculation, and notification."""
    if ticket.hostel and not ticket.hostel.is_active:
        raise ValidationError("Cannot assign ticket for an inactive hostel.")

    assignee = find_initial_assignee(ticket)

    ticket.assigned_to = assignee
    ticket.current_level = 1
    ticket.status = Status.ASSIGNED if assignee else Status.OPEN
    ticket.due_at = calculate_due_date(ticket.priority, level=1)
    ticket.is_overdue = False
    ticket.save()

    # Log ASSIGNED activity
    assignee_name = assignee.full_name or assignee.login_id if assignee else "Unassigned"
    TicketActivity.objects.create(
        ticket=ticket,
        actor=actor,
        action=ActivityAction.ASSIGNED,
        from_value="Unassigned",
        to_value=assignee_name,
        note=f"Automatically routed to Level 1 ({assignee_name})",
    )

    # In-app notification for the assignee
    if assignee:
        Notification.objects.create(
            recipient=assignee,
            ticket=ticket,
            verb="New Ticket Assigned",
            message=f"Ticket {ticket.ticket_no} ({ticket.title}) has been assigned to you.",
        )

    return ticket
