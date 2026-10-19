from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.notifications.models import Notification


@login_required
def notification_list(request):
    notifications_qs = Notification.objects.filter(recipient=request.user).select_related("ticket", "announcement")
    paginator = Paginator(notifications_qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "notifications/list.html",
        {
            "notifications": page_obj,
            "page_obj": page_obj,
            "current_section": "notifications",
            "unread_count": notifications_qs.filter(is_read=False).count(),
        },
    )


@login_required
def mark_all_read(request):
    if request.method == "POST":
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", "")
            or request.content_type == "application/json"
        ):
            return JsonResponse({
                "status": "success",
                "message": "All notifications marked as read.",
                "marked_count": updated_count,
                "unread_count": 0,
            })
        messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")


@login_required
def mark_read_and_redirect(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=["is_read"])

    # If AJAX request, return JSON confirmation
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or request.GET.get("format") == "json"
    ):
        return JsonResponse({
            "status": "ok",
            "id": notif.id,
            "is_read": True,
            "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
        })

    if notif.ticket:
        return redirect("tickets:detail", ticket_no=notif.ticket.ticket_no)
    if notif.announcement:
        return redirect("announcements:detail", announcement_id=notif.announcement.id)
    return redirect("notifications:list")


@login_required
def bell_poll(request):
    """HTMX polling endpoint returning updated bell badge with numeric count."""
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    if unread_count > 0:
        display = "99+" if unread_count > 99 else str(unread_count)
        return HttpResponse(
            f'<span class="notification-badge notification-badge-count" title="{unread_count} unread">{display}</span>'
        )
    return HttpResponse("")


@login_required
def notification_api_list(request):
    """JSON endpoint returning the current user's notifications."""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related("ticket", "announcement")[:50]

    return JsonResponse({
        "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
        "notifications": [
            {
                "id": n.id,
                "title": n.display_title,
                "message": n.message,
                "type": n.notification_type,
                "verb": n.verb,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
                "ticket_no": n.ticket.ticket_no if n.ticket else None,
                "announcement_id": n.announcement_id,
            }
            for n in notifications
        ],
    })
