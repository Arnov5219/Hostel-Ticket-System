from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.tickets.querysets import ActiveTicketManager, AllTicketManager


class Priority(models.TextChoices):
    URGENT = "URGENT", "Urgent"
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"


class Status(models.TextChoices):
    OPEN = "OPEN", "Open"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    ON_HOLD = "ON_HOLD", "On Hold"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"
    REJECTED = "REJECTED", "Rejected"


class TicketVisibility(models.TextChoices):
    PRIVATE = "PRIVATE", "Private"
    HOSTEL = "HOSTEL", "Share with my hostel"


class CommentScope(models.TextChoices):
    INTERNAL = "INTERNAL", "Internal"
    PRIVATE = "PRIVATE", "Private"
    COMMUNITY = "COMMUNITY", "Community"


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default="ticket", help_text="Lucide icon name")
    default_priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    # DEPRECATED: Community removed, kept for historical data, no UI
    allow_community = models.BooleanField(
        default=True,
        help_text="Allow sharing tickets in this category to community feed",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default="#2490EF")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SLAPolicy(TimeStampedModel):
    priority = models.CharField(max_length=10, choices=Priority.choices)
    level = models.PositiveSmallIntegerField(help_text="Escalation level (1 to 4)")
    hours = models.PositiveIntegerField(help_text="Resolution SLA target in hours")

    class Meta:
        unique_together = ("priority", "level")
        ordering = ["priority", "level"]
        verbose_name = "SLA Policy"
        verbose_name_plural = "SLA Policies"

    def __str__(self):
        return f"{self.get_priority_display()} L{self.level}: {self.hours}h"


class RoutingRule(TimeStampedModel):
    hostel = models.ForeignKey(
        "hostels.Hostel",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="routing_rules",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="routing_rules",
    )
    level = models.PositiveSmallIntegerField(default=1)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_routing_rules",
    )

    class Meta:
        ordering = ["hostel", "category", "level"]

    def __str__(self):
        h = self.hostel.name if self.hostel else "All Hostels"
        c = self.category.name if self.category else "All Categories"
        return f"[{h} | {c} | L{self.level}] -> {self.assignee}"


class SavedFilter(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filters",
    )
    name = models.CharField(max_length=100)
    querystring = models.TextField()
    view = models.CharField(max_length=20, default="list")  # 'list' or 'kanban'

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.user.login_id} - {self.name}"


class Ticket(TimeStampedModel):
    ticket_no = models.CharField(max_length=30, unique=True, db_index=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="tickets")
    # DEPRECATED: Community removed, kept for historical data, no UI
    visibility = models.CharField(
        max_length=20,
        choices=TicketVisibility.choices,
        default=TicketVisibility.PRIVATE,
    )
    # DEPRECATED: Community removed, kept for historical data, no UI
    show_reporter_name = models.BooleanField(default=False)
    # DEPRECATED: Community removed, kept for historical data, no UI
    base_priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_tickets",
    )
    hostel = models.ForeignKey(
        "hostels.Hostel",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    room = models.ForeignKey(
        "hostels.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    location_detail = models.CharField(max_length=120, blank=True, default="")
    outside_own_hostel = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    current_level = models.PositiveSmallIntegerField(default=1)
    # DEPRECATED: Community removed, kept for historical data, no UI
    repost_count = models.PositiveIntegerField(default=0, db_index=True)
    level_started_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # DEPRECATED: Community removed, kept for historical data, no UI
    community_hidden = models.BooleanField(default=False)
    # DEPRECATED: Community removed, kept for historical data, no UI
    last_notified_threshold = models.PositiveSmallIntegerField(default=0)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_overdue = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default="")
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1 to 5
    followers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="followed_tickets",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="tickets")

    # Soft-delete audit fields (Feature B)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_tickets",
    )
    delete_reason = models.CharField(max_length=200, blank=True, default="")

    objects = ActiveTicketManager()
    all_objects = AllTicketManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "current_level"]),
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["due_at"]),
            models.Index(fields=["hostel", "visibility", "status", "last_activity_at"]),
            models.Index(fields=["hostel", "repost_count"]),
        ]

    def __str__(self):
        return f"{self.ticket_no} - {self.title}"

    @property
    def affected_count(self):
        # DEPRECATED: Community removed, kept for historical data, no UI
        return self.repost_count + 1


class TicketAttachment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file = models.ImageField(upload_to="attachments/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_attachments",
    )

    def __str__(self):
        return f"Attachment for {self.ticket.ticket_no}"


# DEPRECATED: Community removed, kept for historical data, no UI
class TicketRepost(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="reposts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_reposts",
    )
    note = models.CharField(max_length=140, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "user"],
                name="unique_ticket_user_repost",
            )
        ]

    def __str__(self):
        return f"Repost by {self.user.login_id} on {self.ticket.ticket_no}"


