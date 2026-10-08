from django.contrib import admin

from apps.announcements.models import Announcement, AnnouncementRead


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "severity", "status", "author", "all_hostels", "is_pinned", "published_at"]
    list_filter = ["status", "severity", "kind", "is_pinned", "all_hostels"]
    search_fields = ["title", "body"]
    filter_horizontal = ["hostels"]


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ["announcement", "user", "read_at"]
    search_fields = ["announcement__title", "user__login_id"]
