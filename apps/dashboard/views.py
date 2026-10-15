from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.accounts.models import Role, User
from apps.announcements.services import unread_urgent_announcements, visible_to
from apps.core.permissions import Capability
from apps.dashboard.selectors import (
    get_category_data,
    get_escalation_breakdown,
    get_hosteler_kpis,
    get_kpis,
    get_latest_announcements_staff,
    get_overdue_tickets,
    get_resolution_time_data,
    get_top_staff,
    get_trend_data,
)
from apps.hostels.models import Hostel
from apps.tickets.models import Ticket


@login_required
def dashboard_index(request):
    user = request.user
    if user.is_hosteler:
        # Hosteler Home
        kpis = get_hosteler_kpis(user)
        recent_tickets = (
            Ticket.objects.filter(reporter=user)
            .select_related("category", "hostel", "assigned_to")
            .order_by("-created_at")[:5]
        )

        urgent_announcements = unread_urgent_announcements(user)
        urgent_banner = urgent_announcements.first()
        urgent_more_count = max(0, urgent_announcements.count() - 1)

        announcements = visible_to(user)[:4]

        return render(
            request,
            "dashboard/hosteler.html",
            {
                "kpis": kpis,
                "recent_tickets": recent_tickets,
                "urgent_banner": urgent_banner,
                "urgent_more_count": urgent_more_count,
                "announcements": announcements,
                "current_section": "dashboard",
            },
        )

    # Staff Dashboard
    kpis = get_kpis(user)
    escalations = get_escalation_breakdown(user)
    top_staff = get_top_staff(user)
    overdue_tickets = get_overdue_tickets(user)
    latest_announcements = get_latest_announcements_staff(user)

    hostels_without_staff = []
    no_dean_warning = False
    if user.is_admin:
        no_dean_warning = not User.objects.filter(role=Role.DEAN, is_active=True).exists()

    if user.can(Capability.MANAGE_HOSTELS):
        hostels_without_staff = Hostel.objects.filter(is_active=True, responsible_staff__isnull=True)

    context = {
        "kpis": kpis,
        "escalations": escalations,
        "top_staff": top_staff,
        "overdue_tickets": overdue_tickets,
        "latest_announcements": latest_announcements,
        "hostels_without_staff": hostels_without_staff,
        "no_dean_warning": no_dean_warning,
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