class ActiveTicketCommentManager(models.Manager):
    """Excludes legacy COMMUNITY comments from all querysets."""
    def get_queryset(self):
        return super().get_queryset().exclude(scope="COMMUNITY")


class TicketComment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_comments",
    )
    body = models.TextField()
    # DEPRECATED: Community removed, kept for historical data, no UI
    scope = models.CharField(
        max_length=20,
        choices=CommentScope.choices,
        default=CommentScope.PRIVATE,
    )
    # DEPRECATED: Community removed, kept for historical data, no UI
    is_hidden = models.BooleanField(default=False)
    # DEPRECATED: Community removed, kept for historical data, no UI
    hidden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hidden_ticket_comments",
    )
    # DEPRECATED: Community removed, kept for historical data, no UI
    hidden_reason = models.CharField(max_length=255, blank=True)
    # DEPRECATED: Community removed, kept for historical data, no UI
    is_official = models.BooleanField(default=False)

    objects = ActiveTicketCommentManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.scope} Comment by {self.author.login_id} on {self.ticket.ticket_no}"

    @property
    def is_internal(self):
        return self.scope == CommentScope.INTERNAL

    @is_internal.setter
    def is_internal(self, val):
        self.scope = CommentScope.INTERNAL if val else CommentScope.PRIVATE


# DEPRECATED: Community removed, kept for historical data, no UI
class CommentReport(TimeStampedModel):
    comment = models.ForeignKey(
        TicketComment,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_reports",
    )

    class Meta:
        unique_together = [("comment", "reporter")]

    def __str__(self):
        return f"Report by {self.reporter.login_id} on Comment {self.comment_id}"


# DEPRECATED: Community removed, kept for historical data, no UI
class CriticalityRule(TimeStampedModel):
    min_reposts = models.PositiveIntegerField(unique=True)
    bump_levels = models.PositiveSmallIntegerField(default=1)
    force_priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        null=True,
        blank=True,
    )
    notify_level = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["min_reposts"]

    def __str__(self):
        if self.force_priority:
            effect = f"Force {self.force_priority}"
        else:
            effect = f"+{self.bump_levels} levels"
        return f"{self.min_reposts}+ reposts: {effect}"


class ActivityAction(models.TextChoices):
    CREATED = "CREATED", "Created"
    ASSIGNED = "ASSIGNED", "Assigned"
    STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
    ESCALATED = "ESCALATED", "Escalated"
    REASSIGNED = "REASSIGNED", "Reassigned"
    COMMENTED = "COMMENTED", "Commented"
    REOPENED = "REOPENED", "Reopened"
    CLOSED = "CLOSED", "Closed"
    REJECTED = "REJECTED", "Rejected"
    REPOSTED = "REPOSTED", "Reposted"
    REPOST_REMOVED = "REPOST_REMOVED", "Repost Removed"
    PRIORITY_AUTO_RAISED = "PRIORITY_AUTO_RAISED", "Priority Auto-Raised"
    COMMUNITY_COMMENT = "COMMUNITY_COMMENT", "Community Comment"
    COMMENT_HIDDEN = "COMMENT_HIDDEN", "Comment Hidden"
    VISIBILITY_CHANGED = "VISIBILITY_CHANGED", "Visibility Changed"
    COMMUNITY_HIDDEN = "COMMUNITY_HIDDEN", "Community Hidden"
    DELETED = "DELETED", "Deleted"
    RESTORED = "RESTORED", "Restored"
    PURGED = "PURGED", "Purged"


class ActiveTicketActivityManager(models.Manager):
    """Excludes legacy community actions from activity timeline."""
    LEGACY_ACTIONS = [
        "REPOSTED",
        "REPOST_REMOVED",
        "PRIORITY_AUTO_RAISED",
        "COMMUNITY_COMMENT",
        "COMMENT_HIDDEN",
        "COMMUNITY_HIDDEN",
        "VISIBILITY_CHANGED",
    ]

    def get_queryset(self):
        return super().get_queryset().exclude(action__in=self.LEGACY_ACTIONS)


class TicketActivity(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_activities",
    )
    action = models.CharField(max_length=30, choices=ActivityAction.choices)
    from_value = models.CharField(max_length=150, blank=True, default="")
    to_value = models.CharField(max_length=150, blank=True, default="")
    note = models.TextField(blank=True, default="")

    objects = ActiveTicketActivityManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        actor_name = self.actor.login_id if self.actor else "System"
        return f"{self.ticket.ticket_no} - {self.action} by {actor_name}"
