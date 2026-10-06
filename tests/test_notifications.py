import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.notifications.models import Notification
from apps.tickets.factories import TicketFactory


@pytest.mark.django_db
def test_notifications_list_and_mark_all_read(client):
    user = UserFactory(password="notif_password")
    client.login(username=user.login_id, password="notif_password")

    # Create unread notifications
    Notification.objects.create(recipient=user, verb="Assigned", message="Ticket assigned")
    Notification.objects.create(recipient=user, verb="Escalated", message="Ticket escalated")
    assert Notification.objects.filter(recipient=user, is_read=False).count() == 2

    # View list
    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    assert "Ticket assigned" in response.content.decode()

    # Mark all read
    post_res = client.post(reverse("notifications:read_all"))
    assert post_res.status_code == 302
    assert Notification.objects.filter(recipient=user, is_read=False).count() == 0


@pytest.mark.django_db
def test_notification_poll_endpoint(client):
    user = UserFactory(password="poll_password")
    client.login(username=user.login_id, password="poll_password")

    # Initially 0 unread
    res1 = client.get(reverse("notifications:poll"))
    assert res1.status_code == 200
    assert res1.content.decode() == ""

    # Add unread notification
    Notification.objects.create(recipient=user, verb="Alert", message="Action needed")
    res2 = client.get(reverse("notifications:poll"))
    assert res2.status_code == 200
    assert "notification-badge" in res2.content.decode()


@pytest.mark.django_db
def test_mark_read_and_redirect(client):
    user = UserFactory(password="redr_password")
    client.login(username=user.login_id, password="redr_password")

    ticket = TicketFactory()
    notif = Notification.objects.create(
        recipient=user,
        ticket=ticket,
        verb="Updated",
        message="Status updated",
        is_read=False,
    )

    res = client.get(reverse("notifications:mark_read", kwargs={"notification_id": notif.id}))
    assert res.status_code == 302
    assert res.url == reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no})

    notif.refresh_from_db()
    assert notif.is_read is True
