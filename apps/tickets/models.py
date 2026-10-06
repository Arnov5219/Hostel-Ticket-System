from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


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


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default="ticket", help_text="Lucide icon name")
    default_priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SubCategory(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("category", "name")
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.category.name} - {self.name}"


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
    sub_category = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
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
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    current_level = models.PositiveSmallIntegerField(default=1)
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

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "current_level"]),
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["due_at"]),
        ]

    def __str__(self):
        return f"{self.ticket_no} - {self.title}"


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


class TicketComment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_comments",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="True for staff-only internal notes")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        kind = "Internal Note" if self.is_internal else "Comment"
        return f"{kind} by {self.author.login_id} on {self.ticket.ticket_no}"


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

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        actor_name = self.actor.login_id if self.actor else "System"
        return f"{self.ticket.ticket_no} - {self.action} by {actor_name}"
