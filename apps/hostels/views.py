from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role, User
from apps.core.permissions import Capability, can_manage_config
from apps.hostels.forms import HostelForm
from apps.hostels.models import Hostel, Room
from apps.hostels.services import (
    assign_staff_to_hostel,
    change_hostel_responsible_staff,
    create_hostel,
    deactivate_hostel,
    deactivate_staff,
    generate_rooms,
    natural_sort_key,
    room_options,
    update_hostel,
)
from apps.tickets.models import Status


@login_required
def manage_hostels(request):
    """
    Hostel Management screen.
    Displays: Hostel Name, Code, Type, Responsible Staff, Status, Actions.
    Admin can Add, Edit, Activate/Deactivate, and Change Responsible Staff.
    """
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage hostel configurations.")

    hostels = (
        Hostel.objects.select_related("responsible_staff")
        .annotate(
            hosteler_count=Count(
                "users",
                filter=Q(users__role=Role.HOSTELER, users__is_active=True),
            )
        )
        .all()
    )
    # Annotate or calculate active ticket counts
    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    for h in hostels:
        h.active_ticket_count = h.tickets.filter(status__in=active_statuses).count()

    form = HostelForm()

    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "create":
            form = HostelForm(request.POST)
            if form.is_valid():
                try:
                    create_hostel(
                        name=form.cleaned_data["name"],
                        code=form.cleaned_data["code"],
                        gender_type=form.cleaned_data["gender_type"],
                        address=form.cleaned_data.get("address", ""),
                        responsible_staff=form.cleaned_data.get("responsible_staff"),
                        is_active=form.cleaned_data.get("is_active", True),
                    )
                    messages.success(request, f"Hostel '{form.cleaned_data['name']}' added successfully.")
                    return redirect("hostels:manage_hostels")
                except ValidationError as e:
                    messages.error(request, str(e.message if hasattr(e, "message") else e))
            else:
                messages.error(request, "Please correct the errors in the form.")

        elif action == "update":
            hostel_id = request.POST.get("hostel_id")
            hostel = get_object_or_404(Hostel, id=hostel_id)
            form = HostelForm(request.POST, instance=hostel)
            if form.is_valid():
                try:
                    update_hostel(
                        hostel,
                        name=form.cleaned_data["name"],
                        code=form.cleaned_data["code"],
                        gender_type=form.cleaned_data["gender_type"],
                        address=form.cleaned_data.get("address", ""),
                        responsible_staff=form.cleaned_data.get("responsible_staff"),
                        is_active=form.cleaned_data.get("is_active", True),
                    )
                    messages.success(request, f"Hostel '{hostel.name}' updated successfully.")
                    return redirect("hostels:manage_hostels")
                except ValidationError as e:
                    messages.error(request, str(e.message if hasattr(e, "message") else e))
            else:
                messages.error(request, "Please correct the errors in the form.")

    available_caretakers = User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name")

    return render(
        request,
        "hostels/manage_hostels.html",
        {
            "hostels": hostels,
            "form": form,
            "available_caretakers": available_caretakers,
            "current_section": "manage_hostels",
        },
    )


@login_required
def manage_staff(request):
    """
    Dedicated Staff Management screen.
    Displays: Name, Role, Level, Assigned Hostel, Active Tickets, Status, Actions.
    Admin can change hostel assignment and activate/deactivate staff.
    """
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("Only administrators can manage staff.")

    staff_roles = [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.DEAN, Role.ADMIN]
    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]

    staff_members = (
        User.objects.filter(role__in=staff_roles)
        .select_related("hostel")
        .annotate(
            active_tickets=Count(
                "assigned_tickets",
                filter=Q(assigned_tickets__status__in=active_statuses),
            )
        )
        .order_by("escalation_level", "full_name", "login_id")
    )

    hostels = Hostel.objects.filter(is_active=True).order_by("name")
    available_caretakers = User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name")

    return render(
        request,
        "hostels/manage_staff.html",
        {
            "staff_members": staff_members,
            "hostels": hostels,
            "available_caretakers": available_caretakers,
            "current_section": "manage_staff",
        },
    )


