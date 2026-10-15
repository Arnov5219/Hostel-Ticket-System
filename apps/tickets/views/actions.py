from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import User
from apps.core.permissions import can_add_internal_note, can_reassign_or_escalate, can_view_ticket
from apps.notifications.models import Notification
from apps.tickets.forms import CommentForm
from apps.tickets.models import (
    ActivityAction,
    CommentScope,
    Ticket,
    TicketActivity,
)
from apps.tickets.services.escalation import escalate as service_escalate
from apps.tickets.services.status import change_status as service_change_status


@login_required
def add_comment(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if not can_view_ticket(request.user, ticket):
        raise PermissionDenied("You cannot comment on this ticket.")

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user

            if comment.is_internal and not can_add_internal_note(request.user):
                comment.is_internal = False

            comment.save()

            note_type = "Internal Note" if comment.is_internal else "Public Comment"
            act_note = (
                "Added an internal staff note"
                if comment.is_internal
                else f"Added a comment: {comment.body[:60]}..."
            )
            TicketActivity.objects.create(
                ticket=ticket,
                actor=request.user,
                action=ActivityAction.COMMENTED,
                note=act_note,
            )

            recipient = ticket.assigned_to if request.user == ticket.reporter else ticket.reporter
            if recipient and not comment.is_internal:
                Notification.objects.create(
                    recipient=recipient,
                    ticket=ticket,
                    verb="New Comment",
                    message=f"{request.user.full_name or request.user.login_id} commented on {ticket.ticket_no}.",
                )

            if request.headers.get("HX-Request") == "true":
                comments = ticket.comments.all()
                if request.user.is_hosteler:
                    comments = comments.exclude(scope=CommentScope.INTERNAL).filter(is_hidden=False)
                activities = ticket.activities.all()
                if request.user.is_hosteler:
                    activities = activities.exclude(note__icontains="internal")
                return render(
                    request,
                    "tickets/_activity.html",
                    {
                        "ticket": ticket,
                        "comments": comments,
                        "activities": activities,
                        "can_add_note": can_add_internal_note(request.user),
                    },
                )

            messages.success(request, f"{note_type} posted successfully.")
            return redirect("tickets:detail", ticket_no=ticket.ticket_no)

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def change_status(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if request.method == "POST":
        new_status = request.POST.get("status")
        note = request.POST.get("note", "").strip()
        try:
            service_change_status(ticket, new_status, actor=request.user, note=note)
            messages.success(request, f"Ticket status changed to {new_status}.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def move_ticket(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
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

        Notification.objects.create(
            recipient=new_assignee,
            ticket=ticket,
            verb="Ticket Reassigned",
            message=f"Ticket {ticket.ticket_no} has been reassigned to you by {request.user.full_name or request.user.login_id}.",
        )

        messages.success(request, f"Ticket reassigned to {new_assignee_name}.")

    return redirect("tickets:detail", ticket_no=ticket.ticket_no)


@login_required
def manual_escalate(request, ticket_no):
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    if not can_reassign_or_escalate(request.user, ticket):
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
