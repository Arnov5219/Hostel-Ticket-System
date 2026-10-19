from django.conf import settings
from django.db import models


class NotificationVerb:
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    COMMENTED = "COMMENTED"
    REOPENED = "REOPENED"
    REASSIGNED = "REASSIGNED"
    # DEPRECATED: Community removed, kept for historical data, no UI
    REPOSTED = "REPOSTED"
    COMMUNITY_COMMENT = "COMMUNITY_COMMENT"
    PRIORITY_RAISED = "PRIORITY_RAISED"
    CRITICAL_ISSUE = "CRITICAL_ISSUE"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    ANNOUNCEMENT_URGENT = "ANNOUNCEMENT_URGENT"
    ANNOUNCEMENT_UPDATED = "ANNOUNCEMENT_UPDATED"


DEPRECATED_COMMUNITY_VERBS = [
    NotificationVerb.REPOSTED,
    NotificationVerb.COMMUNITY_COMMENT,
    NotificationVerb.PRIORITY_RAISED,
    NotificationVerb.CRITICAL_ISSUE,
]


class NotificationType(models.TextChoices):
    TICKET = "TICKET", "Ticket"
    ANNOUNCEMENT = "ANNOUNCEMENT", "Announcement"
    SYSTEM = "SYSTEM", "System"


class ActiveNotificationManager(models.Manager):
    """Excludes legacy community notifications from lists, unread counts, and bell badges."""
    def get_queryset(self):
        return super().get_queryset().exclude(verb__in=DEPRECATED_COMMUNITY_VERBS)


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    announcement = models.ForeignKey(
        "announcements.Announcement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    verb = models.CharField(max_length=100)
    title = models.CharField(max_length=200, blank=True, default="")
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Idempotency key to prevent duplicates from the same event
    event_key = models.CharField(max_length=255, blank=True, default="", db_index=True)

    objects = ActiveNotificationManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.login_id}: {self.verb}"

    @classmethod
    def create_once(cls, *, event_key="", **kwargs):
        """Create notification only if event_key doesn't already exist for this recipient.

        If event_key is empty, always creates (no dedup).
        Returns the created Notification or None if duplicate.
        """
        if event_key:
            if cls.all_objects.filter(
                recipient=kwargs["recipient"], event_key=event_key
            ).exists():
                return None
        kwargs["event_key"] = event_key
        return cls.objects.create(**kwargs)

    @property
    def display_title(self):
        """Returns title if set, otherwise falls back to verb."""
        return self.title or self.verb