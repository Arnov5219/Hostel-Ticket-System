import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from apps.accounts.models import Role, User
from apps.accounts.services.staff import (
    ActiveTicketsError,
    archive_staff,
    change_login_id,
    create_staff,
    deactivate_staff,
    edit_staff,
    get_active_tickets_count,
    get_eligible_replacements,
    reactivate_staff,
    reset_staff_password,
)
from apps.core.permissions import Capability, can_manage_user
from apps.hostels.models import Hostel
from apps.tickets.models import Status

STAFF_ROLES = [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]
ACTIVE_STATUSES = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD, Status.RESOLVED]


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@login_required
def staff_list_view(request):
    """
    Staff management list page.
    Columns: Name (avatar + login ID) · Role · Level · Hostel · Active tickets · Status · Actions.
    Filters: role, hostel, status (Active default; Deactivated; Archived). Search by name/login_id.
    """
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    role_filter = request.GET.get("role", "")
    hostel_filter = request.GET.get("hostel", "")
    status_filter = request.GET.get("status", "ACTIVE")
    search_query = request.GET.get("search", "").strip()

    qs = User.objects.filter(role__in=STAFF_ROLES).select_related("hostel")

    if status_filter == "ACTIVE":
        qs = qs.filter(is_active=True, archived_at__isnull=True)
    elif status_filter == "DEACTIVATED":
        qs = qs.filter(is_active=False, archived_at__isnull=True)
    elif status_filter == "ARCHIVED":
        qs = qs.filter(archived_at__isnull=False)
    elif status_filter == "ALL":
        pass

    if role_filter:
        qs = qs.filter(role=role_filter)
    if hostel_filter:
        if hostel_filter == "CAMPUS":
            qs = qs.filter(hostel__isnull=True)
        else:
            qs = qs.filter(hostel_id=hostel_filter)

    if search_query:
        qs = qs.filter(Q(full_name__icontains=search_query) | Q(login_id__icontains=search_query))

    staff_members = qs.annotate(
        active_tickets=Count(
            "assigned_tickets",
            filter=Q(assigned_tickets__status__in=ACTIVE_STATUSES),
        )
    ).order_by("escalation_level", "full_name", "login_id")

    # Add `can_manage` flag for actor
    for member in staff_members:
        member.actor_can_manage = can_manage_user(request.user, member)

    # Determine which roles actor may assign
    assignable_roles = []
    for r in STAFF_ROLES:
        if can_manage_user(request.user, User(role=r)):
            assignable_roles.append(r)

    hostels = Hostel.objects.filter(is_active=True).order_by("name")

    context = {
        "staff_members": staff_members,
        "hostels": hostels,
        "assignable_roles": assignable_roles,
        "current_section": "manage_staff",
        "curr_role": role_filter,
        "curr_hostel": hostel_filter,
        "curr_status": status_filter,
        "curr_search": search_query,
        "all_roles": STAFF_ROLES,
    }
    return render(request, "hostels/manage_staff.html", context)


@login_required
def create_staff_view(request):
    """Creates a new staff member."""
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        login_id = request.POST.get("login_id", "").strip()
        role = request.POST.get("role", "")
        hostel_id = request.POST.get("hostel_id")
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        password_mode = request.POST.get("password_mode", "generate")
        custom_password = request.POST.get("custom_password", "") if password_mode == "manual" else None
        is_l1_responsible = request.POST.get("is_l1_responsible") == "on"

        hostel = Hostel.objects.filter(id=hostel_id, is_active=True).first() if hostel_id else None

        try:
            user, temp_pw = create_staff(
                actor=request.user,
                full_name=full_name,
                login_id=login_id,
                role=role,
                hostel=hostel,
                phone=phone,
                email=email,
                password=custom_password,
                is_l1_responsible=is_l1_responsible,
                ip=get_client_ip(request),
            )
            if temp_pw:
                request.session["just_created_staff"] = {
                    "login_id": user.login_id,
                    "name": user.full_name,
                    "temp_password": temp_pw,
                }
                messages.success(request, f"Staff member '{user.full_name}' created successfully.")
            else:
                messages.success(request, f"Staff member '{user.full_name}' created successfully with custom password.")
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")


