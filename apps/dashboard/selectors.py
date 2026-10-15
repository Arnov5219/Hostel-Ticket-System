from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel
from apps.tickets.models import Status, Ticket


def get_kpis(user):
    """Computes summary metrics scoped to user's permissions."""
    qs = Ticket.objects.visible_to(user)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_month = qs.filter(created_at__gte=month_start).count()
    resolved_count = qs.filter(status__in=[Status.RESOLVED, Status.CLOSED]).count()
    open_count = qs.filter(
        status__in=[Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    ).count()
    overdue_count = qs.filter(
        status__in=[Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD],
        due_at__lt=now,
    ).count()

    return {
        "total_month": total_month,
        "resolved_count": resolved_count,
        "open_count": open_count,
        "overdue_count": overdue_count,
    }


def get_hosteler_kpis(user):
    """KPIs for hosteler home view."""
    qs = Ticket.objects.filter(reporter=user)
    my_open = qs.filter(
        status__in=[Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    ).count()
    my_resolved = qs.filter(status=Status.RESOLVED).count()
    my_closed = qs.filter(status=Status.CLOSED).count()

    return {
        "my_open": my_open,
        "my_resolved": my_resolved,
        "my_closed": my_closed,
    }


def get_category_data(user):
    """Returns ticket counts by category for Chart.js."""
    qs = Ticket.objects.visible_to(user)
    categories = qs.values("category__name").annotate(count=Count("id")).order_by("-count")[:8]

    labels = [c["category__name"] or "Uncategorized" for c in categories]
    counts = [c["count"] for c in categories]
    return {"labels": labels, "data": counts}


def get_trend_data(user):
    """Returns monthly ticket trends for Chart.js."""
    qs = Ticket.objects.visible_to(user)
    now = timezone.now()
    months = []
    created_counts = []
    resolved_counts = []
    overdue_counts = []

    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i * 30)
        start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (start + timedelta(days=32)).replace(day=1)
        month_label = start.strftime("%b %Y")

        months.append(month_label)
        c_count = qs.filter(created_at__gte=start, created_at__lt=next_month).count()
        r_count = qs.filter(
            status__in=[Status.RESOLVED, Status.CLOSED],
            resolved_at__gte=start,
            resolved_at__lt=next_month,
        ).count()
        o_count = qs.filter(
            due_at__gte=start,
            due_at__lt=next_month,
            is_overdue=True,
        ).count()

        created_counts.append(c_count)
        resolved_counts.append(r_count)
        overdue_counts.append(o_count)

    return {
        "labels": months,
        "created": created_counts,
        "resolved": resolved_counts,
        "overdue": overdue_counts,
    }


def get_resolution_time_data(user):
    """Computes average resolution hours per hostel."""
    hostels = Hostel.objects.filter(is_active=True)
    labels = []
    avg_hours = []

    for h in hostels:
        tickets = Ticket.objects.visible_to(user).filter(
            hostel=h,
            status__in=[Status.RESOLVED, Status.CLOSED],
            resolved_at__isnull=False,
        )
        if tickets.exists():
            diffs = [(t.resolved_at - t.created_at).total_seconds() / 3600 for t in tickets]
            avg = round(sum(diffs) / len(diffs), 1)
        else:
            avg = 0
        labels.append(h.name)
        avg_hours.append(avg)

    return {"labels": labels, "data": avg_hours}


def get_escalation_breakdown(user):
    """Count of active tickets per level."""
    qs = Ticket.objects.visible_to(user).filter(
        status__in=[Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    )
    return {
        "L1": qs.filter(current_level=1).count(),
        "L2": qs.filter(current_level=2).count(),
        "L3": qs.filter(current_level=3).count(),
        "L4": qs.filter(current_level=4).count(),
    }


def get_top_staff(user, limit=5):
    """Top staff members by resolved tickets."""
    return (
        User.objects.filter(
            role__in=[Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN],
            is_active=True,
        )
        .annotate(
            resolved_count=Count(
                "assigned_tickets",
                filter=Q(assigned_tickets__status__in=[Status.RESOLVED, Status.CLOSED]),
            )
        )
        .order_by("-resolved_count")[:limit]
    )


def get_overdue_tickets(user, limit=5):
    """Fetches critical overdue tickets for compact dashboard table."""
    now = timezone.now()
    return (
        Ticket.objects.visible_to(user)
        .filter(
            status__in=[Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD],
            due_at__lt=now,
        )
        .select_related("hostel", "category", "assigned_to")
        .order_by("due_at")[:limit]
    )




def get_latest_announcements_staff(user, limit=3):
    """Returns latest announcements with read stats for staff dashboard."""
    from apps.announcements.models import Announcement, AnnouncementRead
    from apps.announcements.services import audience_users
    qs = Announcement.objects.all().order_by("-published_at", "-created_at")
    if getattr(user, "is_warden", False) and user.hostel:
        qs = qs.filter(Q(all_hostels=True) | Q(hostels=user.hostel))
    items = []
    for ann in qs[:limit]:
        total = audience_users(ann).count()
        read = AnnouncementRead.objects.filter(announcement=ann).count()
        items.append({
            "announcement": ann,
            "total": total,
            "read": read,
            "read_pct": int((read / total) * 100) if total > 0 else 0,
        })
    return items

