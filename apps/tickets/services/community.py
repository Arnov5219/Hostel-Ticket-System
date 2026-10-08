import re
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Case, Count, Exists, F, IntegerField, OuterRef, Q, Value, When
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationVerb
from apps.tickets.models import (
    ActivityAction,
    CommentScope,
    Status,
    Ticket,
    TicketActivity,
    TicketComment,
    TicketRepost,
    TicketVisibility,
)
from apps.tickets.services.criticality import recompute_criticality

STOP_WORDS = {
    "the", "and", "for", "with", "not", "this", "that", "from", "are", "was",
    "room", "block", "hostel", "please", "issue", "problem", "broken",
}


def clean_text(text: str) -> str:
    """Strips control characters from text input."""
    if not text:
        return ""
    return "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or not ch.isspace() or ch == " ")


def feed_queryset(user, sort="recent", category_id=None, status=None):
    """
    Returns community feed tickets visible to the user.
    Scope: user's hostel, visibility=HOSTEL, community_hidden=False, category.allow_community=True.
    Reporter is not the current user (user's own tickets are shown separately in My Tickets).
    """
    # Active statuses + resolved within 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    active_or_recent_resolved = (
        Q(status__in=[Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD])
        | Q(status=Status.RESOLVED, resolved_at__gte=seven_days_ago)
    )

    qs = Ticket.objects.filter(
        hostel=user.hostel,
        visibility=TicketVisibility.HOSTEL,
        community_hidden=False,
        category__allow_community=True,
    ).exclude(reporter=user).filter(active_or_recent_resolved)

    if category_id:
        qs = qs.filter(category_id=category_id)

    if status:
        qs = qs.filter(status=status)

    # Annotate whether the current user has reposted this ticket
    user_repost_exists = TicketRepost.objects.filter(
        ticket=OuterRef("pk"),
        user=user,
    )
    qs = qs.annotate(
        has_reposted=Exists(user_repost_exists),
        community_comments_count=Count(
            "comments",
            filter=Q(comments__scope=CommentScope.COMMUNITY, comments__is_hidden=False),
            distinct=True,
        ),
    )

    # Sorting
    if sort == "trending":
        # Order by repost count, then last_activity_at
        qs = qs.order_by("-repost_count", "-last_activity_at")
    elif sort == "critical":
        # Order by priority weight: URGENT(4), HIGH(3), MEDIUM(2), LOW(1)
        priority_rank = Case(
            When(priority="URGENT", then=Value(4)),
            When(priority="HIGH", then=Value(3)),
            When(priority="MEDIUM", then=Value(2)),
            When(priority="LOW", then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
        qs = qs.annotate(_prio_weight=priority_rank).order_by("-_prio_weight", "-repost_count", "-last_activity_at")
    elif sort in ["mine", "my_reposts"]:
        qs = qs.filter(reposts__user=user).order_by("-last_activity_at")
    else:  # default "recent"
        qs = qs.order_by("-last_activity_at")

    return qs.select_related("reporter", "category", "hostel")


def toggle_repost(user, ticket: Ticket, note: str = "") -> dict:
    """
    Toggles repost on a ticket for a user.
    Transaction-safe with select_for_update.
    """
    if not user.is_hosteler:
        raise PermissionDenied("Only hostelers can repost community tickets.")

    if ticket.hostel != user.hostel:
        raise PermissionDenied("You can only repost tickets from your own hostel.")

    if ticket.reporter == user:
        raise ValidationError("You cannot repost your own ticket.")

    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    if ticket.status not in active_statuses:
        raise ValidationError("This issue is no longer active.")

    note = clean_text(note)[:140]

    with transaction.atomic():
        locked_ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
        now = timezone.now()

        existing_repost = TicketRepost.objects.filter(ticket=locked_ticket, user=user).first()
        if existing_repost:
            existing_repost.delete()
            Ticket.objects.filter(pk=locked_ticket.pk).update(
                repost_count=Case(
                    When(repost_count__gt=0, then=F("repost_count") - 1),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                last_activity_at=now,
            )
            locked_ticket.followers.remove(user)

            TicketActivity.objects.create(
                ticket=locked_ticket,
                actor=user,
                action=ActivityAction.REPOST_REMOVED,
                note="Hosteler removed their repost.",
            )
            reposted = False
        else:
            # Check daily limit of 30 reposts
            one_day_ago = now - timedelta(days=1)
            recent_reposts = TicketRepost.objects.filter(
                user=user,
                created_at__gte=one_day_ago,
            ).count()
            if recent_reposts >= 30:
                raise ValidationError("You have reached the daily repost limit (30).")

            TicketRepost.objects.create(ticket=locked_ticket, user=user, note=note)
            Ticket.objects.filter(pk=locked_ticket.pk).update(
                repost_count=F("repost_count") + 1,
                last_activity_at=now,
            )
            locked_ticket.followers.add(user)

            act_note = f"Hosteler reposted: {note}" if note else "Hosteler marked as facing this too."
            TicketActivity.objects.create(
                ticket=locked_ticket,
                actor=user,
                action=ActivityAction.REPOSTED,
                note=act_note,
            )

            # Batched hourly notification to reporter
            if locked_ticket.reporter and locked_ticket.reporter != user:
                one_hour_ago = now - timedelta(hours=1)
                recent_notif = Notification.objects.filter(
                    recipient=locked_ticket.reporter,
                    ticket=locked_ticket,
                    verb=NotificationVerb.REPOSTED,
                    created_at__gte=one_hour_ago,
                ).first()

                new_count = locked_ticket.repost_count + 1
                msg = f"{new_count} hosteler{'s' if new_count > 1 else ''} reposted your ticket {locked_ticket.ticket_no}."
                if recent_notif:
                    recent_notif.message = msg
                    recent_notif.save(update_fields=["message"])
                else:
                    Notification.objects.create(
                        recipient=locked_ticket.reporter,
                        ticket=locked_ticket,
                        verb=NotificationVerb.REPOSTED,
                        message=msg,
                    )

            reposted = True

        locked_ticket.refresh_from_db()
        recompute_criticality(locked_ticket)

    return {
        "reposted": reposted,
        "repost_count": locked_ticket.repost_count,
        "affected_count": locked_ticket.affected_count,
        "priority": locked_ticket.priority,
        "ticket": locked_ticket,
    }


def add_community_comment(user, ticket: Ticket, body: str) -> TicketComment:
    """
    Adds a public community comment to a ticket.
    """
    if ticket.visibility != TicketVisibility.HOSTEL:
        raise ValidationError("Community comments are only permitted on shared hostel tickets.")

    body = clean_text(body).strip()
    if not body:
        raise ValidationError("Comment body cannot be empty.")
    if len(body) > 500:
        raise ValidationError("Comment cannot exceed 500 characters.")

    # Rate limit: max 5 comments per minute per user
    one_min_ago = timezone.now() - timedelta(minutes=1)
    recent_count = TicketComment.objects.filter(author=user, created_at__gte=one_min_ago).count()
    if recent_count >= 5:
        raise ValidationError("You are commenting too fast. Please wait a minute before replying again.")

    is_staff = user.role in [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]

    comment = TicketComment.objects.create(
        ticket=ticket,
        author=user,
        body=body,
        scope=CommentScope.COMMUNITY,
        is_official=is_staff,
    )

    ticket.last_activity_at = timezone.now()
    ticket.save(update_fields=["last_activity_at"])

    # Log activity
    act_note = f"Community comment by {user.role}: {body[:60]}" if is_staff else f"Community comment: {body[:60]}"
    TicketActivity.objects.create(
        ticket=ticket,
        actor=user,
        action=ActivityAction.COMMUNITY_COMMENT,
        note=act_note,
    )

    # Notify reporter and followers
    recipients = set()
    if ticket.reporter and ticket.reporter != user:
        recipients.add(ticket.reporter)
    for follower in ticket.followers.all():
        if follower != user:
            recipients.add(follower)

    display_name = user.full_name or user.login_id
    notif_msg = f"{display_name} commented on community issue {ticket.ticket_no}."
    notifications = [
        Notification(
            recipient=r,
            ticket=ticket,
            verb=NotificationVerb.COMMUNITY_COMMENT,
            message=notif_msg,
        )
        for r in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)

    return comment


def hide_comment(staff_user, comment: TicketComment, reason: str = "") -> TicketComment:
    """Hides a community comment. Restricted to Warden, Chief Warden, and Admin."""
    if staff_user.role not in [Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]:
        raise PermissionDenied("Only Wardens and Administrators can moderate comments.")

    comment.is_hidden = True
    comment.hidden_by = staff_user
    comment.hidden_reason = reason.strip()
    comment.save(update_fields=["is_hidden", "hidden_by", "hidden_reason"])

    TicketActivity.objects.create(
        ticket=comment.ticket,
        actor=staff_user,
        action=ActivityAction.COMMENT_HIDDEN,
        note=f"Comment #{comment.id} hidden by staff: {reason}",
    )
    return comment


def set_community_hidden(staff_user, ticket: Ticket, hidden: bool, reason: str = "") -> Ticket:
    """Removes or restores a ticket from the community feed."""
    if staff_user.role not in [Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]:
        raise PermissionDenied("Only Wardens and Administrators can change community feed visibility.")

    ticket.community_hidden = hidden
    ticket.save(update_fields=["community_hidden"])

    TicketActivity.objects.create(
        ticket=ticket,
        actor=staff_user,
        action=ActivityAction.COMMUNITY_HIDDEN,
        note=f"Community visibility changed to {'hidden' if hidden else 'visible'}. Reason: {reason}",
    )
    return ticket


def similar_open_tickets(user, title: str, category=None):
    """
    Finds up to 3 similar open tickets in the same hostel to avoid duplicates.
    """
    if not user.hostel or not title or len(title.strip()) < 3:
        return []

    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    qs = Ticket.objects.filter(
        hostel=user.hostel,
        visibility=TicketVisibility.HOSTEL,
        community_hidden=False,
        status__in=active_statuses,
    ).exclude(reporter=user)

    if category:
        qs = qs.filter(category=category)

    # Extract words length >= 3
    words = [
        re.sub(r"[^\w]", "", w.lower())
        for w in title.split()
    ]
    keywords = [w for w in words if len(w) >= 3 and w not in STOP_WORDS][:3]

    if not keywords:
        return []

    q_filter = Q()
    for kw in keywords:
        q_filter |= Q(title__icontains=kw)

    return list(qs.filter(q_filter).select_related("category", "reporter")[:3])
