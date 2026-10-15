from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.permissions import Capability, has_capability
from apps.tickets.models import (
    Category,
    CommentReport,
    CommentScope,
    Ticket,
    TicketComment,
    TicketVisibility,
)
from apps.tickets.services.community import (
    add_community_comment,
    feed_queryset,
    similar_open_tickets,
    toggle_repost,
)


def hosteler_community_required(view_func):
    """Enforces that only authenticated hostelers have access to Community endpoints."""
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not has_capability(request.user, Capability.COMMUNITY_ACCESS):
            raise PermissionDenied("Community is reserved for residents only.")
        return view_func(request, *args, **kwargs)
    return _wrapped


@hosteler_community_required
def feed_page(request):
    """Full-page view of the community feed."""
    sort = request.GET.get("sort", "recent")
    category_id = request.GET.get("category")
    status = request.GET.get("status")

    qs = feed_queryset(request.user, sort=sort, category_id=category_id, status=status)
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    categories = Category.objects.filter(is_active=True, allow_community=True)

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
        },
    )


@hosteler_community_required
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


@hosteler_community_required
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


@hosteler_community_required
@require_POST
def toggle_repost_view(request, ticket_no):
    """HTMX endpoint to toggle repost on a ticket."""
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


@hosteler_community_required
def community_comments_view(request, ticket_no):
    """HTMX endpoint to view and add community comments on a ticket."""
    ticket = get_object_or_404(Ticket, ticket_no=ticket_no)

    if ticket.visibility != TicketVisibility.HOSTEL:
        raise PermissionDenied("Community comments are only available on shared hostel tickets.")

    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        try:
            add_community_comment(request.user, ticket, body)
        except (ValidationError, PermissionDenied) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return HttpResponse(
                f'<div class="form-error" style="color: var(--danger); font-size: var(--fs-xs); padding: 4px 8px;">{msg}</div>',
                status=400,
            )

    # Fetch active community comments
    comments_qs = (
        ticket.comments.filter(scope=CommentScope.COMMUNITY, is_hidden=False)
        .select_related("author")
        .prefetch_related("reports")
    )

    return render(
        request,
        "community/_comment_thread.html",
        {
            "ticket": ticket,
            "comments": comments_qs,
        },
    )


# ---------------------------------------------------------
# Hosteler Self-Moderation Endpoints (Section 4.5)
# ---------------------------------------------------------

@hosteler_community_required
@require_POST
def delete_comment_view(request, comment_id):
    """Hosteler deletes their own comment."""
    comment = get_object_or_404(TicketComment, id=comment_id, scope=CommentScope.COMMUNITY)
    if comment.author_id != request.user.id:
        raise PermissionDenied("You can only delete your own comment.")

    comment.delete()
    return HttpResponse("")


@hosteler_community_required
@require_POST
def reporter_hide_comment_view(request, comment_id):
    """Ticket reporter can hide comments on their own ticket."""
    comment = get_object_or_404(TicketComment, id=comment_id, scope=CommentScope.COMMUNITY)
    if comment.ticket.reporter_id != request.user.id:
        raise PermissionDenied("Only the ticket creator can moderate comments on this post.")

    comment.is_hidden = True
    comment.hidden_by = request.user
    comment.hidden_reason = "Hidden by ticket reporter"
    comment.save(update_fields=["is_hidden", "hidden_by", "hidden_reason"])
    return HttpResponse(
        '<div class="text-muted" style="font-size: var(--fs-xs); font-style: italic;">Comment hidden by post author</div>'
    )


@hosteler_community_required
@require_POST
def report_comment_view(request, comment_id):
    """Hosteler reports a comment. Auto-hides when 3 distinct reports are recorded."""
    comment = get_object_or_404(TicketComment, id=comment_id, scope=CommentScope.COMMUNITY)
    if comment.author_id == request.user.id:
        return HttpResponse("You cannot report your own comment.", status=400)

    report, created = CommentReport.objects.get_or_create(comment=comment, reporter=request.user)
    report_count = comment.reports.count()

    if report_count >= 3:
        comment.is_hidden = True
        comment.hidden_reason = "Reported by residents"
        comment.save(update_fields=["is_hidden", "hidden_reason"])
        return HttpResponse(
            '<div class="text-muted" style="font-size: var(--fs-xs); font-style: italic;">Comment hidden due to resident reports</div>'
        )

    return HttpResponse(
        '<span class="badge" style="color: var(--text-muted); font-size: 11px;">Reported</span>'
    )
