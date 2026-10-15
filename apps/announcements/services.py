
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.announcements.models import (
    Announcement,
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.notifications.models import Notification, NotificationVerb


def audience_users(announcement: Announcement):
    """Returns queryset of active hostelers targeted by this announcement."""
    qs = User.objects.filter(role=Role.HOSTELER, is_active=True)
    if announcement.all_hostels:
        return qs
    return qs.filter(hostel__in=announcement.hostels.all()).distinct()


def can_publish(user: User, announcement: Announcement) -> bool:
    """Enforces audience scope rules for publishing announcements."""
    if not user.is_authenticated:
        return False
    if user.role in [Role.ADMIN, Role.CHIEF_WARDEN]:
        return True
    if user.role == Role.WARDEN:
        if not user.hostel:
            return False
        if announcement.all_hostels:
            return False
        # Every targeted hostel must be the warden's hostel
        targeted = announcement.hostels.all()
        if not targeted.exists():
            return False
        for h in targeted:
            if h.id != user.hostel.id:
                return False
        return True
    return False


def publish(announcement: Announcement, actor: User) -> Announcement:
    """
    Publishes an announcement and dispatches notifications to the audience in batches of 500.
    """
    if not can_publish(actor, announcement):
        raise PermissionDenied("You do not have permission to publish this announcement.")

    now = timezone.now()
    announcement.status = AnnouncementStatus.PUBLISHED
    announcement.published_at = now
    announcement.save(update_fields=["status", "published_at"])

    # Determine notification verb
    is_urgent = announcement.severity == AnnouncementSeverity.URGENT
    verb = NotificationVerb.ANNOUNCEMENT_URGENT if is_urgent else NotificationVerb.ANNOUNCEMENT
    msg_prefix = "[URGENT] " if is_urgent else ""
    msg = f"{msg_prefix}{announcement.title}: {announcement.body[:120]}"

    # Fetch audience hostelers
    audience = audience_users(announcement)
    recipient_ids = list(audience.values_list("id", flat=True))

    # Bulk create notifications in batches of 500
    batch_size = 500
    for i in range(0, len(recipient_ids), batch_size):
        batch = recipient_ids[i:i + batch_size]
        notifs = [
            Notification(
                recipient_id=uid,
                announcement=announcement,
                verb=verb,
                message=msg,
            )
            for uid in batch
        ]
        Notification.objects.bulk_create(notifs)

    return announcement


def schedule(announcement: Announcement, when, actor: User) -> Announcement:
    """Schedules an announcement to be published at a future datetime."""
    if not can_publish(actor, announcement):
        raise PermissionDenied("You do not have permission to schedule this announcement.")

    if when <= timezone.now():
        raise ValidationError("Scheduled time must be in the future.")

    announcement.status = AnnouncementStatus.SCHEDULED
    announcement.publish_at = when
    announcement.save(update_fields=["status", "publish_at"])
    return announcement


def archive(announcement: Announcement, actor: User) -> Announcement:
    """Archives an announcement."""
    if not can_publish(actor, announcement):
        raise PermissionDenied("You do not have permission to archive this announcement.")

    announcement.status = AnnouncementStatus.ARCHIVED
    announcement.save(update_fields=["status"])
    return announcement


def visible_to(user: User):
    """
    Returns queryset of announcements visible to the user:
    Published, not expired, targeting the user's hostel or all hostels.
    Pinned first, then newest.
    """
    now = timezone.now()
    qs = Announcement.objects.filter(
        status=AnnouncementStatus.PUBLISHED,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now),
    )

    if user.is_authenticated:
        if user.is_hosteler:
            if user.hostel:
                qs = qs.filter(Q(all_hostels=True) | Q(hostels=user.hostel))
            else:
                qs = qs.filter(all_hostels=True)
        elif user.is_warden or user.is_caretaker:
            if user.hostel:
                qs = qs.filter(Q(all_hostels=True) | Q(hostels=user.hostel))
            else:
                qs = qs.filter(all_hostels=True)
        # Admin and Chief Warden see all published announcements

    return qs.distinct().order_by("-is_pinned", "-published_at")


def unread_count(user: User) -> int:
    """Counts unread announcements visible to the user."""
    if not user.is_authenticated:
        return 0
    visible_qs = visible_to(user)
    read_ids = AnnouncementRead.objects.filter(user=user).values_list("announcement_id", flat=True)
    return visible_qs.exclude(id__in=read_ids).count()


def unread_urgent_announcements(user: User):
    """Returns queryset of unread urgent announcements visible to the user."""
    if not user.is_authenticated:
        return Announcement.objects.none()
    visible_qs = visible_to(user).filter(severity=AnnouncementSeverity.URGENT)
    read_ids = AnnouncementRead.objects.filter(user=user).values_list("announcement_id", flat=True)
    return visible_qs.exclude(id__in=read_ids)


def mark_read(user: User, announcement: Announcement) -> AnnouncementRead:
    """Marks an announcement as read by the user (idempotent)."""
    if not user.is_authenticated:
        return None
    read_obj, _ = AnnouncementRead.objects.get_or_create(
        announcement=announcement,
        user=user,
    )
    # Also mark associated notifications as read
    Notification.objects.filter(
        recipient=user,
        announcement=announcement,
        is_read=False,
    ).update(is_read=True)
    return read_obj
