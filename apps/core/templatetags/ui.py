import hashlib

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe

register = template.Library()

HUMAN_STATUS_MAP = {
    "OPEN": "Open",
    "ASSIGNED": "Assigned",
    "IN_PROGRESS": "In progress",
    "ON_HOLD": "On hold",
    "RESOLVED": "Resolved",
    "CLOSED": "Closed",
    "REJECTED": "Rejected",
}

AVATAR_BG_PALETTE = [
    ("#E8F1FD", "#1D5FB4"),  # blue
    ("#E6F4EA", "#137333"),  # green
    ("#FEF7E0", "#B06000"),  # amber
    ("#F3E8FD", "#6B3FA0"),  # purple
    ("#FCE8E6", "#C5221F"),  # red/pink
    ("#E8EAED", "#3C4043"),  # gray
]


@register.filter
def humanize_status(value):
    """Converts enum status codes like IN_PROGRESS to 'In progress'."""
    if not value:
        return ""
    val_upper = str(value).upper()
    return HUMAN_STATUS_MAP.get(val_upper, val_upper.replace("_", " ").capitalize())


@register.simple_tag
def status_pill(status):
    """Renders ERPNext-style pastel status pill with 6px leading dot."""
    if not status:
        return ""
    status_str = str(status).upper()
    css_class = status_str.lower().replace("_", "-")
    label = humanize_status(status_str)
    return mark_safe(
        f'<span class="status-pill status-pill--{css_class}">'
        f'<span class="status-pill__dot"></span>'
        f'<span class="status-pill__label">{label}</span>'
        f'</span>'
    )


@register.simple_tag
def priority_dot(priority):
    """Renders priority dot with label."""
    if not priority:
        return ""
    prio_str = str(priority).upper()
    css_class = prio_str.lower()
    label = prio_str.capitalize()
    return mark_safe(
        f'<span class="priority-indicator">'
        f'<span class="priority-dot prio-dot priority-dot--{css_class}"></span>'
        f'<span class="priority-label">{label}</span>'
        f'</span>'
    )


@register.simple_tag
def level_badge(level):
    """Renders escalation level chip (L1 to L4)."""
    if not level:
        return ""
    try:
        lvl_num = int(level)
    except (ValueError, TypeError):
        lvl_num = 1
    return mark_safe(f'<span class="level-chip level-chip--l{lvl_num}">L{lvl_num}</span>')


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
    """
    Renders a 28px circular avatar with soft deterministic background color,
    preventing plain raw letters without circle styling.
    """
    size_cls = f"avatar--{size}" if size != "md" else ""
    if user and getattr(user, "avatar", None) and user.avatar:
        return mark_safe(
            f'<div class="avatar {size_cls}"><img src="{user.avatar.url}" alt="{user.get_full_name() or user.username}"></div>'
        )

    if not user:
        # Unassigned avatar: dashed circle
        return mark_safe(
            f'<div class="avatar avatar--unassigned {size_cls}" data-tooltip="Unassigned" title="Unassigned">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/></svg>'
            f'</div>'
        )

    name = getattr(user, "full_name", "") or getattr(user, "login_id", "") or str(user)
    parts = name.split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[1][0]).upper()
    elif parts:
        initials = parts[0][:2].upper()
    else:
        initials = "?"

    # Hash name to choose deterministic tint from palette
    hash_val = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    bg_color, fg_color = AVATAR_BG_PALETTE[hash_val % len(AVATAR_BG_PALETTE)]

    return mark_safe(
        f'<div class="avatar {size_cls}" style="background-color: {bg_color}; color: {fg_color};" title="{name}">'
        f'<span>{initials}</span>'
        f'</div>'
    )


@register.simple_tag
def sla_indicator(ticket):
    """
    SLA indicator (Section 4 & U-07):
    Active tickets: thin progress bar + hover info.
    Resolved / Closed tickets: muted check icon and 'Met'/'Closed' text (NO green bar!).
    """
    if not ticket:
        return ""

    if ticket.status in ["RESOLVED", "CLOSED"]:
        return mark_safe(
            '<span class="sla-done" title="Ticket resolved within SLA">'
            '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>'
            '<span>Completed</span>'
            '</span>'
        )

    now = timezone.now()
    if not ticket.due_at:
        return '<span class="sla-done">—</span>'

    diff = ticket.due_at - now
    hours_left = int(diff.total_seconds() / 3600)
    is_overdue = ticket.is_overdue or hours_left < 0

    if is_overdue:
        bar_cls = "red"
        label = f"Overdue {abs(hours_left)}h" if abs(hours_left) < 48 else f"Overdue {abs(hours_left)//24}d"
    elif hours_left <= 4:
        bar_cls = "amber"
        label = f"Due in {hours_left}h"
    else:
        bar_cls = "green"
        label = f"Due in {hours_left}h"

    return mark_safe(
        f'<div class="sla-bar-container" data-tooltip="{label}" title="{label}">'
        f'<div class="sla-bar sla-bar--{bar_cls}"></div>'
        f'</div>'
    )


@register.simple_tag
def kanban_time_copy(ticket):
    """
    Kanban due/resolved copy (Fix B-07):
    Active: 'Due in 3h', 'Due now', 'Overdue 2d'.
    Resolved: 'Resolved 2d ago', no countdown.
    """
    if not ticket:
        return ""

    now = timezone.now()
    if ticket.status in ["RESOLVED", "CLOSED"]:
        ref_time = ticket.resolved_at or ticket.closed_at or ticket.updated_at
        diff = now - ref_time if ref_time else None
        if diff:
            hours = int(diff.total_seconds() / 3600)
            if hours < 1:
                return "Resolved just now"
            elif hours < 24:
                return f"Resolved {hours}h ago"
            else:
                return f"Resolved {hours // 24}d ago"
        return "Resolved"

    if not ticket.due_at:
        return ""

    diff = ticket.due_at - now
    total_sec = int(diff.total_seconds())

    if total_sec < 0 or ticket.is_overdue:
        abs_h = abs(total_sec) // 3600
        if abs_h < 24:
            return f"Overdue {abs_h}h"
        return f"Overdue {abs_h // 24}d"

    hours = total_sec // 3600
    if hours < 1:
        return "Due now"
    if hours < 24:
        return f"Due in {hours}h"
    return f"Due in {hours // 24}d"


@register.simple_tag
def category_chip(category):
    """Renders a neat category chip with icon."""
    if not category:
        return ""
    icon_html = f'<i data-lucide="{category.icon}" style="width: 12px; height: 12px;"></i> ' if getattr(category, "icon", None) else ""
    return mark_safe(
        f'<span class="category-chip" style="display: inline-flex; align-items: center; gap: 4px; font-size: var(--fs-xs); color: var(--text-secondary); background: var(--bg-subtle); padding: 2px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border);">'
        f'{icon_html}{category.name}'
        f'</span>'
    )

