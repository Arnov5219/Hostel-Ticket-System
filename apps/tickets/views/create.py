from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from apps.core.permissions import can_raise_ticket
from apps.tickets.forms import TicketCreateForm
from apps.tickets.models import ActivityAction, TicketActivity, TicketAttachment
from apps.tickets.services.numbering import generate_ticket_number
from apps.tickets.services.routing import assign_initial


@login_required
def ticket_create(request):
    if not can_raise_ticket(request.user):
        raise PermissionDenied("You do not have permission to raise tickets.")

    if request.method == "POST":
        form = TicketCreateForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                images = form.clean_images(request.FILES)
            except ValidationError as e:
                form.add_error(None, e.message)
                return render(request, "tickets/create.html", {"form": form})

            ticket = form.save(commit=False)
            ticket.ticket_no = generate_ticket_number()
            ticket.reporter = request.user
            ticket.save()

            # Save uploaded attachments
            for img in images:
                TicketAttachment.objects.create(ticket=ticket, file=img, uploaded_by=request.user)

            # Log CREATED activity
            TicketActivity.objects.create(
                ticket=ticket,
                actor=request.user,
                action=ActivityAction.CREATED,
                from_value="",
                to_value="OPEN",
                note="Ticket raised by hosteler",
            )

            # Route and assign initial staff member
            assign_initial(ticket, actor=request.user)

            messages.success(
                request,
                f"Ticket {ticket.ticket_no} created successfully and assigned to staff.",
            )
            return redirect("tickets:detail", ticket_no=ticket.ticket_no)
    else:
        form = TicketCreateForm(user=request.user)

    return render(
        request,
        "tickets/create.html",
        {"form": form, "current_section": "tickets"},
    )
