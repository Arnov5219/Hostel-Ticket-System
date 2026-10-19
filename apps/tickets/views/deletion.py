from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.permissions import Capability, has_capability
from apps.hostels.models import Hostel
from apps.tickets.models import Ticket
from apps.tickets.services.deletion import (
    can_delete,
    generate_undo_token,
    restore,
    soft_delete,
    undo_delete,
)


@login_required
def ticket_delete_view(request, ticket_no):
    """
    POST /tickets/<ticket_no>/delete/
    Soft-deletes an eligible ticket per hosteler / staff rules.
    """
    if request.method != "POST":
        return redirect("tickets:detail", ticket_no=ticket_no)

    # Use all_objects to find ticket then check can_delete
    ticket = get_object_or_404(Ticket.all_objects, ticket_no=ticket_no)
    allowed, block_reason = can_delete(request.user, ticket)
    if not allowed:
        messages.error(request, block_reason)
        return redirect("tickets:detail", ticket_no=ticket_no)

    reason = request.POST.get("reason", "")
    try:
        soft_delete(ticket, request.user, reason=reason)
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))
        return redirect("tickets:detail", ticket_no=ticket_no)

    undo_token = generate_undo_token(ticket.ticket_no, request.user.id)

    if request.headers.get("HX-Request") == "true":
        is_detail = request.POST.get("from_detail") == "true" or f"/{ticket_no}/" in request.META.get("HTTP_REFERER", "")
        if is_detail:
            if request.user.is_hosteler:
                request.session["undo_delete"] = {
                    "ticket_no": ticket.ticket_no,
                    "token": undo_token,
                }
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("tickets:list")
            return response

        if request.user.is_hosteler:
            # Return 8-second undo toast partial with out-of-band swap
            return render(
                request,
                "tickets/partials/_delete_toast.html",
                {"ticket": ticket, "undo_token": undo_token, "is_oob": True},
            )
        else:
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("tickets:list")
            return response

    if request.user.is_hosteler:
        request.session["undo_delete"] = {
            "ticket_no": ticket.ticket_no,
            "token": undo_token,
        }
    messages.success(request, f"Ticket {ticket.ticket_no} was successfully deleted.")
    return redirect("tickets:list")


@login_required
def ticket_undo_delete_view(request, ticket_no):
    """
    POST /tickets/<ticket_no>/undo-delete/
    Restores ticket within 8-second window using cryptographic token.
    """
    token = request.POST.get("token") or request.GET.get("token")
    if not token:
        messages.error(request, "Missing undo token.")
        return redirect("tickets:list")

    try:
        undo_delete(ticket_no, request.user, token)
        messages.success(request, f"Ticket {ticket_no} restored successfully.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))
        return redirect("tickets:list")

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("tickets:detail", kwargs={"ticket_no": ticket_no})
        return response

    return redirect("tickets:detail", ticket_no=ticket_no)


@login_required
def ticket_restore_view(request, ticket_no):
    """
    POST /tickets/<ticket_no>/restore/
    Restores soft-deleted ticket (Admin only).
    """
    if not has_capability(request.user, Capability.RESTORE_TICKET):
        raise PermissionDenied("Only administrators can restore deleted tickets.")

    if request.method != "POST":
        return redirect("tickets:trash")

    ticket = get_object_or_404(Ticket.all_objects, ticket_no=ticket_no)
    try:
        restore(ticket, request.user)
        messages.success(request, f"Ticket {ticket.ticket_no} restored successfully.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("tickets:trash")
        return response

    return redirect("tickets:trash")


@login_required
def trash_list_view(request):
    """
    GET /manage/trash/ (or /tickets/trash/)
    Displays soft-deleted tickets for Admin only (VIEW_TRASH_ALL).
    """
    if not has_capability(request.user, Capability.VIEW_TRASH_ALL):
        raise PermissionDenied("You do not have permission to view the trash.")

    qs = Ticket.all_objects.filter(is_deleted=True)

    deleted_tickets = (
        qs.select_related("hostel", "category", "reporter", "deleted_by")
        .order_by("-deleted_at")
    )

    hostels = Hostel.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "tickets/trash.html",
        {
            "tickets": deleted_tickets,
            "hostels": hostels,
            "can_restore": True,
            "current_section": "trash",
        },
    )
