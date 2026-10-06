from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.notifications.models import Notification


@login_required
def notification_list(request):
    notifications_qs = Notification.objects.filter(recipient=request.user).select_related("ticket")
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
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")


@login_required
def mark_read_and_redirect(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notif.is_read = True
    notif.save()

    if notif.ticket:
        return redirect("tickets:detail", ticket_no=notif.ticket.ticket_no)
    return redirect("notifications:list")


@login_required
def bell_poll(request):
    """HTMX polling endpoint returning updated bell badge."""
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    if unread_count > 0:
        return HttpResponse(
            '<span class="notification-badge" title="' + str(unread_count) + ' unread"></span>'
        )
    return HttpResponse("")
