import json
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.announcements.models import (
    Announcement,
    AnnouncementKind,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.hostels.models import GenderType, Hostel
from apps.notifications.models import (
    Notification,
    NotificationType,
    NotificationVerb,
)
from apps.notifications.services import (
    notify_announcement_published,
    notify_ticket_assigned,
    notify_ticket_closed,
    notify_ticket_created,
    notify_ticket_escalated,
    notify_ticket_reassigned,
    notify_ticket_reopened,
    notify_ticket_resolved,
    notify_ticket_status_changed,
    notify_urgent_ticket,
)
from apps.tickets.factories import TicketFactory
from apps.tickets.models import Priority, Status
from apps.tickets.services.escalation import escalate
from apps.tickets.services.status import change_status


@pytest.mark.django_db
def test_ticket_assigned_creates_notification():
    """Assignee gets notification when ticket is assigned."""
    assignee = UserFactory(role=Role.CARETAKER)
    reporter = UserFactory(role=Role.HOSTELER)
    ticket = TicketFactory(reporter=reporter, assigned_to=assignee)

    notify_ticket_assigned(ticket, assignee)

    notifs = Notification.objects.filter(recipient=assignee)
    assert notifs.count() == 1
    notif = notifs.first()
    assert notif.ticket == ticket
    assert notif.verb == NotificationVerb.ASSIGNED
    assert "assigned" in notif.message.lower()
    assert notif.notification_type == NotificationType.TICKET


@pytest.mark.django_db
def test_ticket_status_change_notifies_reporter():
    """Reporter is notified when ticket status changes."""
    assignee = UserFactory(role=Role.CARETAKER)
    reporter = UserFactory(role=Role.HOSTELER)
    ticket = TicketFactory(reporter=reporter, assigned_to=assignee, status=Status.ASSIGNED)

    change_status(ticket, Status.IN_PROGRESS, actor=assignee)

    notifs = Notification.objects.filter(recipient=reporter)
    assert notifs.filter(verb=NotificationVerb.STATUS_CHANGED).exists()


@pytest.mark.django_db
def test_ticket_resolved_notifies_reporter():
    """Reporter gets specific RESOLVED notification when ticket is resolved."""
    assignee = UserFactory(role=Role.CARETAKER)
    reporter = UserFactory(role=Role.HOSTELER)
    ticket = TicketFactory(reporter=reporter, assigned_to=assignee, status=Status.IN_PROGRESS)

    change_status(ticket, Status.RESOLVED, actor=assignee)

    notif = Notification.objects.filter(recipient=reporter, verb=NotificationVerb.RESOLVED).first()
    assert notif is not None
    assert notif.ticket == ticket
    assert "resolved" in notif.message.lower()


@pytest.mark.django_db
def test_ticket_reopened_notifies_assignee():
    """Assignee gets specific REOPENED notification when ticket is reopened."""
    assignee = UserFactory(role=Role.CARETAKER)
    reporter = UserFactory(role=Role.HOSTELER)
    ticket = TicketFactory(reporter=reporter, assigned_to=assignee, status=Status.RESOLVED)

    change_status(ticket, Status.IN_PROGRESS, actor=reporter)

    notif = Notification.objects.filter(recipient=assignee, verb=NotificationVerb.REOPENED).first()
    assert notif is not None
    assert notif.ticket == ticket
    assert "reopened" in notif.message.lower()


@pytest.mark.django_db
def test_ticket_escalated_notifies_all_parties():
    """Escalation notifies new assignee, old assignee, and reporter."""
    hostel = Hostel.objects.create(name="Hostel Alpha", code="HA", gender_type=GenderType.BOYS)
    old_assignee = UserFactory(role=Role.CARETAKER, hostel=hostel, escalation_level=1)
    new_assignee = UserFactory(role=Role.WARDEN, hostel=hostel, escalation_level=2)
    hostel.responsible_warden = new_assignee
    hostel.save()

    reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
    ticket = TicketFactory(
        reporter=reporter,
        assigned_to=old_assignee,
        hostel=hostel,
        current_level=1,
        priority=Priority.MEDIUM,
    )

    escalate(ticket, actor=None, reason="SLA breach")

    # Check new assignee notification
    assert Notification.objects.filter(recipient=new_assignee, verb=NotificationVerb.ESCALATED).exists()
    # Check old assignee notification
    assert Notification.objects.filter(recipient=old_assignee, verb=NotificationVerb.ESCALATED).exists()
    # Check reporter notification
    assert Notification.objects.filter(recipient=reporter, verb=NotificationVerb.ESCALATED).exists()


@pytest.mark.django_db
def test_ticket_reassigned_notifies_all_parties():
    """Reassignment notifies new assignee, old assignee, and reporter."""
    old_assignee = UserFactory(role=Role.CARETAKER)
    new_assignee = UserFactory(role=Role.CARETAKER)
    reporter = UserFactory(role=Role.HOSTELER)
    actor = UserFactory(role=Role.ADMIN)
    ticket = TicketFactory(reporter=reporter, assigned_to=old_assignee)

    notify_ticket_reassigned(ticket, old_assignee, new_assignee, actor)

    assert Notification.objects.filter(recipient=new_assignee, verb=NotificationVerb.REASSIGNED).exists()
    assert Notification.objects.filter(recipient=old_assignee, verb=NotificationVerb.REASSIGNED).exists()
    assert Notification.objects.filter(recipient=reporter, verb=NotificationVerb.REASSIGNED).exists()


@pytest.mark.django_db
def test_announcement_published_notifies_audience():
    """Hostel audience receives notification when notice is published."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    author = UserFactory(role=Role.WARDEN, hostel=hostel)
    hosteler_1 = UserFactory(role=Role.HOSTELER, hostel=hostel)
    hosteler_2 = UserFactory(role=Role.HOSTELER, hostel=hostel)

    ann = Announcement.objects.create(
        title="Power Outage",
        body="Power outage tonight from 10 PM to 11 PM.",
        kind=AnnouncementKind.NOTICE,
        severity=AnnouncementSeverity.INFO,
        status=AnnouncementStatus.PUBLISHED,
        author=author,
        all_hostels=False,
    )
    ann.hostels.add(hostel)

    notify_announcement_published(ann, [hosteler_1.id, hosteler_2.id])

    assert Notification.objects.filter(recipient=hosteler_1, announcement=ann).exists()
    assert Notification.objects.filter(recipient=hosteler_2, announcement=ann).exists()


@pytest.mark.django_db
def test_announcement_not_sent_to_other_hostel():
    """Hostelers in other hostels do not receive targeted notice notification."""
    hostel_a = Hostel.objects.create(name="Hostel A", code="HA", gender_type=GenderType.BOYS)
    hostel_b = Hostel.objects.create(name="Hostel B", code="HB", gender_type=GenderType.GIRLS)

    author = UserFactory(role=Role.WARDEN, hostel=hostel_a)
    user_a = UserFactory(role=Role.HOSTELER, hostel=hostel_a)
    user_b = UserFactory(role=Role.HOSTELER, hostel=hostel_b)

    ann = Announcement.objects.create(
        title="Hostel A Cleaning",
        body="Cleaning in Hostel A only.",
        kind=AnnouncementKind.NOTICE,
        severity=AnnouncementSeverity.INFO,
        status=AnnouncementStatus.PUBLISHED,
        author=author,
        all_hostels=False,
    )
    ann.hostels.add(hostel_a)

    notify_announcement_published(ann, [user_a.id])

    assert Notification.objects.filter(recipient=user_a, announcement=ann).exists()
    assert not Notification.objects.filter(recipient=user_b, announcement=ann).exists()


@pytest.mark.django_db
def test_duplicate_prevention():
    """Same event key does not create duplicate notifications for the same recipient."""
    user = UserFactory()
    ticket = TicketFactory(reporter=user)

    n1 = Notification.create_once(
        event_key="unique_event_123",
        recipient=user,
        ticket=ticket,
        verb=NotificationVerb.CREATED,
        message="Created first time",
    )
    assert n1 is not None

    n2 = Notification.create_once(
        event_key="unique_event_123",
        recipient=user,
        ticket=ticket,
        verb=NotificationVerb.CREATED,
        message="Attempt duplicate",
    )
    assert n2 is None
    assert Notification.objects.filter(recipient=user, event_key="unique_event_123").count() == 1


@pytest.mark.django_db
def test_unread_count_context_processor(client):
    """unread_notifications_count is properly injected in template context."""
    user = UserFactory(password="pass123")
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M1", is_read=False)
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M2", is_read=False)
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M3", is_read=True)

    client.login(username=user.login_id, password="pass123")
    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    assert response.context["unread_notifications_count"] == 2


@pytest.mark.django_db
def test_mark_read_updates_count(client):
    """Marking an individual notification as read updates unread count."""
    user = UserFactory(password="pass123")
    notif = Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M1", is_read=False)

    client.login(username=user.login_id, password="pass123")
    response = client.get(
        reverse("notifications:mark_read", kwargs={"notification_id": notif.id}) + "?format=json",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_read"] is True
    assert data["unread_count"] == 0

    notif.refresh_from_db()
    assert notif.is_read is True


@pytest.mark.django_db
def test_mark_all_read(client):
    """Mark all as read marks all user notifications as read."""
    user = UserFactory(password="pass123")
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M1", is_read=False)
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M2", is_read=False)

    client.login(username=user.login_id, password="pass123")
    response = client.post(
        reverse("notifications:read_all"),
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["unread_count"] == 0
    assert Notification.objects.filter(recipient=user, is_read=False).count() == 0


@pytest.mark.django_db
def test_bell_poll_returns_count(client):
    """HTMX bell poll endpoint returns HTML badge with correct count."""
    user = UserFactory(password="pass123")
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M1", is_read=False)
    Notification.objects.create(recipient=user, verb=NotificationVerb.CREATED, message="M2", is_read=False)

    client.login(username=user.login_id, password="pass123")
    response = client.get(reverse("notifications:poll"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "notification-badge-count" in content
    assert "2" in content


@pytest.mark.django_db
def test_notification_belongs_to_user(client):
    """A user cannot read or access another user's notification."""
    user_a = UserFactory(password="pass_a")
    user_b = UserFactory(password="pass_b")
    notif_b = Notification.objects.create(recipient=user_b, verb=NotificationVerb.CREATED, message="For B", is_read=False)

    client.login(username=user_a.login_id, password="pass_a")
    response = client.get(
        reverse("notifications:mark_read", kwargs={"notification_id": notif_b.id})
    )
    assert response.status_code == 404

    notif_b.refresh_from_db()
    assert notif_b.is_read is False


@pytest.mark.django_db
def test_notification_api_list_authenticated(client):
    """API endpoint returns current user's notifications and unread count."""
    user = UserFactory(password="pass123")
    other_user = UserFactory(password="pass456")
    ticket = TicketFactory(reporter=user)

    Notification.objects.create(
        recipient=user,
        ticket=ticket,
        verb=NotificationVerb.CREATED,
        title="Ticket Received",
        message="Your ticket has been logged.",
        notification_type=NotificationType.TICKET,
        is_read=False,
    )
    Notification.objects.create(
        recipient=other_user,
        verb=NotificationVerb.CREATED,
        message="Other user secret",
        is_read=False,
    )

    client.login(username=user.login_id, password="pass123")
    response = client.get(reverse("notifications:api_list"))
    assert response.status_code == 200
    data = response.json()
    assert data["unread_count"] == 1
    assert len(data["notifications"]) == 1
    item = data["notifications"][0]
    assert item["title"] == "Ticket Received"
    assert item["ticket_no"] == ticket.ticket_no
    assert item["type"] == NotificationType.TICKET


@pytest.mark.django_db
def test_notification_list_page(client):
    """Notification center template renders properly with notifications."""
    user = UserFactory(password="pass123")
    ticket = TicketFactory(reporter=user)
    Notification.objects.create(
        recipient=user,
        ticket=ticket,
        verb=NotificationVerb.ASSIGNED,
        title="Ticket Assigned",
        message="Assigned to Caretaker.",
        is_read=False,
    )

    client.login(username=user.login_id, password="pass123")
    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Ticket Assigned" in content
    assert "Assigned to Caretaker." in content
    assert "Mark all as read" in content
