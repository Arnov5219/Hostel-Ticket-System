from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class AnnouncementKind(models.TextChoices):
    NOTICE = "NOTICE", "Notice"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    EMERGENCY = "EMERGENCY", "Emergency"
    EVENT = "EVENT", "Event"
    POLICY = "POLICY", "Policy"


class AnnouncementSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    IMPORTANT = "IMPORTANT", "Important"
    URGENT = "URGENT", "Urgent"


class AnnouncementStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SCHEDULED = "SCHEDULED", "Scheduled"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=150)
    body = models.TextField()
    kind = models.CharField(
        max_length=20,
        choices=AnnouncementKind.choices,
        default=AnnouncementKind.NOTICE,
    )
    severity = models.CharField(
        max_length=20,
        choices=AnnouncementSeverity.choices,
        default=AnnouncementSeverity.INFO,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    all_hostels = models.BooleanField(default=False)
    hostels = models.ManyToManyField(
        "hostels.Hostel",
        blank=True,
        related_name="announcements",
    )
    status = models.CharField(
        max_length=20,
        choices=AnnouncementStatus.choices,
        default=AnnouncementStatus.DRAFT,
    )
    is_pinned = models.BooleanField(default=False)
    publish_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to="announcements/", null=True, blank=True)
    related_ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements",
    )

    class Meta:
        ordering = ["-is_pinned", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["is_pinned", "published_at"]),
        ]

    def __str__(self):
        return self.title


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="reads",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcement_reads",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["announcement", "user"],
                name="unique_announcement_user_read",
            )
        ]

    def __str__(self):
        return f"{self.user.login_id} read {self.announcement.title}"
