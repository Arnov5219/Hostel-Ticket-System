from django.contrib import admin

from apps.tickets.models import (
    Category,
    CriticalityRule,
    RoutingRule,
    SavedFilter,
    SLAPolicy,
    Tag,
    Ticket,
    TicketActivity,
    TicketAttachment,
    TicketComment,
    TicketRepost,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "default_priority", "allow_community", "is_active"]
    list_filter = ["allow_community", "is_active", "default_priority"]
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
        "base_priority",
        "status",
        "visibility",
        "repost_count",
        "created_at",
    ]
    list_filter = ["status", "priority", "visibility", "community_hidden", "hostel", "category"]
    search_fields = ["ticket_no", "title", "description", "reporter__login_id"]


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ["ticket", "uploaded_by", "created_at"]


# TicketRepost is not registered in Django Admin (Section 4.2: Community is hostelers only)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ["ticket", "author", "scope", "is_official", "is_hidden", "created_at"]
    list_filter = ["scope", "is_official", "is_hidden"]
    search_fields = ["ticket__ticket_no", "author__login_id", "body"]

    def get_queryset(self, request):
        # Community comments are not listed in Django admin
        return super().get_queryset(request).exclude(scope="COMMUNITY")


@admin.register(CriticalityRule)
class CriticalityRuleAdmin(admin.ModelAdmin):
    list_display = ["min_reposts", "bump_levels", "force_priority", "notify_level"]
    ordering = ["min_reposts"]


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    list_display = ["ticket", "actor", "action", "created_at"]
    list_filter = ["action"]
    search_fields = ["ticket__ticket_no", "actor__login_id"]
