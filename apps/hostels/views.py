from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.permissions import can_manage_config
from apps.hostels.forms import BlockForm, HostelForm, RoomForm
from apps.hostels.models import Block, Hostel, Room


@login_required
def manage_hostels(request):
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage hostel configurations.")

    hostels = Hostel.objects.all().prefetch_related("blocks__rooms")
    form = HostelForm()

    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "create":
            form = HostelForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Hostel added successfully.")
                return redirect("hostels:manage_hostels")
        elif action == "update":
            hostel_id = request.POST.get("hostel_id")
            hostel = get_object_or_404(Hostel, id=hostel_id)
            form = HostelForm(request.POST, instance=hostel)
            if form.is_valid():
                form.save()
                messages.success(request, "Hostel updated successfully.")
                return redirect("hostels:manage_hostels")

    return render(
        request,
        "hostels/manage_hostels.html",
        {
            "hostels": hostels,
            "form": form,
            "current_section": "manage_hostels",
        },
    )


@login_required
def manage_blocks(request):
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage hostel blocks.")

    blocks = Block.objects.select_related("hostel").all()
    form = BlockForm()

    if request.method == "POST":
        form = BlockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Block added successfully.")
            return redirect("hostels:manage_blocks")

    return render(
        request,
        "hostels/manage_blocks.html",
        {
            "blocks": blocks,
            "form": form,
            "current_section": "manage_hostels",
        },
    )


@login_required
def manage_rooms(request):
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage rooms.")

    rooms = Room.objects.select_related("block__hostel").all()[:100]
    form = RoomForm()

    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Room added successfully.")
            return redirect("hostels:manage_rooms")

    return render(
        request,
        "hostels/manage_rooms.html",
        {
            "rooms": rooms,
            "form": form,
            "current_section": "manage_hostels",
        },
    )
