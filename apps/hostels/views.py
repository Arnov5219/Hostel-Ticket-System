from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role, User
from apps.core.permissions import can_manage_config
from apps.hostels.forms import AssignStaffHostelForm, ChangeResponsibleStaffForm, HostelForm
from apps.hostels.models import Hostel
from apps.hostels.services import (
    assign_staff_to_hostel,
    change_hostel_responsible_staff,
    create_hostel,
    deactivate_hostel,
    deactivate_staff,
    get_active_tickets_count_for_hostel,
    get_active_tickets_count_for_staff,
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

    hostels = Hostel.objects.select_related("responsible_staff").all()
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
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage staff.")

    staff_roles = [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]
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

    hostels = Hostel.objects.select_related("responsible_staff").all().order_by("name")
    available_caretakers = User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name")

    return render(
        request,
        "hostels/manage_responsibility.html",
        {
            "hostels": hostels,
            "available_caretakers": available_caretakers,
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
