from django.contrib import admin

from apps.hostels.models import Hostel, Room


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "gender_type", "responsible_staff", "responsible_warden", "is_active")
    search_fields = ("code", "name")
    list_filter = ("gender_type", "is_active")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "hostel", "floor", "capacity", "is_active")
    search_fields = ("room_number", "hostel__code", "hostel__name")
    list_filter = ("hostel", "floor", "is_active")