@login_required
def manage_responsibility(request):
    """
    Dedicated Hostel Responsibility screen.
    Each hostel has one Level 1 responsible staff member.
    All ticket categories for that hostel route to this staff member.
    """
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage hostel responsibilities.")

    hostels = list(Hostel.objects.select_related("responsible_staff").all())
    hostels = sorted(hostels, key=natural_sort_key)

    wardens = User.objects.filter(role=Role.WARDEN, is_active=True, hostel__isnull=False).select_related("hostel")
    wardens_by_hostel = {w.hostel_id: w for w in wardens}

    for h in hostels:
        h.warden = wardens_by_hostel.get(h.id)

    available_caretakers = User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name")
    available_wardens = User.objects.filter(role=Role.WARDEN, is_active=True).order_by("full_name")

    return render(
        request,
        "hostels/manage_responsibility.html",
        {
            "hostels": hostels,
            "available_caretakers": available_caretakers,
            "available_wardens": available_wardens,
            "current_section": "manage_responsibility",
        },
    )


@login_required
def change_responsible_staff_view(request, hostel_id):
    """Action to change Level 1 responsible staff for a hostel."""
    if not can_manage_config(request.user):
        raise PermissionDenied()

    hostel = get_object_or_404(Hostel, id=hostel_id)
    if request.method == "POST":
        staff_id = request.POST.get("responsible_staff")
        staff = get_object_or_404(User, id=staff_id)
        try:
            change_hostel_responsible_staff(hostel, staff, actor=request.user)
            messages.success(
                request,
                f"Assigned {staff.full_name or staff.login_id} as Level 1 responsible staff for {hostel.name}."
            )
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_hostels"
    return redirect(next_url)


@login_required
def assign_staff_hostel_view(request, user_id):
    """Action to change a staff member's assigned hostel."""
    if not can_manage_config(request.user):
        raise PermissionDenied()

    staff = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        hostel_id = request.POST.get("hostel_id")
        hostel = get_object_or_404(Hostel, id=hostel_id) if hostel_id else None
        assign_staff_to_hostel(staff, hostel, actor=request.user)
        hostel_name = hostel.name if hostel else "None / All Hostels"
        messages.success(
            request,
            f"Assigned {staff.full_name or staff.login_id} to {hostel_name}."
        )

    return redirect("hostels:manage_staff")


@login_required
def toggle_hostel_status_view(request, hostel_id):
    """Action to activate or deactivate a hostel."""
    if not can_manage_config(request.user):
        raise PermissionDenied()

    hostel = get_object_or_404(Hostel, id=hostel_id)
    if request.method == "POST":
        if hostel.is_active:
            # Deactivate
            _, active_count = deactivate_hostel(hostel)
            if active_count > 0:
                messages.warning(
                    request,
                    f"Hostel '{hostel.name}' has been marked Inactive. Note: {active_count} active tickets are still associated with this hostel."
                )
            else:
                messages.success(request, f"Hostel '{hostel.name}' has been marked Inactive.")
        else:
            hostel.is_active = True
            hostel.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"Hostel '{hostel.name}' is now Active.")

    return redirect("hostels:manage_hostels")


