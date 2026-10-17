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
        {
            "status": Status.OPEN,
            "title": "Open",
            "desc": "Newly reported issues awaiting triage",
            "tickets": tickets.filter(status=Status.OPEN),
        },
        {
            "status": Status.ASSIGNED,
            "title": "Assigned",
            "desc": "Allocated to maintenance personnel",
            "tickets": tickets.filter(status=Status.ASSIGNED),
        },
        {
            "status": Status.IN_PROGRESS,
            "title": "In Progress",
            "desc": "Actively being serviced by technicians",
            "tickets": tickets.filter(status=Status.IN_PROGRESS),
        },
        {
            "status": Status.ON_HOLD,
            "title": "On Hold",
            "desc": "Awaiting parts, vendor or clearance",
            "tickets": tickets.filter(status=Status.ON_HOLD),
        },
        {
            "status": Status.RESOLVED,
            "title": "Resolved",
            "desc": "Work completed and verified",
            "tickets": tickets.filter(status=Status.RESOLVED),
        },
    ]

    return render(
        request,
        "tickets/kanban.html",
        {
            "columns": columns,
            "kanban_statuses": [(col["status"], col["title"]) for col in columns],
            "is_kanban": True,
            "current_section": "tickets",
        },
    )
