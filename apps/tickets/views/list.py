import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel
from apps.tickets.models import Category, Priority, SavedFilter, Status, Tag, Ticket
from apps.tickets.services.status import change_status


def get_filtered_tickets(request):
    user = request.user
    qs = (
        Ticket.objects.visible_to(user)
        .select_related("category", "hostel", "assigned_to", "reporter")
        .prefetch_related("tags")
        .annotate(comment_count=Count("comments"))
    )

    # 1. Search filter (⌘K / top search)
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(ticket_no__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(reporter__login_id__icontains=search)
            | Q(reporter__full_name__icontains=search)
        )

    # 2. Sidebar Filters
    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    priority_filter = request.GET.get("priority", "").strip()
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    category_filter = request.GET.get("category", "").strip()
    if category_filter:
        qs = qs.filter(category_id=category_filter)

    hostel_filter = request.GET.get("hostel", "").strip()
    if hostel_filter:
        qs = qs.filter(hostel_id=hostel_filter)

    assigned_filter = request.GET.get("assigned_to", "").strip()
    if assigned_filter:
        qs = qs.filter(assigned_to_id=assigned_filter)

    tag_filter = request.GET.get("tag", "").strip()
    if tag_filter:
        qs = qs.filter(tags__id=tag_filter)

    level_filter = request.GET.get("level", "").strip()
    if level_filter:
        qs = qs.filter(current_level=level_filter)

    # 3. Sorting
    sort_by = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "-created_at",
        "created_at",
        "-updated_at",
        "updated_at",
        "due_at",
        "-due_at",
        "priority",
    ]
    if sort_by in allowed_sorts:
        qs = qs.order_by(sort_by)

    return qs


@login_required
def ticket_list(request):
    user = request.user
    qs = get_filtered_tickets(request)

    # Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Prepare preserved query parameters for pagination and export links
    query_dict = request.GET.copy()
    if "page" in query_dict:
        del query_dict["page"]
    query_params = query_dict.urlencode()

    context = {
        "tickets": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "query_params": query_params,
        "current_section": "tickets",
        "is_kanban": False,
        # Filter options
        "statuses": Status.choices,
        "priorities": Priority.choices,
        "categories": Category.objects.filter(is_active=True),
        "hostels": Hostel.objects.filter(is_active=True),
        "staff_users": User.objects.filter(
            role__in=[Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN],
            is_active=True,
        ),
        "tags": Tag.objects.all(),
        "saved_filters": SavedFilter.objects.filter(user=user, view="list"),
        # Current active filter values
        "curr_search": request.GET.get("search", "").strip(),
        "curr_status": request.GET.get("status", "").strip(),
        "curr_priority": request.GET.get("priority", "").strip(),
        "curr_category": request.GET.get("category", "").strip(),
        "curr_hostel": request.GET.get("hostel", "").strip(),
        "curr_assigned": request.GET.get("assigned_to", "").strip(),
        "curr_tag": request.GET.get("tag", "").strip(),
        "curr_sort": request.GET.get("sort", "-created_at"),
    }

    # If HTMX request, return only the partial table
    if request.headers.get("HX-Request") == "true":
        return render(request, "tickets/_list_table.html", context)

    return render(request, "tickets/list.html", context)


@login_required
def export_tickets_csv(request):
    """Exports currently filtered tickets to CSV format."""
    qs = get_filtered_tickets(request)
    response = HttpResponse(content_type="text/csv")
    filename = f"tickets_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Ticket No",
            "Title",
            "Status",
            "Priority",
            "Category",
            "Hostel",
            "Reporter Roll ID",
            "Reporter Name",
            "Assigned To",
            "Current Level",
            "Created At",
            "Due At",
            "Resolved At",
            "Is Overdue",
        ]
    )

    for t in qs:
        writer.writerow(
            [
                t.ticket_no,
                t.title,
                t.get_status_display(),
                t.get_priority_display(),
                t.category.name if t.category else "",
                t.hostel.name if t.hostel else "",
                t.reporter.login_id if t.reporter else "",
                t.reporter.full_name if t.reporter else "",
                (
                    t.assigned_to.full_name or t.assigned_to.login_id
                    if t.assigned_to
                    else "Unassigned"
                ),
                f"L{t.current_level}",
                t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
                t.due_at.strftime("%Y-%m-%d %H:%M:%S") if t.due_at else "",
                t.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if t.resolved_at else "",
                "Yes" if t.is_overdue else "No",
            ]
        )

    return response


@login_required
def search_quick(request):
    """Instant JSON search endpoint for ⌘K palette."""
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    tickets = (
        Ticket.objects.visible_to(request.user)
        .filter(
            Q(ticket_no__icontains=query)
            | Q(title__icontains=query)
            | Q(reporter__login_id__icontains=query)
            | Q(reporter__full_name__icontains=query)
        )
        .select_related("category", "hostel")[:6]
    )

    results = [
        {
            "ticket_no": t.ticket_no,
            "title": t.title,
            "status": t.status,
            "status_display": t.get_status_display(),
            "category": t.category.name if t.category else "",
            "hostel": t.hostel.name if t.hostel else "",
            "url": reverse("tickets:detail", kwargs={"ticket_no": t.ticket_no}),
        }
        for t in tickets
    ]
    return JsonResponse({"results": results})


@login_required
def save_filter(request):
    """Saves current query string as a user preset."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        querystring = request.POST.get("querystring", "").strip()
        view_type = request.POST.get("view", "list")
        if name and querystring:
            SavedFilter.objects.create(
                user=request.user,
                name=name,
                querystring=querystring,
                view=view_type,
            )
            messages.success(request, f"Saved filter '{name}'.")
        return redirect(f"{reverse('tickets:list')}?{querystring}")
    return redirect("tickets:list")


@login_required
def delete_filter(request, filter_id):
    """Deletes a saved filter."""
    if request.method == "POST":
        sf = get_object_or_404(SavedFilter, id=filter_id, user=request.user)
        sf.delete()
        messages.info(request, "Filter removed.")
    return redirect("tickets:list")


@login_required
def bulk_action(request):
    """Applies bulk actions (status update, reassignment) for selected tickets."""
    if request.method != "POST":
        return redirect("tickets:list")

    if request.user.is_hosteler:
        messages.error(request, "Hostelers cannot perform bulk operations.")
        return redirect("tickets:list")

    action = request.POST.get("action", "").strip()
    ticket_ids = request.POST.getlist("selected_tickets")
    target_value = request.POST.get("target_value", "").strip()

    if not ticket_ids:
        messages.warning(request, "No tickets selected.")
        return redirect("tickets:list")

    tickets = Ticket.objects.visible_to(request.user).filter(id__in=ticket_ids)
    count = 0

    if action == "status" and target_value:
        for t in tickets:
            try:
                change_status(t, target_value, actor=request.user)
                count += 1
            except Exception:
                pass
        messages.success(request, f"Updated status of {count} ticket(s) to {target_value}.")

    elif action == "assign" and target_value:
        try:
            assignee = User.objects.get(id=target_value)
            for t in tickets:
                t.assigned_to = assignee
                t.save(update_fields=["assigned_to", "updated_at"])
                count += 1
            messages.success(
                request,
                f"Assigned {count} ticket(s) to {assignee.full_name or assignee.login_id}.",
            )
        except User.DoesNotExist:
            messages.error(request, "Assignee not found.")

    return redirect("tickets:list")
