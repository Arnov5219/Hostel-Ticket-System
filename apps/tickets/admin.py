from django.contrib import admin

from apps.tickets.models import (
    Category,
    RoutingRule,
    SavedFilter,
    SLAPolicy,
    Tag,
    Ticket,
    TicketActivity,
    TicketAttachment,
    TicketComment,
)

DEPRECATED_COMMUNITY_ACTIONS = [
    "REPOSTED",
    "REPOST_REMOVED",
    "PRIORITY_AUTO_RAISED",
    "COMMUNITY_COMMENT",
    "COMMENT_HIDDEN",
    "COMMUNITY_HIDDEN",
    "VISIBILITY_CHANGED",
]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "default_priority", "is_active"]
    list_filter = ["is_active", "default_priority"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "color"]
    search_fields = ["name"]


@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ["priority", "level", "hours"]
    list_filter = ["priority", "level"]


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ["hostel", "category", "level", "assignee"]
    list_filter = ["level", "hostel", "category"]


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "view"]
    search_fields = ["name", "user__login_id"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_no",
        "title",
        "hostel",
        "category",
        "priority",
        "status",
        "created_at",
    ]
    list_filter = ["status", "priority", "hostel", "category"]
    search_fields = ["ticket_no", "title", "description", "reporter__login_id"]


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ["ticket", "uploaded_by", "created_at"]


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ["ticket", "author", "scope", "created_at"]
    list_filter = ["scope"]
    search_fields = ["ticket__ticket_no", "author__login_id", "body"]

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(scope="COMMUNITY")


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    list_display = ["ticket", "actor", "action", "created_at"]
    list_filter = ["action"]
    search_fields = ["ticket__ticket_no", "actor__login_id"]

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(action__in=DEPRECATED_COMMUNITY_ACTIONS)
