from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.tickets.models import (
    ActivityAction,
    RoutingRule,
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
    """Finds the responsible staff assignee using hierarchy fallback rules."""
    # 1. Matching hostel and category rule
    rule = RoutingRule.objects.filter(
        hostel=ticket.hostel, category=ticket.category, level=1
    ).first()
    if rule and rule.assignee and rule.assignee.is_active:
        return rule.assignee

    # 2. Matching hostel rule (any category)
    rule = RoutingRule.objects.filter(hostel=ticket.hostel, category__isnull=True, level=1).first()
    if rule and rule.assignee and rule.assignee.is_active:
        return rule.assignee

    # 3. Matching category rule (any hostel)
    rule = RoutingRule.objects.filter(
        hostel__isnull=True, category=ticket.category, level=1
    ).first()
    if rule and rule.assignee and rule.assignee.is_active:
        return rule.assignee

    # 4. Caretaker in that hostel
    caretaker = User.objects.filter(
        hostel=ticket.hostel, role=Role.CARETAKER, is_active=True
    ).first()
    if caretaker:
        return caretaker

    # 5. Warden in that hostel
    warden = User.objects.filter(hostel=ticket.hostel, role=Role.WARDEN, is_active=True).first()
    if warden:
        return warden

    # 6. Global fallback: Chief Warden or Admin
    fallback = User.objects.filter(role__in=[Role.CHIEF_WARDEN, Role.ADMIN], is_active=True).first()
    return fallback


def assign_initial(ticket: Ticket, actor: User | None = None) -> Ticket:
    """Performs initial routing assignment, SLA deadline calculation, and notification."""
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
