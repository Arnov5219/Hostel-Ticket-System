from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.core.permissions import (
    can_add_internal_note,
    can_view_ticket,
)
from apps.tickets.forms import CommentForm
from apps.tickets.models import (
    CommentScope,
    Status,
    Ticket,
)
from apps.tickets.services.deletion import can_delete


@login_required
def ticket_detail(request, ticket_no):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "category",
            "hostel",
            "room",
            "reporter",
            "assigned_to",
        ).prefetch_related(
            "attachments",
            "tags",
            "followers",
            "activities__actor",
            "comments__author",
        ),
        ticket_no=ticket_no,
    )

    if not can_view_ticket(request.user, ticket):
        raise PermissionDenied("You do not have permission to view this ticket.")

    # Comments visibility: internal notes hidden from hostelers
    comments_qs = ticket.comments.all()
    if request.user.is_hosteler:
        comments_qs = comments_qs.exclude(scope=CommentScope.INTERNAL).filter(is_hidden=False)

    # SLA time calculation
    sla_percentage = 0
    sla_status = "green"
    time_left_str = "No deadline"

    if ticket.due_at:
        now = timezone.now()
        total_seconds = (ticket.due_at - ticket.created_at).total_seconds()
        elapsed_seconds = (now - ticket.created_at).total_seconds()

        if total_seconds > 0:
            pct = min(100, max(0, int((elapsed_seconds / total_seconds) * 100)))
            sla_percentage = pct

        if now > ticket.due_at:
            sla_status = "red"
            overdue_diff = now - ticket.due_at
            hours = int(overdue_diff.total_seconds() // 3600)
            time_left_str = f"Overdue by {hours}h"
        else:
            remaining = ticket.due_at - now
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            time_left_str = f"{hours}h {mins}m left"
            if sla_percentage >= 80:
                sla_status = "red"
            elif sla_percentage >= 50:
                sla_status = "amber"
            else:
                sla_status = "green"

    # Eligible assignees for reassigning
    eligible_staff = User.objects.filter(
        role__in=[Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN],
        is_active=True,
    )

    # Activity timeline: legacy actions excluded automatically by manager
    activities_qs = ticket.activities.all()
    if request.user.is_hosteler:
        activities_qs = activities_qs.exclude(note__icontains="internal")

    user_can_delete, delete_block_reason = can_delete(request.user, ticket)

    context = {
        "ticket": ticket,
        "comments": comments_qs,
        "activities": activities_qs,
        "comment_form": CommentForm(),
        "can_add_note": can_add_internal_note(request.user),
        "is_following": ticket.followers.filter(id=request.user.id).exists(),
        "sla_percentage": sla_percentage,
        "sla_status": sla_status,
        "time_left_str": time_left_str,
        "current_section": "tickets",
        "eligible_staff": eligible_staff,
        "statuses": Status.choices,
        "user_can_delete": user_can_delete,
        "delete_block_reason": delete_block_reason,
    }
    return render(request, "tickets/detail.html", context)
