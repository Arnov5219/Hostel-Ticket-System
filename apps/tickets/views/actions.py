from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect

from apps.accounts.models import Role, User
from apps.core.permissions import (
    Capability,
    can_reassign_or_escalate,
    can_view_ticket,
    has_capability,
)
from apps.notifications.services import notify_ticket_reassigned
from apps.tickets.models import (
    ActivityAction,
    Status,
    Ticket,
    TicketActivity,
)
from apps.tickets.services.escalation import escalate as service_escalate
from apps.tickets.services.status import change_status as service_change_status


@login_required
def add_comment(request, ticket_no):
    """
    Comment submission endpoint - disabled per cleanup plan.
    Ticket comments/discussions have been permanently removed in favor of the activity timeline.
    """
    raise PermissionDenied("Ticket comments have been disabled.")


AUTHORITY_ROLES = [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.DEAN, Role.ADMIN]
ALLOWED_STATUS_INPUTS = {Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD, Status.RESOLVED, Status.CLOSED, Status.REJECTED}


@login_required
def change_status(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    user_role = getattr(request.user, "role", None)

    # Authority roles can update ticket status; hostellers cannot unless confirming/reopening their own ticket
    is_authority = user_role in AUTHORITY_ROLES or request.user.is_superuser
    is_reporter = request.user == ticket.reporter and user_role == Role.HOSTELER

    if not is_authority and not is_reporter:
        if request.headers.get("HX-Request") == "true" or request.headers.get("Accept") == "application/json":
            return JsonResponse({"error": "You do not have permission to change ticket status."}, status=403)
        raise PermissionDenied("You do not have permission to change ticket status.")

    if request.method == "POST":
        new_status = request.POST.get("status")
        note = request.POST.get("note", "").strip()

        # Reporter restriction: can only confirm close (when RESOLVED) or reopen (when RESOLVED/CLOSED)
        if is_reporter and not is_authority:
            if new_status == Status.CLOSED and ticket.status == Status.RESOLVED:
                pass  # Permitted
            elif new_status == Status.IN_PROGRESS and ticket.status in [Status.RESOLVED, Status.CLOSED]:
                pass  # Permitted
            else:
                if request.headers.get("HX-Request") == "true":
                    return JsonResponse({"error": "Hostellers cannot change ticket status."}, status=403)
                raise PermissionDenied("Hostellers cannot change ticket status.")

        # Note requirement validation for authority status changes:
        is_ajax = (
            request.headers.get("HX-Request") == "true"
            or request.headers.get("x-requested-with", "").lower() == "xmlhttprequest"
            or "application/json" in request.headers.get("accept", "").lower()
        )

        # Note requirement: status note is optional per requirements


        try:
            service_change_status(ticket, new_status, actor=request.user, note=note)
            if request.headers.get("HX-Request") == "true":
                messages.success(request, f"Ticket status changed to {new_status}.")
                # Return partials or signal refresh
                response = render(request, "tickets/_status_update_panel.html", {
                    "ticket": ticket,
                    "user_can_change_status": is_authority,
                    "success_message": f"Status updated to {ticket.get_status_display()}.",
                })
                response["HX-Trigger"] = "ticketStatusUpdated"
                return response
            messages.success(request, f"Ticket status changed to {new_status}.")
        except ValidationError as e:
            err_msg = str(e.message if hasattr(e, "message") else e)
            if request.headers.get("HX-Request") == "true":
                return render(request, "tickets/_status_update_panel.html", {
                    "ticket": ticket,
                    "user_can_change_status": is_authority,
                    "error_message": err_msg,
                }, status=400)
            messages.error(request, err_msg)

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def move_ticket(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    user_role = getattr(request.user, "role", None)
    if user_role not in AUTHORITY_ROLES and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to change ticket status.")

    if request.method == "POST":
        new_status = request.POST.get("status")
        try:
            service_change_status(
                ticket, new_status, actor=request.user, note="Moved on Kanban board"
            )
            return JsonResponse(
                {"success": True, "ticket_no": ticket.ticket_no, "status": new_status}
            )
        except ValidationError as e:
            err_msg = e.message if hasattr(e, "message") else str(e)
            return JsonResponse({"error": err_msg}, status=400)
    return JsonResponse({"error": "POST method required"}, status=405)


@login_required
def reassign(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if not can_reassign_or_escalate(request.user, ticket):
        raise PermissionDenied("You do not have permission to reassign this ticket.")

    if request.method == "POST":
        assignee_id = request.POST.get("assignee_id")
        note = request.POST.get("note", "").strip()
        new_assignee = get_object_or_404(User, id=assignee_id)

        old_assignee_name = (
            ticket.assigned_to.full_name or ticket.assigned_to.login_id
            if ticket.assigned_to
            else "Unassigned"
        )
        new_assignee_name = new_assignee.full_name or new_assignee.login_id

        old_assignee = ticket.assigned_to
        ticket.assigned_to = new_assignee
        ticket.save()

        TicketActivity.objects.create(
            ticket=ticket,
            actor=request.user,
            action=ActivityAction.REASSIGNED,
            from_value=old_assignee_name,
            to_value=new_assignee_name,
            note=note,
        )

        notify_ticket_reassigned(ticket, old_assignee, new_assignee, request.user)

        messages.success(request, f"Ticket reassigned to {new_assignee_name}.")

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def manual_escalate(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if not has_capability(request.user, Capability.ESCALATE) or not can_view_ticket(request.user, ticket):
        raise PermissionDenied("You do not have permission to escalate this ticket.")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        service_escalate(ticket, actor=request.user, reason=reason)
        messages.success(request, f"Ticket escalated to Level {ticket.current_level}.")

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def toggle_follow(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if not can_view_ticket(request.user, ticket):
        raise PermissionDenied()

    if request.user in ticket.followers.all():
        ticket.followers.remove(request.user)
        following = False
    else:
        ticket.followers.add(request.user)
        following = True

    if request.headers.get("HX-Request") == "true":
        icon_color = "var(--st-open-fg)" if following else "var(--text-muted)"
        fill_attr = 'fill="currentColor"' if following else 'fill="none"'
        return HttpResponse(
            f'<button type="button" class="btn btn-ghost btn-sm" hx-post="/tickets/{ticket.ticket_no}/follow/" hx-swap="outerHTML" style="color: {icon_color};">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" {fill_attr} stroke="currentColor" stroke-width="2"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>'
            f"<span>{ticket.followers.count()}</span></button>"
        )

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def rate_ticket(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if request.user != ticket.reporter:
        raise PermissionDenied("Only the ticket reporter can rate resolution quality.")

    if request.method == "POST":
        rating = request.POST.get("rating")
        if rating and rating.isdigit() and 1 <= int(rating) <= 5:
            ticket.rating = int(rating)
            ticket.save()
            messages.success(request, "Thank you for your feedback rating!")

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)
