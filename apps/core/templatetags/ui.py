from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def status_pill(status):
    """Renders ERPNext-style pastel status pill."""
    if not status:
        return ""
    status_str = str(status).upper()
    css_class = status_str.lower()
    label = status_str.replace("_", " ").title()
    return mark_safe(f'<span class="status-pill {css_class}">{label}</span>')


@register.simple_tag
def priority_dot(priority):
    """Renders priority dot with label."""
    if not priority:
        return ""
    prio_str = str(priority).upper()
    css_class = prio_str.lower()
    label = prio_str.capitalize()
    return mark_safe(
        f'<span class="priority-indicator"><span class="prio-dot {css_class}"></span>{label}</span>'
    )


@register.simple_tag
def level_badge(level):
    """Renders escalation level badge (L1 to L4)."""
    if not level:
        return ""
    lvl_num = int(level)
    return mark_safe(f'<span class="level-badge l{lvl_num}">L{lvl_num}</span>')


@register.simple_tag
def time_ago(dt):
    """Renders dense time-ago representation (e.g. 5m, 2h, 3d, 1y)."""
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    if days < 30:
        return f"{days}d"
    months = days // 30
    if months < 12:
        return f"{months}mo"
    years = days // 365
    return f"{years}y"


@register.simple_tag
def user_avatar(user, size="md"):
    """Renders avatar or fallback initials."""
    size_cls = f"avatar-{size}" if size != "md" else ""
    if user and getattr(user, "avatar", None) and user.avatar:
        return mark_safe(
            f'<div class="avatar {size_cls}"><img src="{user.avatar.url}" alt="{user.get_full_name() or user.username}"></div>'
        )
    initials = "?"
    if user:
        name = getattr(user, "full_name", "") or getattr(user, "login_id", "") or str(user)
        parts = name.split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[1][0]).upper()
        elif parts:
            initials = parts[0][:2].upper()
    return mark_safe(f'<div class="avatar {size_cls}"><span>{initials}</span></div>')
