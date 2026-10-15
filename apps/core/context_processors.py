from apps.core.navigation import nav_for
from apps.notifications.models import Notification


def global_ui_context(request):
    """Provides global UI variables and unified navigation across templates."""
    context = {
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
