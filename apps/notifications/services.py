"""
Centralized notification service layer for HostelFlow.

All notification creation logic lives here. Ticket services, announcement
services, and views call these helpers instead of creating Notification
objects directly.
"""

from apps.accounts.models import Role, User
from apps.notifications.models import (
    Notification,
    NotificationType,
    NotificationVerb,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ticket_event_key(verb, ticket_id, recipient_id, extra=""):
    """Builds a deterministic idempotency key for ticket notifications."""
    base = f"ticket_{verb}_{ticket_id}_{recipient_id}"
    if extra:
        base += f"_{extra}"
    return base


def _announcement_event_key(verb, announcement_id, recipient_id, extra=""):
    """Builds a deterministic idempotency key for announcement notifications."""
    base = f"ann_{verb}_{announcement_id}_{recipient_id}"
    if extra:
        base += f"_{extra}"
    return base


def _safe_name(user):
    """Returns a display name for a user, or 'Unknown' if None."""
    if not user:
        return "Unknown"
    return user.full_name or user.login_id


# ---------------------------------------------------------------------------
# Ticket notification helpers
# ---------------------------------------------------------------------------

def notify_ticket_created(ticket, actor=None):
    """Notify the reporter that their ticket was created and routed."""
    if not ticket.reporter:
        return
    assignee_name = _safe_name(ticket.assigned_to) if ticket.assigned_to else "staff"
    Notification.create_once(
        event_key=_ticket_event_key(NotificationVerb.CREATED, ticket.id, ticket.reporter_id),
        recipient=ticket.reporter,
        ticket=ticket,
        verb=NotificationVerb.CREATED,
        title="Ticket Created",
        notification_type=NotificationType.TICKET,
        message=f"Your ticket {ticket.ticket_no} ({ticket.title}) has been created and assigned to {assignee_name}.",
    )


def notify_ticket_assigned(ticket, assignee, actor=None):
    """Notify the assignee that a ticket has been assigned to them."""
    if not assignee:
        return
    actor_name = _safe_name(actor) if actor else "System"
    Notification.create_once(
        event_key=_ticket_event_key(NotificationVerb.ASSIGNED, ticket.id, assignee.id),
        recipient=assignee,
        ticket=ticket,
        verb=NotificationVerb.ASSIGNED,
        title="New Ticket Assigned",
        notification_type=NotificationType.TICKET,
        message=f"Ticket {ticket.ticket_no} ({ticket.title}) has been assigned to you.",
    )


def notify_ticket_status_changed(ticket, old_status, new_status, actor):
    """
    Notify the appropriate parties about a generic status change.
    - If actor is staff -> notify reporter
    - If actor is reporter -> notify assignee
    """
    recipients = set()
    if ticket.reporter and ticket.reporter != actor:
        recipients.add(ticket.reporter)
    if ticket.assigned_to and ticket.assigned_to != actor:
        recipients.add(ticket.assigned_to)

    for recipient in recipients:
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.STATUS_CHANGED, ticket.id, recipient.id,
                extra=f"{old_status}_{new_status}",
            ),
            recipient=recipient,
            ticket=ticket,
            verb=NotificationVerb.STATUS_CHANGED,
            title=f"Ticket Status: {new_status}",
            notification_type=NotificationType.TICKET,
            message=f"Ticket {ticket.ticket_no} status changed from {old_status} to {new_status} by {_safe_name(actor)}.",
        )


def notify_ticket_resolved(ticket, actor):
    """Notify the reporter that their ticket has been resolved."""
    if not ticket.reporter or ticket.reporter == actor:
        return
    Notification.create_once(
        event_key=_ticket_event_key(NotificationVerb.RESOLVED, ticket.id, ticket.reporter_id),
        recipient=ticket.reporter,
        ticket=ticket,
        verb=NotificationVerb.RESOLVED,
        title="Ticket Resolved",
        notification_type=NotificationType.TICKET,
        message=f"Your ticket {ticket.ticket_no} ({ticket.title}) has been resolved by {_safe_name(actor)}.",
    )


def notify_ticket_closed(ticket, actor):
    """Notify the reporter that their ticket has been closed."""
    if not ticket.reporter or ticket.reporter == actor:
        return
    Notification.create_once(
        event_key=_ticket_event_key(NotificationVerb.CLOSED, ticket.id, ticket.reporter_id),
        recipient=ticket.reporter,
        ticket=ticket,
        verb=NotificationVerb.CLOSED,
        title="Ticket Closed",
        notification_type=NotificationType.TICKET,
        message=f"Your ticket {ticket.ticket_no} has been closed by {_safe_name(actor)}.",
    )