@login_required
def edit_staff_view(request, user_id):
    """Edits basic staff information (name, phone, email, role, hostel)."""
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if not can_manage_user(request.user, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", target.role)
        hostel_id = request.POST.get("hostel_id")
        hostel = Hostel.objects.filter(id=hostel_id).first() if hostel_id else None

        try:
            edit_staff(
                actor=request.user,
                target=target,
                full_name=full_name,
                phone=phone,
                email=email,
                role=role,
                hostel=hostel,
                ip=get_client_ip(request),
            )
            messages.success(request, f"Details updated for {target.full_name or target.login_id}.")
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")


@login_required
def change_login_id_view(request, user_id):
    """Changes a staff member's login ID."""
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if not can_manage_user(request.user, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    if request.method == "POST":
        new_login_id = request.POST.get("new_login_id", "").strip()
        try:
            change_login_id(
                actor=request.user,
                target=target,
                new_login_id=new_login_id,
                ip=get_client_ip(request),
            )
            messages.success(request, f"Login ID updated to '{new_login_id}'. User sessions invalidated.")
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")


@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def reset_password_view(request, user_id):
    """
    Resets a staff member's password with re-authentication.
    Returns temporary password once with no-store headers.
    """
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if not can_manage_user(request.user, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    if request.method == "POST":
        actor_password = request.POST.get("actor_password", "")
        try:
            temp_password = reset_staff_password(
                actor=request.user,
                target=target,
                actor_password=actor_password,
                ip=get_client_ip(request),
            )
            # Render HTMX snippet or JSON displaying temporary password once
            if request.headers.get("HX-Request") == "true":
                response = render(
                    request,
                    "hostels/partials/_password_reset_result.html",
                    {"target": target, "temp_password": temp_password},
                )
                response["Cache-Control"] = "no-store, no-cache, must-revalidate"
                return response

            messages.success(request, f"Password reset for {target.login_id}. Temporary password: {temp_password}")
        except (ValidationError, PermissionDenied) as e:
            if request.headers.get("HX-Request") == "true":
                return HttpResponse(
                    f'<div class="form-error" style="color: var(--st-open-fg); margin-top: 8px;">{e.message if hasattr(e, "message") else str(e)}</div>',
                    status=400,
                )
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")


@login_required
def reassign_preview_view(request, user_id):
    """
    HTMX endpoint returning the deactivation / archive modal content with
    active tickets count and eligible replacement dropdown.
    """
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if not can_manage_user(request.user, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    action_type = request.GET.get("action", "deactivate")
    active_count = get_active_tickets_count(target)
    replacements = get_eligible_replacements(target) if active_count > 0 else []

    is_l1_default_hostel = Hostel.objects.filter(responsible_staff=target).first()

    return render(
        request,
        "hostels/partials/_staff_deactivate_dialog.html",
        {
            "target": target,
            "action_type": action_type,
            "active_count": active_count,
            "replacements": replacements,
            "is_l1_default_hostel": is_l1_default_hostel,
        },
    )


@login_required
def deactivate_staff_view(request, user_id):
    """Deactivates staff account with ticket reassignment."""
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        replacement_id = request.POST.get("replacement_id")
        reason = request.POST.get("reason", "").strip()
        replacement = User.objects.filter(id=replacement_id, is_active=True).first() if replacement_id else None

        try:
            deactivate_staff(
                actor=request.user,
                target=target,
                replacement=replacement,
                reason=reason,
                archive=False,
                ip=get_client_ip(request),
            )
            messages.success(request, f"Staff member '{target.full_name or target.login_id}' deactivated.")
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")


@login_required
def archive_staff_view(request, user_id):
    """Archives (deletes) staff account with ticket reassignment."""
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        replacement_id = request.POST.get("replacement_id")
        reason = request.POST.get("reason", "").strip()
        replacement = User.objects.filter(id=replacement_id, is_active=True).first() if replacement_id else None

        try:
            archive_staff(
                actor=request.user,
                target=target,
                replacement=replacement,
                reason=reason,
                ip=get_client_ip(request),
            )
            messages.success(request, f"Staff member '{target.full_name or target.login_id}' deleted (archived).")
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")


@login_required
def reactivate_staff_view(request, user_id):
    """Reactivates a deactivated or archived staff member."""
    if not request.user.can(Capability.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    target = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        try:
            reactivate_staff(
                actor=request.user,
                target=target,
                ip=get_client_ip(request),
            )
            messages.success(request, f"Staff member '{target.full_name or target.login_id}' reactivated.")
        except (ValidationError, PermissionDenied) as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("hostels:manage_staff")
