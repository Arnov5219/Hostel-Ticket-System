from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "login_id",
        "full_name",
        "role",
        "escalation_level",
        "hostel",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "escalation_level", "hostel", "is_active")
    search_fields = ("login_id", "full_name", "email", "phone")
    ordering = ("login_id",)

    fieldsets = (
        (None, {"fields": ("login_id", "password")}),
        (
            "Personal info",
            {"fields": ("full_name", "email", "phone", "avatar")},
        ),
        (
            "Role & Hostel Assignment",
            {"fields": ("role", "escalation_level", "hostel")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "login_id",
                    "full_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