def notify_ticket_reopened(ticket, actor):
    """Notify the current assignee that a ticket has been reopened."""
    recipients = set()
    if ticket.assigned_to and ticket.assigned_to != actor:
        recipients.add(ticket.assigned_to)
    if ticket.reporter and ticket.reporter != actor:
        recipients.add(ticket.reporter)

    for recipient in recipients:
        Notification.create_once(
            event_key=_ticket_event_key(NotificationVerb.REOPENED, ticket.id, recipient.id),
            recipient=recipient,
            ticket=ticket,
            verb=NotificationVerb.REOPENED,
            title="Ticket Reopened",
            notification_type=NotificationType.TICKET,
            message=f"Ticket {ticket.ticket_no} ({ticket.title}) has been reopened by {_safe_name(actor)}.",
        )


def notify_ticket_escalated(ticket, old_assignee, new_assignee, new_level, actor=None):
    """Notify all relevant parties about a ticket escalation."""
    actor_label = _safe_name(actor) if actor else "Automated SLA Timer"
    recipients_seen = set()

    # Notify new assignee
    if new_assignee:
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.ESCALATED, ticket.id, new_assignee.id,
                extra=f"L{new_level}",
            ),
            recipient=new_assignee,
            ticket=ticket,
            verb=NotificationVerb.ESCALATED,
            title=f"Escalated to Level {new_level}",
            notification_type=NotificationType.TICKET,
            message=f"Ticket {ticket.ticket_no} ({ticket.title}) has been escalated to you at Level {new_level}.",
        )
        recipients_seen.add(new_assignee.id)

    # Notify old assignee
    if old_assignee and old_assignee.id not in recipients_seen:
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.ESCALATED, ticket.id, old_assignee.id,
                extra=f"L{new_level}_old",
            ),
            recipient=old_assignee,
            ticket=ticket,
            verb=NotificationVerb.ESCALATED,
            title="Ticket Escalated",
            notification_type=NotificationType.TICKET,
            message=f"Ticket {ticket.ticket_no} has been escalated from your queue to Level {new_level}.",
        )
        recipients_seen.add(old_assignee.id)

    # Notify reporter
    if ticket.reporter and ticket.reporter_id not in recipients_seen:
        new_role = new_assignee.get_role_display() if new_assignee else "Higher Authority"
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.ESCALATED, ticket.id, ticket.reporter_id,
                extra=f"L{new_level}_reporter",
            ),
            recipient=ticket.reporter,
            ticket=ticket,
            verb=NotificationVerb.ESCALATED,
            title="Ticket Escalated",
            notification_type=NotificationType.TICKET,
            message=f"Your ticket {ticket.ticket_no} was escalated to Level {new_level} ({new_role}).",
        )


def notify_ticket_reassigned(ticket, old_assignee, new_assignee, actor):
    """Notify all relevant parties about a ticket reassignment."""
    actor_name = _safe_name(actor)
    recipients_seen = set()

    # Notify new assignee
    if new_assignee:
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.REASSIGNED, ticket.id, new_assignee.id,
                extra=f"to_{new_assignee.id}",
            ),
            recipient=new_assignee,
            ticket=ticket,
            verb=NotificationVerb.REASSIGNED,
            title="Ticket Reassigned to You",
            notification_type=NotificationType.TICKET,
            message=f"Ticket {ticket.ticket_no} ({ticket.title}) has been reassigned to you by {actor_name}.",
        )
        recipients_seen.add(new_assignee.id)

    # Notify old assignee
    if old_assignee and old_assignee.id not in recipients_seen:
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.REASSIGNED, ticket.id, old_assignee.id,
                extra=f"from_{old_assignee.id}",
            ),
            recipient=old_assignee,
            ticket=ticket,
            verb=NotificationVerb.REASSIGNED,
            title="Ticket Reassigned",
            notification_type=NotificationType.TICKET,
            message=f"Ticket {ticket.ticket_no} has been reassigned from you to {_safe_name(new_assignee)} by {actor_name}.",
        )
        recipients_seen.add(old_assignee.id)

    # Notify reporter
    if ticket.reporter and ticket.reporter_id not in recipients_seen:
        Notification.create_once(
            event_key=_ticket_event_key(
                NotificationVerb.REASSIGNED, ticket.id, ticket.reporter_id,
                extra=f"reporter_{new_assignee.id if new_assignee else 'none'}",
            ),
            recipient=ticket.reporter,
            ticket=ticket,
            verb=NotificationVerb.REASSIGNED,
            title="Ticket Reassigned",
            notification_type=NotificationType.TICKET,
            message=f"Your ticket {ticket.ticket_no} has been reassigned to {_safe_name(new_assignee)}.",
        )


