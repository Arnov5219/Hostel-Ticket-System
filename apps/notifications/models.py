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
    REPOSTED = "REPOSTED"
    COMMUNITY_COMMENT = "COMMUNITY_COMMENT"
    PRIORITY_RAISED = "PRIORITY_RAISED"
    CRITICAL_ISSUE = "CRITICAL_ISSUE"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    ANNOUNCEMENT_URGENT = "ANNOUNCEMENT_URGENT"


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
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.login_id}: {self.verb}"
