from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationVerb
from apps.tickets.models import (
    ActivityAction,
    CriticalityRule,
    Priority,
    SLAPolicy,
    Status,
    Ticket,
    TicketActivity,
)

PRIORITY_ORDER = {
    Priority.LOW: 1,
    Priority.MEDIUM: 2,
    Priority.HIGH: 3,
    Priority.URGENT: 4,
}

ORDER_TO_PRIORITY = {
    1: Priority.LOW,
    2: Priority.MEDIUM,
    3: Priority.HIGH,
    4: Priority.URGENT,
}


def priority_rank(p: str) -> int:
    return PRIORITY_ORDER.get(p, 2)


def bump_priority(base_priority: str, levels: int) -> str:
    base_rank = priority_rank(base_priority)
    new_rank = min(4, base_rank + levels)
    return ORDER_TO_PRIORITY[new_rank]


def max_priority(p1: str, p2: str) -> str:
    return p1 if priority_rank(p1) >= priority_rank(p2) else p2


def get_staff_for_level(hostel, level: int):
    """Returns active staff members responsible for the given level and hostel."""
    if level == 1:
        qs = User.objects.filter(hostel=hostel, role=Role.CARETAKER, is_active=True)
        if not qs.exists() and hostel and hostel.responsible_staff and hostel.responsible_staff.is_active:
            return [hostel.responsible_staff]
        return list(qs)
    elif level == 2:
        return list(User.objects.filter(hostel=hostel, role=Role.WARDEN, is_active=True))
    elif level == 3:
        return list(User.objects.filter(role=Role.CHIEF_WARDEN, is_active=True))
    elif level == 4:
        return list(User.objects.filter(role=Role.ADMIN, is_active=True))
    return list(User.objects.filter(role=Role.ADMIN, is_active=True))


def recompute_criticality(ticket: Ticket) -> Ticket:
    """
    Recomputes effective priority and SLA deadline based on repost count and CriticalityRules.
    Idempotent. Only this function should write Ticket.priority.
    """
    # 1. Find highest matching rule
    rule = (
        CriticalityRule.objects.filter(min_reposts__lte=ticket.repost_count)
        .order_by("-min_reposts")
        .first()
    )

    base = ticket.base_priority or Priority.MEDIUM
    auto = base

    if rule:
        if rule.force_priority:
            auto = rule.force_priority
        else:
            auto = bump_priority(base, rule.bump_levels)

    new_priority = max_priority(base, auto)
    old_priority = ticket.priority
    fields_to_save = []

    # 2. Priority change & SLA deadline update
    if new_priority != old_priority:
        ticket.priority = new_priority
        fields_to_save.append("priority")

        # Recompute due_at from level_started_at if present
        start_time = ticket.level_started_at or ticket.created_at or timezone.now()
        from apps.tickets.services.sla import hours_for
        hours = hours_for(new_priority, ticket.current_level)
        ticket.due_at = start_time + timedelta(hours=hours)
        if ticket.status in [
            Status.OPEN,
            Status.ASSIGNED,
            Status.IN_PROGRESS,
            Status.ON_HOLD,
        ]:
            ticket.is_overdue = timezone.now() > ticket.due_at
        fields_to_save.extend(["due_at", "is_overdue"])

        # Log activity
        if priority_rank(new_priority) > priority_rank(old_priority):
            action = ActivityAction.PRIORITY_AUTO_RAISED
            note = (
                f"Priority automatically raised from {old_priority} to {new_priority} "
                f"({ticket.repost_count} reposts)"
            )
        else:
            action = ActivityAction.STATUS_CHANGED
            note = (
                f"Priority automatically adjusted from {old_priority} to {new_priority} "
                f"({ticket.repost_count} reposts)"
            )

        TicketActivity.objects.create(
            ticket=ticket,
            actor=None,
            action=action,
            from_value=old_priority,
            to_value=new_priority,
            note=note,
        )

        # Notify reporter, assignee, and reposters
        recipients = set()
        if ticket.reporter:
            recipients.add(ticket.reporter)
        if ticket.assigned_to:
            recipients.add(ticket.assigned_to)
        reposter_users = User.objects.filter(ticket_reposts__ticket=ticket)
        for u in reposter_users:
            recipients.add(u)

        notif_msg = (
            f"Priority for ticket {ticket.ticket_no} ({ticket.title}) was automatically "
            f"updated to {new_priority} ({ticket.affected_count} affected)."
        )
        notifications = [
            Notification(
                recipient=user,
                ticket=ticket,
                verb=NotificationVerb.PRIORITY_RAISED,
                message=notif_msg,
            )
            for user in recipients
        ]
        Notification.objects.bulk_create(notifications)

    # 3. Critical threshold crossed notification
    if rule and rule.min_reposts > ticket.last_notified_threshold:
        ticket.last_notified_threshold = rule.min_reposts
        fields_to_save.append("last_notified_threshold")

        if rule.notify_level:
            staff_to_notify = get_staff_for_level(ticket.hostel, rule.notify_level)
            crit_msg = (
                f"Critical issue: {ticket.affected_count} hostelers affected on "
                f"{ticket.ticket_no} ({ticket.title})."
            )
            staff_notifs = [
                Notification(
                    recipient=staff_user,
                    ticket=ticket,
                    verb=NotificationVerb.CRITICAL_ISSUE,
                    message=crit_msg,
                )
                for staff_user in staff_to_notify
            ]
            Notification.objects.bulk_create(staff_notifs)

    if fields_to_save:
        ticket.save(update_fields=fields_to_save)

    return ticket
