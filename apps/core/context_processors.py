def global_ui_context(request):
    """Provides global UI variables across templates."""
    context = {
        "unread_notifications_count": 0,
    }
    if request.user.is_authenticated:
        # Will be populated with notification count once models exist
        context["user_role"] = getattr(request.user, "role", "")
    return context