def notify_urgent_ticket(ticket):
    """Send urgent attention notifications for high-priority tickets."""
    recipients = set()

    # Assignee always gets notified
    if ticket.assigned_to:
        recipients.add(ticket.assigned_to)

    # Hostel warden if different from assignee
    if ticket.hostel:
        warden = User.objects.filter(
            hostel=ticket.hostel, role=Role.WARDEN, is_active=True
        ).first()
        if warden:
            recipients.add(warden)

    for recipient in recipients:
        Notification.create_once(
            event_key=_ticket_event_key("URGENT", ticket.id, recipient.id),
            recipient=recipient,
            ticket=ticket,
            verb=NotificationVerb.ESCALATED,
            title="Urgent Ticket Requires Attention",
            notification_type=NotificationType.TICKET,
            message=f"URGENT: Ticket {ticket.ticket_no} ({ticket.title}) requires immediate attention.",
        )


# ---------------------------------------------------------------------------
# Announcement notification helpers
# ---------------------------------------------------------------------------

def notify_announcement_published(announcement, audience_user_ids):
    """
    Bulk-create notifications for announcement publication.
    Also notifies hostel staff (caretakers, wardens) for hostel-scoped notices.
    """
    is_urgent = announcement.severity == "URGENT"
    verb = NotificationVerb.ANNOUNCEMENT_URGENT if is_urgent else NotificationVerb.ANNOUNCEMENT
    msg_prefix = "[URGENT] " if is_urgent else ""
    title = f"{msg_prefix}{announcement.title}"
    msg = f"{msg_prefix}{announcement.title}: {announcement.body[:120]}"

    # Build notifications for audience hostelers
    batch_size = 500
    all_recipient_ids = list(audience_user_ids)

    # Also notify hostel staff (caretakers/wardens) for hostel-scoped notices
    if not announcement.all_hostels:
        hostel_ids = list(announcement.hostels.values_list("id", flat=True))
        if hostel_ids:
            staff_ids = list(
                User.objects.filter(
                    hostel_id__in=hostel_ids,
                    role__in=[Role.CARETAKER, Role.WARDEN],
                    is_active=True,
                ).values_list("id", flat=True)
            )
            # Add staff IDs that aren't already in the audience
            existing_ids = set(all_recipient_ids)
            for sid in staff_ids:
                if sid not in existing_ids:
                    all_recipient_ids.append(sid)

    for i in range(0, len(all_recipient_ids), batch_size):
        batch = all_recipient_ids[i : i + batch_size]
        notifs = [
            Notification(
                recipient_id=uid,
                announcement=announcement,
                verb=verb,
                title=title,
                notification_type=NotificationType.ANNOUNCEMENT,
                message=msg,
                event_key=_announcement_event_key(verb, announcement.id, uid),
            )
            for uid in batch
        ]
        Notification.objects.bulk_create(notifs, ignore_conflicts=False)


def notify_announcement_updated(announcement, audience_user_ids):
    """
    Notify audience about a significant update to a published announcement.
    Only notifies users who haven't already received an update notification.
    """
    verb = NotificationVerb.ANNOUNCEMENT_UPDATED
    title = f"Notice Updated: {announcement.title}"
    msg = f"The notice \"{announcement.title}\" has been updated. Please review the latest version."

    batch_size = 500
    recipient_ids = list(audience_user_ids)

    # Filter out recipients who already have an update notification for this announcement
    existing = set(
        Notification.all_objects.filter(
            announcement=announcement,
            verb=verb,
        ).values_list("recipient_id", flat=True)
    )
    recipient_ids = [uid for uid in recipient_ids if uid not in existing]

    for i in range(0, len(recipient_ids), batch_size):
        batch = recipient_ids[i : i + batch_size]
        notifs = [
            Notification(
                recipient_id=uid,
                announcement=announcement,
                verb=verb,
                title=title,
                notification_type=NotificationType.ANNOUNCEMENT,
                message=msg,
                event_key=_announcement_event_key(verb, announcement.id, uid),
            )
            for uid in batch
        ]
        Notification.objects.bulk_create(notifs)