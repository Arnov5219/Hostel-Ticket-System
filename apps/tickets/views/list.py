from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel
from apps.tickets.models import Category, Priority, SavedFilter, Status, Tag, Ticket


@login_required
def ticket_list(request):
    user = request.user
    qs = (
        Ticket.objects.visible_to(user)
        .select_related("category", "hostel", "room", "assigned_to", "reporter")
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

    # 4. Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Prepare preserved query parameters for pagination links
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
        "curr_search": search,
        "curr_status": status_filter,
        "curr_priority": priority_filter,
        "curr_category": category_filter,
        "curr_hostel": hostel_filter,
        "curr_assigned": assigned_filter,
        "curr_tag": tag_filter,
        "curr_sort": sort_by,
    }

    # If HTMX request, return only the partial table
    if request.headers.get("HX-Request") == "true":
        return render(request, "tickets/_list_table.html", context)

    return render(request, "tickets/list.html", context)
