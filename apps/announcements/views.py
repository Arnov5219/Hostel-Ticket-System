from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.announcements.forms import AnnouncementForm
from apps.announcements.models import (
    Announcement,
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.announcements.services import (
    archive,
    audience_users,
    can_publish,
    mark_read,
    publish,
    schedule,
    unread_count,
    visible_to,
)
from apps.core.permissions import can_publish_announcements
from apps.hostels.models import Hostel


@login_required
def announcement_list(request):
    """Hosteler & staff list view for announcements with All, Unread, and Pinned tabs."""
    tab = request.GET.get("tab", "all")
    qs = visible_to(request.user)

    read_ids = set(
        AnnouncementRead.objects.filter(user=request.user).values_list("announcement_id", flat=True)
    )

    if tab == "unread":
        qs = qs.exclude(id__in=read_ids)
    elif tab == "pinned":
        qs = qs.filter(is_pinned=True)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "announcements/list.html",
        {
            "page_obj": page_obj,
            "announcements": page_obj.object_list,
            "read_ids": read_ids,
            "current_tab": tab,
            "unread_total": unread_count(request.user),
            "current_section": "announcements",
            "can_manage": can_publish_announcements(request.user),
        },
    )


@login_required
def announcement_detail(request, announcement_id):
    """Detail view for an announcement; automatically marks it as read."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    # Check visibility
    if not request.user.is_admin and not request.user.is_chief_warden:
        if announcement.status != AnnouncementStatus.PUBLISHED:
            raise PermissionDenied("This announcement is not published.")
        if request.user.is_hosteler and not announcement.all_hostels:
            if not request.user.hostel or request.user.hostel not in announcement.hostels.all():
                raise PermissionDenied("You do not have access to this announcement.")

    # Mark as read
    mark_read(request.user, announcement)

    return render(
        request,
        "announcements/detail.html",
        {
            "announcement": announcement,
            "current_section": "announcements",
            "can_manage": can_publish_announcements(request.user),
        },
    )


@login_required
@require_POST
def mark_read_endpoint(request, announcement_id):
    """HTMX endpoint to dismiss banners or mark an announcement read."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    mark_read(request.user, announcement)
    return HttpResponse("")


# ==============================================================================
# Staff Management Views (/manage/announcements/...)
# ==============================================================================


@login_required
def manage_list(request):
    """Staff table view of all announcements within scope."""
    if not can_publish_announcements(request.user):
        raise PermissionDenied("You do not have permission to manage announcements.")

    qs = Announcement.objects.all().select_related("author").prefetch_related("hostels", "reads")
    if request.user.role == Role.WARDEN:
        if request.user.hostel:
            qs = qs.filter(hostels=request.user.hostel)
        else:
            qs = qs.none()

    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    hostel_filter = request.GET.get("hostel")
    if hostel_filter and request.user.role in [Role.ADMIN, Role.CHIEF_WARDEN]:
        qs = qs.filter(hostels__id=hostel_filter)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # Calculate read counts and audience sizes
    announcement_items = []
    for ann in page_obj.object_list:
        total_audience = audience_users(ann).count()
        read_count_val = ann.reads.count()
        announcement_items.append({
            "announcement": ann,
            "read_count": read_count_val,
            "total_audience": total_audience,
        })

    hostels = Hostel.objects.filter(is_active=True)

    return render(
        request,
        "announcements/manage_list.html",
        {
            "items": announcement_items,
            "page_obj": page_obj,
            "hostels": hostels,
            "current_status": status_filter,
            "current_hostel": hostel_filter,
            "current_section": "announcements",
        },
    )


@login_required
def manage_create(request):
    """Staff form to create, draft, schedule, or publish an announcement."""
    if not can_publish_announcements(request.user):
        raise PermissionDenied("You do not have permission to publish announcements.")

    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            action_btn = request.POST.get("action", "publish")

            if action_btn == "draft":
                announcement.status = AnnouncementStatus.DRAFT
                announcement.save()
                form.save_m2m()
                messages.success(request, f"Announcement draft '{announcement.title}' saved.")
                return redirect("announcements:manage_list")
            elif action_btn == "schedule":
                publish_at = form.cleaned_data.get("publish_at")
                if not publish_at or publish_at <= timezone.now():
                    form.add_error("publish_at", "Please provide a future date and time to schedule.")
                    return render(request, "announcements/manage_form.html", {"form": form})
                announcement.status = AnnouncementStatus.SCHEDULED
                announcement.save()
                form.save_m2m()
                messages.success(request, f"Announcement scheduled for {publish_at}.")
                return redirect("announcements:manage_list")
            else:  # publish now
                announcement.save()
                form.save_m2m()
                publish(announcement, actor=request.user)
                messages.success(request, f"Announcement '{announcement.title}' published successfully.")
                return redirect("announcements:manage_list")
    else:
        form = AnnouncementForm(user=request.user)

    return render(
        request,
        "announcements/manage_form.html",
        {
            "form": form,
            "is_edit": False,
            "current_section": "announcements",
        },
    )


@login_required
def manage_edit(request, announcement_id):
    """Staff form to edit an existing announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if not can_publish(request.user, announcement):
        raise PermissionDenied("You do not have permission to edit this announcement.")

    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement, user=request.user)
        if form.is_valid():
            ann = form.save(commit=False)
            action_btn = request.POST.get("action")

            if action_btn == "publish" and ann.status != AnnouncementStatus.PUBLISHED:
                ann.save()
                form.save_m2m()
                publish(ann, actor=request.user)
                messages.success(request, f"Announcement '{ann.title}' published.")
            else:
                ann.save()
                form.save_m2m()
                messages.success(request, f"Announcement '{ann.title}' updated.")

            return redirect("announcements:manage_list")
    else:
        form = AnnouncementForm(instance=announcement, user=request.user)

    return render(
        request,
        "announcements/manage_form.html",
        {
            "form": form,
            "announcement": announcement,
            "is_edit": True,
            "current_section": "announcements",
        },
    )


@login_required
@require_POST
def manage_state_action(request, announcement_id, action):
    """Performs publish, archive, or pin state transitions on an announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if not can_publish(request.user, announcement):
        raise PermissionDenied("You cannot modify this announcement.")

    if action == "publish":
        publish(announcement, actor=request.user)
        messages.success(request, f"Announcement '{announcement.title}' published.")
    elif action == "archive":
        archive(announcement, actor=request.user)
        messages.success(request, f"Announcement '{announcement.title}' archived.")
    elif action == "pin":
        announcement.is_pinned = not announcement.is_pinned
        announcement.save(update_fields=["is_pinned"])
        messages.success(
            request,
            f"Announcement {'pinned to top' if announcement.is_pinned else 'unpinned'}."
        )

    return redirect("announcements:manage_list")
