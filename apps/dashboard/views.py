from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from django.core.paginator import Paginator
from apps.announcements.services import unread_urgent_announcements, visible_to
from apps.dashboard.selectors import (
    get_category_data,
    get_escalation_breakdown,
    get_hosteler_kpis,
    get_kpis,
    get_latest_announcements_staff,
    get_most_reported_issues,
    get_overdue_tickets,
    get_resolution_time_data,
    get_top_staff,
    get_trend_data,
)
from apps.tickets.models import Category, Ticket, TicketVisibility
from apps.tickets.services.community import feed_queryset


@login_required
def dashboard_index(request):
    user = request.user
    if user.is_hosteler:
        # Hosteler Home
        kpis = get_hosteler_kpis(user)
        recent_tickets = (
            Ticket.objects.filter(reporter=user)
            .select_related("category", "hostel", "assigned_to")
            .order_by("-created_at")[:3]
        )

        urgent_announcements = unread_urgent_announcements(user)
        urgent_banner = urgent_announcements.first()
        urgent_more_count = max(0, urgent_announcements.count() - 1)

        announcements = visible_to(user)[:4]

        trending_tickets = (
            Ticket.objects.filter(
                hostel=user.hostel,
                visibility=TicketVisibility.HOSTEL,
                community_hidden=False,
                repost_count__gt=0,
            )
            .select_related("category")
            .order_by("-repost_count")[:3]
        ) if user.hostel else Ticket.objects.none()

        feed_qs = feed_queryset(user)
        paginator = Paginator(feed_qs, 10)
        page_obj = paginator.get_page(1)
        categories = Category.objects.filter(is_active=True, allow_community=True)

        return render(
            request,
            "dashboard/hosteler.html",
            {
                "kpis": kpis,
                "recent_tickets": recent_tickets,
                "urgent_banner": urgent_banner,
                "urgent_more_count": urgent_more_count,
                "announcements": announcements,
                "trending_tickets": trending_tickets,
                "page_obj": page_obj,
                "tickets": page_obj.object_list,
                "categories": categories,
                "current_section": "dashboard",
            },
        )

    # Staff Dashboard
    kpis = get_kpis(user)
    escalations = get_escalation_breakdown(user)
    top_staff = get_top_staff(user)
    overdue_tickets = get_overdue_tickets(user)
    most_reported = get_most_reported_issues(user)
    latest_announcements = get_latest_announcements_staff(user)

    from django.conf import settings
    from apps.core.permissions import Capability
    from apps.hostels.models import Hostel

    hostels_without_staff = []
    if user.can(Capability.MANAGE_HOSTELS):
        hostels_without_staff = Hostel.objects.filter(is_active=True, responsible_staff__isnull=True)

    context = {
        "kpis": kpis,
        "escalations": escalations,
        "top_staff": top_staff,
        "overdue_tickets": overdue_tickets,
        "most_reported_issues": most_reported,
        "latest_announcements": latest_announcements,
        "hostels_without_staff": hostels_without_staff,
        "show_affected_count": getattr(settings, "SHOW_AFFECTED_COUNT_TO_STAFF", True),
        "current_section": "dashboard",
    }
    return render(request, "dashboard/staff.html", context)


# JSON Chart API Endpoints
@login_required
def api_summary(request):
    return JsonResponse(get_kpis(request.user))


@login_required
def api_by_category(request):
    return JsonResponse(get_category_data(request.user))


@login_required
def api_trend(request):
    return JsonResponse(get_trend_data(request.user))


@login_required
def api_resolution_time(request):
    return JsonResponse(get_resolution_time_data(request.user))
