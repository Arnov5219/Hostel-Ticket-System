from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.core.permissions import can_moderate_community
from apps.tickets.models import (
    Category,
    CommentScope,
    Status,
    Ticket,
    TicketComment,
    TicketVisibility,
)
from apps.tickets.services.community import (
    add_community_comment,
    feed_queryset,
    hide_comment,
    set_community_hidden,
    similar_open_tickets,
    toggle_repost,
)


@login_required
def feed_page(request):
    """Full-page view of the community feed."""
    sort = request.GET.get("sort", "recent")
    category_id = request.GET.get("category")
    status = request.GET.get("status")

    qs = feed_queryset(request.user, sort=sort, category_id=category_id, status=status)
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    categories = Category.objects.filter(is_active=True, allow_community=True)
    is_unverified = request.user.is_hosteler and not getattr(request.user, "is_verified", True)

    return render(
        request,
        "community/feed.html",
        {
            "page_obj": page_obj,
            "tickets": page_obj.object_list,
            "categories": categories,
            "current_sort": sort,
            "current_category": category_id,
            "current_status": status,
            "current_section": "community",
            "is_unverified": is_unverified,
        },
    )


@login_required
def feed_partial(request):
    """HTMX endpoint returning paged post cards for infinite scroll and filtering."""
    sort = request.GET.get("sort", "recent")
    category_id = request.GET.get("category")
    status = request.GET.get("status")

    qs = feed_queryset(request.user, sort=sort, category_id=category_id, status=status)
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "community/_feed_list.html",
        {
            "page_obj": page_obj,
            "tickets": page_obj.object_list,
            "current_sort": sort,
            "current_category": category_id,
            "current_status": status,
        },
    )


@login_required
def similar_issues(request):
    """HTMX endpoint returning similar issues while raising a ticket."""
    title = request.GET.get("title", "").strip()
    category_id = request.GET.get("category")

    if not title or len(title) < 3:
        return HttpResponse("")

    category = None
    if category_id:
        category = Category.objects.filter(id=category_id).first()

    similar = similar_open_tickets(request.user, title=title, category=category)
    if not similar:
        return HttpResponse("")

    return render(
        request,
        "community/_similar_tickets.html",
        {
            "similar_tickets": similar,
        },
    )


@login_required
@require_POST
def toggle_repost_view(request, ticket_no):
    """HTMX endpoint to toggle repost on a ticket."""
    if request.user.is_hosteler and not getattr(request.user, "is_verified", True):
        return HttpResponse(
            '<div class="toast-error" role="alert" style="color: var(--danger); font-size: var(--fs-xs); margin-top: 4px;">'
            'Your account is pending warden verification. Community reposting unlocks once verified.</div>',
            status=403,
        )

    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    note = request.POST.get("note", "")

    try:
        result = toggle_repost(request.user, ticket, note=note)
    except (ValidationError, PermissionDenied) as e:
        msg = e.message if hasattr(e, "message") else str(e)
        return HttpResponse(
            f'<div class="toast-error" role="alert" style="color: var(--danger); font-size: var(--fs-xs); margin-top: 4px;">{msg}</div>',
            status=400,
        )

    updated_ticket = result["ticket"]
    # Provide has_reposted attribute for template
    updated_ticket.has_reposted = result["reposted"]

    return render(
        request,
        "community/_card_footer.html",
        {
            "ticket": updated_ticket,
            "user": request.user,
            "reposted": result["reposted"],
            "repost_count": result["repost_count"],
            "affected_count": result["affected_count"],
            "priority": result["priority"],
        },
    )


@login_required
def community_comments_view(request, ticket_no):
    """HTMX endpoint to view and add community comments on a ticket."""
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)

    if ticket.visibility != TicketVisibility.HOSTEL:
        raise PermissionDenied("Community comments are only available on shared hostel tickets.")

    if request.method == "POST":
        if request.user.is_hosteler and not getattr(request.user, "is_verified", True):
            return HttpResponse(
                '<div class="form-error" style="color: var(--danger); font-size: var(--fs-xs); padding: 4px 8px;">'
                'Your account is pending warden verification. Community comments unlock once verified.</div>',
                status=403,
            )

        body = request.POST.get("body", "").strip()
        try:
            add_community_comment(request.user, ticket, body)
        except (ValidationError, PermissionDenied) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return HttpResponse(
                f'<div class="form-error" style="color: var(--danger); font-size: var(--fs-xs); padding: 4px 8px;">{msg}</div>',
                status=400,
            )

    # Fetch community comments
    comments_qs = ticket.comments.filter(scope=CommentScope.COMMUNITY).select_related("author")
    if request.user.is_hosteler:
        comments_qs = comments_qs.filter(is_hidden=False)

    return render(
        request,
        "community/_comment_thread.html",
        {
            "ticket": ticket,
            "comments": comments_qs,
            "can_moderate": can_moderate_community(request.user),
        },
    )


@login_required
@require_POST
def hide_comment_view(request, comment_id):
    """Staff moderation endpoint to hide a community comment."""
    comment = get_object_or_404(TicketComment, id=comment_id)
    reason = request.POST.get("reason", "Inappropriate content")

    try:
        hide_comment(request.user, comment, reason=reason)
    except PermissionDenied as e:
        return HttpResponse(str(e), status=403)

    return HttpResponse(
        f'<span class="badge" style="background-color: var(--bg-subtle); color: var(--text-muted); font-size: 11px;">Hidden: {reason}</span>'
    )


@login_required
@require_POST
def hide_ticket_view(request, ticket_no):
    """Staff moderation endpoint to remove/restore a ticket from community feed."""
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)
    hidden = request.POST.get("hidden", "true").lower() == "true"
    reason = request.POST.get("reason", "")

    try:
        set_community_hidden(request.user, ticket, hidden=hidden, reason=reason)
    except PermissionDenied as e:
        return HttpResponse(str(e), status=403)

    return HttpResponse(
        f'<div class="community-hidden-status" style="font-size: var(--fs-xs); color: var(--text-muted);">'
        f'Community visibility: {"Hidden" if hidden else "Visible"}</div>'
    )