@login_required
def toggle_staff_status_view(request, user_id):
    """Action to activate or deactivate a staff member."""
    if not can_manage_config(request.user):
        raise PermissionDenied()

    staff = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        if staff.is_active:
            replacement_id = request.POST.get("replacement_staff")
            replacement = (
                get_object_or_404(User, id=replacement_id) if replacement_id else None
            )
            try:
                _, active_tickets = deactivate_staff(staff, replacement_staff=replacement)
                if active_tickets > 0:
                    messages.warning(
                        request,
                        f"Staff member {staff.full_name or staff.login_id} deactivated. Warning: They still have {active_tickets} active tickets assigned."
                    )
                else:
                    messages.success(request, f"Staff member {staff.full_name or staff.login_id} deactivated.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, "message") else e))
        else:
            staff.is_active = True
            staff.save(update_fields=["is_active"])
            messages.success(request, f"Staff member {staff.full_name or staff.login_id} activated.")

    return redirect("hostels:manage_staff")


def options_floors_view(request):
    """
    Returns HTML floor options / segmented buttons for a hostel.
    GET /hostels/options/floors/?hostel=<id>
    """
    hostel_id = request.GET.get("hostel")
    floors = []
    if hostel_id:
        try:
            hostel = Hostel.objects.get(pk=hostel_id)
            floors = hostel.floors
        except (Hostel.DoesNotExist, ValueError):
            floors = []
    selected_floor = request.GET.get("selected")
    return render(
        request,
        "hostels/partials/_options_floors.html",
        {"floors": floors, "selected_floor": str(selected_floor) if selected_floor else ""},
    )


def options_rooms_view(request):
    """
    Returns HTML room chips / options for a given hostel and optional floor.
    GET /hostels/options/rooms/?hostel=<id>&floor=<floor>&format=options|chips
    """
    from django.http import HttpResponse

    hostel_id = request.GET.get("hostel")
    floor = request.GET.get("floor")
    selected_id = request.GET.get("selected")
    format_type = request.GET.get("format", "chips")

    rooms = []
    if hostel_id:
        try:
            hostel = Hostel.objects.get(pk=hostel_id)
            floor_int = int(floor) if floor and str(floor).isdigit() else None
            rooms = room_options(hostel, floor=floor_int)
        except (Hostel.DoesNotExist, ValueError):
            rooms = []

    if format_type == "options":
        options_html = ['<option value="">Select room</option>']
        for r in rooms:
            sel = " selected" if str(r.id) == str(selected_id) else ""
            res_count = getattr(r, "resident_count", 0)
            options_html.append(
                f'<option value="{r.id}" data-floor="{r.floor}" data-capacity="{r.capacity}" data-residents="{res_count}"{sel}>'
                f'Room {r.room_number} · Floor {r.floor}'
                f'</option>'
            )
        return HttpResponse("\n".join(options_html))

    return render(
        request,
        "hostels/partials/_options_rooms.html",
        {
            "rooms": rooms,
            "selected_id": str(selected_id) if selected_id else "",
            "hostel_id": hostel_id,
            "selected_floor": floor,
        },
    )


@login_required
def manage_rooms(request):
    """
    Admin Rooms management page.
    Filters: Hostel (12), Floor, Status, Occupancy (Empty / Partial / Full).
    Search: Room number.
    Server-side pagination: 50 per page.
    """
    from django.core.paginator import Paginator

    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage rooms.")

    rooms_qs = Room.objects.select_related("hostel").annotate(
        resident_count=Count("residents", filter=Q(residents__is_active=True))
    )

    hostel_filter = request.GET.get("hostel", "").strip()
    if hostel_filter:
        rooms_qs = rooms_qs.filter(hostel_id=hostel_filter)

    floor_filter = request.GET.get("floor", "").strip()
    if floor_filter and floor_filter.isdigit():
        rooms_qs = rooms_qs.filter(floor=int(floor_filter))

    status_filter = request.GET.get("status", "").strip()
    if status_filter == "active":
        rooms_qs = rooms_qs.filter(is_active=True)
    elif status_filter == "inactive":
        rooms_qs = rooms_qs.filter(is_active=False)

    occupancy_filter = request.GET.get("occupancy", "").strip()
    if occupancy_filter == "empty":
        rooms_qs = rooms_qs.filter(resident_count=0)
    elif occupancy_filter == "full":
        rooms_qs = rooms_qs.filter(resident_count__gte=F("capacity"))
    elif occupancy_filter == "partial":
        rooms_qs = rooms_qs.filter(resident_count__gt=0, resident_count__lt=F("capacity"))

    search_query = request.GET.get("q", "").strip()
    if search_query:
        rooms_qs = rooms_qs.filter(room_number__icontains=search_query)

    rooms_qs = sorted(rooms_qs, key=lambda r: (natural_sort_key(r.hostel.code), r.floor, r.room_number))

    paginator = Paginator(rooms_qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    all_hostels = sorted(Hostel.objects.filter(is_active=True), key=natural_sort_key)

    return render(
        request,
        "hostels/manage_rooms.html",
        {
            "page_obj": page_obj,
            "hostels": all_hostels,
            "selected_hostel": hostel_filter,
            "selected_floor": floor_filter,
            "selected_status": status_filter,
            "selected_occupancy": occupancy_filter,
            "search_query": search_query,
            "current_section": "manage_rooms",
        },
    )


@login_required
def generate_rooms_view(request, hostel_id):
    """
    POST /manage/hostels/<hostel_id>/generate-rooms/
    Generates missing rooms for a hostel (idempotent).
    """
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can generate rooms.")

    if request.method == "POST":
        hostel = get_object_or_404(Hostel, pk=hostel_id)
        floors = int(request.POST.get("floors", 3))
        rooms_per_floor = int(request.POST.get("rooms_per_floor", 40))
        capacity = int(request.POST.get("capacity", 2))
        first_floor = int(request.POST.get("first_floor", 1))

        count = generate_rooms(
            hostel=hostel,
            floors=floors,
            rooms_per_floor=rooms_per_floor,
            capacity=capacity,
            first_floor=first_floor,
        )
        messages.success(request, f"Generated {count} new rooms for {hostel.code}.")
    return redirect("hostels:manage_hostels")


@login_required
def toggle_room_status_view(request, room_id):
    """POST /manage/rooms/<room_id>/toggle-status/"""
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can edit rooms.")

    room = get_object_or_404(Room, pk=room_id)
    if request.method == "POST":
        room.is_active = not room.is_active
        room.save(update_fields=["is_active", "updated_at"])
        status_label = "Active" if room.is_active else "Inactive"
        messages.success(request, f"Room {room.room_number} ({room.hostel.code}) is now {status_label}.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_rooms"
    return redirect(next_url)


@login_required
def edit_room_view(request, room_id):
    """POST /manage/rooms/<room_id>/edit/"""
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can edit rooms.")

    room = get_object_or_404(Room, pk=room_id)
    if request.method == "POST":
        capacity = request.POST.get("capacity")
        if capacity and capacity.isdigit():
            room.capacity = int(capacity)
            room.save(update_fields=["capacity", "updated_at"])
            messages.success(request, f"Updated capacity for Room {room.room_number} to {room.capacity}.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_rooms"
    return redirect(next_url)


@login_required
def manage_residents(request):
    """
    Warden & Admin Resident Verification page.
    Wardens see residents in their own hostel.
    Admins & Chief Wardens see campus-wide residents.
    """
    from django.core.paginator import Paginator

    from apps.core.permissions import can_verify_residents

    if not can_verify_residents(request.user):
        raise PermissionDenied("You do not have permission to view residents.")

    is_scoped_warden = (request.user.role == Role.WARDEN and not request.user.is_superuser)
    warden_hostel = request.user.hostel if is_scoped_warden else None

    residents_qs = User.objects.filter(role=Role.HOSTELER).select_related(
        "hostel", "room", "verified_by"
    )

    if is_scoped_warden:
        if not warden_hostel:
            residents_qs = residents_qs.none()
        else:
            residents_qs = residents_qs.filter(hostel=warden_hostel)

    # Base counts for tabs
    tab_base_qs = residents_qs
    pending_count = tab_base_qs.filter(is_verified=False, rejected_reason="").count()
    verified_count = tab_base_qs.filter(is_verified=True).count()
    rejected_count = tab_base_qs.filter(is_verified=False).exclude(rejected_reason="").count()
    all_count = tab_base_qs.count()

    # Tab filtering
    tab = request.GET.get("tab", "all").lower()
    if tab == "verified":
        residents_qs = residents_qs.filter(is_verified=True)
    elif tab == "rejected":
        residents_qs = residents_qs.filter(is_verified=False).exclude(rejected_reason="")
    elif tab == "pending":
        residents_qs = residents_qs.filter(is_verified=False, rejected_reason="")
    else:  # all (default)
        tab = "all"

    # Hostel filter for Admins
    hostel_filter = request.GET.get("hostel", "").strip()
    if not is_scoped_warden and hostel_filter:
        residents_qs = residents_qs.filter(hostel_id=hostel_filter)

    # Floor filter
    floor_filter = request.GET.get("floor", "").strip()
    if floor_filter and floor_filter.isdigit():
        residents_qs = residents_qs.filter(room__floor=int(floor_filter))

    # Search query
    search_query = request.GET.get("q", "").strip()
    if search_query:
        residents_qs = residents_qs.filter(
            Q(full_name__icontains=search_query)
            | Q(login_id__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(room__room_number__icontains=search_query)
        )

    residents_qs = residents_qs.order_by("-date_joined")

    paginator = Paginator(residents_qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    all_hostels = sorted(Hostel.objects.filter(is_active=True), key=natural_sort_key)

    return render(
        request,
        "hostels/manage_residents.html",
        {
            "page_obj": page_obj,
            "tab": tab,
            "pending_count": pending_count,
            "verified_count": verified_count,
            "rejected_count": rejected_count,
            "all_count": all_count,
            "is_scoped_warden": is_scoped_warden,
            "warden_hostel": warden_hostel,
            "hostels": all_hostels,
            "selected_hostel": hostel_filter,
            "selected_floor": floor_filter,
            "search_query": search_query,
            "current_section": "manage_residents",
        },
    )


@login_required
def verify_resident_view(request, resident_id):
    """POST /manage/residents/<resident_id>/verify/"""
    from apps.accounts.services import verify_resident
    from apps.core.permissions import can_verify_residents

    if not can_verify_residents(request.user):
        raise PermissionDenied()

    resident = get_object_or_404(User, pk=resident_id, role=Role.HOSTELER)
    if request.user.role == Role.WARDEN and not request.user.is_superuser:
        if resident.hostel_id != request.user.hostel_id:
            raise PermissionDenied("You can only verify residents in your assigned hostel.")

    if request.method == "POST":
        verify_resident(resident, verified_by=request.user)
        messages.success(request, f"Verified resident {resident.full_name or resident.login_id}.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_residents"
    return redirect(next_url)


@login_required
def reject_resident_view(request, resident_id):
    """POST /manage/residents/<resident_id>/reject/"""
    from apps.accounts.services import reject_resident
    from apps.core.permissions import can_verify_residents

    if not can_verify_residents(request.user):
        raise PermissionDenied()

    resident = get_object_or_404(User, pk=resident_id, role=Role.HOSTELER)
    if request.user.role == Role.WARDEN and not request.user.is_superuser:
        if resident.hostel_id != request.user.hostel_id:
            raise PermissionDenied("You can only reject residents in your assigned hostel.")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        try:
            reject_resident(resident, reason=reason, rejected_by=request.user)
            messages.warning(request, f"Resident {resident.full_name or resident.login_id} marked as rejected.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_residents"
    return redirect(next_url)


@login_required
def reset_resident_password_view(request, resident_id):
    """POST /manage/residents/<resident_id>/reset-password/"""
    from apps.accounts.services import reset_resident_password
    from apps.core.permissions import can_verify_residents

    if not can_verify_residents(request.user):
        raise PermissionDenied()

    resident = get_object_or_404(User, pk=resident_id, role=Role.HOSTELER)
    if request.user.role == Role.WARDEN and not request.user.is_superuser:
        if resident.hostel_id != request.user.hostel_id:
            raise PermissionDenied("You can only reset passwords for residents in your assigned hostel.")

    if request.method == "POST":
        temp_pw = reset_resident_password(resident, reset_by=request.user)
        messages.success(
            request,
            f"Password reset for {resident.login_id}! Temporary password: {temp_pw} (User must change password on next login)."
        )

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_residents"
    return redirect(next_url)


@login_required
def bulk_verify_residents_view(request):
    """POST /manage/residents/bulk-verify/"""
    from apps.accounts.services import bulk_verify_residents
    from apps.core.permissions import can_verify_residents

    if not can_verify_residents(request.user):
        raise PermissionDenied()

    if request.method == "POST":
        resident_ids = request.POST.getlist("resident_ids")
        if resident_ids:
            allowed_hostel = request.user.hostel_id if (request.user.role == Role.WARDEN and not request.user.is_superuser) else None
            count = bulk_verify_residents(resident_ids, verified_by=request.user, allowed_hostel_id=allowed_hostel)
            messages.success(request, f"Successfully verified {count} resident(s).")
        else:
            messages.info(request, "No residents selected.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "hostels:manage_residents"
    return redirect(next_url)


