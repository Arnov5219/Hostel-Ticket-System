from apps.notifications.models import Notification


def global_ui_context(request):
    """Provides global UI variables across templates."""
    context = {
        "unread_notifications_count": 0,
    }
    if hasattr(request, "user") and request.user.is_authenticated:
        context["user_role"] = getattr(request.user, "role", "")
        context["unread_notifications_count"] = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
    return context
