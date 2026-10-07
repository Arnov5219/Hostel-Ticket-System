from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.core.permissions import can_view_kanban
from apps.tickets.models import Status, Ticket


@login_required
def ticket_kanban(request):
    if not can_view_kanban(request.user):
        raise PermissionDenied("Hostelers do not have access to the Kanban board.")

    tickets = Ticket.objects.visible_to(request.user).select_related(
        "category", "hostel", "assigned_to"
    )

    columns = [
        {"status": Status.OPEN, "title": "Open", "tickets": tickets.filter(status=Status.OPEN)},
        {
            "status": Status.ASSIGNED,
            "title": "Assigned",
            "tickets": tickets.filter(status=Status.ASSIGNED),
        },
        {
            "status": Status.IN_PROGRESS,
            "title": "In Progress",
            "tickets": tickets.filter(status=Status.IN_PROGRESS),
        },
        {
            "status": Status.ON_HOLD,
            "title": "On Hold",
            "tickets": tickets.filter(status=Status.ON_HOLD),
        },
        {
            "status": Status.RESOLVED,
            "title": "Resolved",
            "tickets": tickets.filter(status=Status.RESOLVED),
        },
    ]

    return render(
        request,
        "tickets/kanban.html",
        {
            "columns": columns,
            "is_kanban": True,
            "current_section": "tickets",
        },
    )
