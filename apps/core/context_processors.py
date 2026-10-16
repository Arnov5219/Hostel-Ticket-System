from datetime import datetime

from django.conf import settings

from apps.core.navigation import nav_for
from apps.notifications.models import Notification


def global_ui_context(request):
    """Provides global UI variables and unified navigation across templates."""
    context = {
        "site_name": getattr(settings, "SITE_NAME", "HostelFlow"),
        "site_descriptor": getattr(settings, "SITE_DESCRIPTOR", "Hostel Ticket System"),
        "site_tagline": getattr(settings, "SITE_TAGLINE", "Report. Track. Resolve."),
        "department_name": getattr(settings, "DEPARTMENT_NAME", "Department of Residential Infrastructure"),
        "help_hotline": getattr(settings, "HELP_HOTLINE_NUMBER", ""),
        "help_warden_desk": getattr(settings, "HELP_WARDEN_DESK_NUMBER", ""),
        "help_guide_url": getattr(settings, "HELP_GUIDE_URL", "#"),
        "current_year": datetime.now().year,
        "unread_notifications_count": 0,
        "navigation": {"sidebar_items": [], "mobile_bar_items": [], "mobile_more_items": []},
    }
    if hasattr(request, "user") and request.user.is_authenticated:
        context["user_role"] = getattr(request.user, "role", "")
        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        context["unread_notifications_count"] = unread_count
        context["navigation"] = nav_for(request.user)
        if hasattr(request, "session"):
            context["undo_delete"] = request.session.pop("undo_delete", None)
    return context

