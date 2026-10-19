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
from apps.notifications.models import Notification, NotificationVerb
from apps.tickets.factories import TicketFactory


@pytest.mark.django_db
def test_pinned_notice_renders_clean_badge_and_structure(client):
    """Pinned notices must render clean badge without cramping or overlapping title."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    author = UserFactory(role=Role.WARDEN, hostel=hostel, password="password123")
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")

    ann = Announcement.objects.create(
        title="Emergency Water Tank Maintenance Schedule",
        body="There will be water supply disruption tomorrow morning between 9 AM and 12 PM.",
        kind=AnnouncementKind.MAINTENANCE,
        severity=AnnouncementSeverity.URGENT,
        status=AnnouncementStatus.PUBLISHED,
        author=author,
        all_hostels=True,
        is_pinned=True,
        published_at=timezone.now(),
    )

    client.login(username=hosteler.login_id, password="password123")
    response = client.get(reverse("announcements:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    # Check dedicated classes preventing overlap
    assert "notice-card" in content
    assert "notice-card-header" in content
    assert "notice-card-title-row" in content
    assert "notice-pinned-pill" in content
    assert "badge-urgent-pill" in content
    assert "Emergency Water Tank Maintenance Schedule" in content
    assert "Pinned" in content

    # Quick View removal verification
    assert "Quick view" not in content
    assert "openNoticeQuickView" not in content
    assert "notice-quick-view-modal" not in content
    assert "notice-full-body-" not in content
    assert "Read full notice →" in content



@pytest.mark.django_db
def test_notice_detail_shows_exact_date_time_and_full_content(client):
    """Notice detail page must prominently show exact date, time, and full un-truncated content."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    author = UserFactory(role=Role.CHIEF_WARDEN, password="password123")
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")

    pub_time = timezone.now()
    ann = Announcement.objects.create(
        title="Hostel Rules Revision 2026",
        body="Paragraph 1: Curfew hours are updated.\n\nParagraph 2: Visitor policy is amended.",
        kind=AnnouncementKind.POLICY,
        severity=AnnouncementSeverity.IMPORTANT,
        status=AnnouncementStatus.PUBLISHED,
        author=author,
        all_hostels=True,
        is_pinned=True,
        published_at=pub_time,
    )

    client.login(username=hosteler.login_id, password="password123")
    response = client.get(reverse("announcements:detail", kwargs={"announcement_id": ann.id}))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    # Check exact date & time grid
    assert "notice-meta-grid" in content
    assert "Posted on" in content
    assert pub_time.strftime("%d %B %Y") in content
    assert "Time" in content
    assert "Posted by" in content
    assert "Target Audience" in content
    # Check body preservation
    assert "Paragraph 1: Curfew hours are updated." in content
    assert "Paragraph 2: Visitor policy is amended." in content


@pytest.mark.django_db
def test_mark_all_notifications_as_read_ajax_and_isolation(client):
    """Mark all as read must update only the logged-in user's notifications and support JSON responses."""
    user_a = UserFactory(password="user_a_pass")
    user_b = UserFactory(password="user_b_pass")

    # Create unread notifications for User A
    Notification.objects.create(recipient=user_a, verb=NotificationVerb.ASSIGNED, message="Ticket A1 assigned", is_read=False)
    Notification.objects.create(recipient=user_a, verb=NotificationVerb.STATUS_CHANGED, message="Ticket A2 updated", is_read=False)

    # Create unread notification for User B
    Notification.objects.create(recipient=user_b, verb=NotificationVerb.COMMENTED, message="Ticket B1 commented", is_read=False)

    assert Notification.objects.filter(recipient=user_a, is_read=False).count() == 2
    assert Notification.objects.filter(recipient=user_b, is_read=False).count() == 1

    # User A sends AJAX mark-all-read
    client.login(username=user_a.login_id, password="user_a_pass")
    response = client.post(
        reverse("notifications:read_all"),
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    assert data.get("status") == "success"
    assert data.get("unread_count") == 0
    assert data.get("marked_count") == 2

    # Verify User A notifications are read
    assert Notification.objects.filter(recipient=user_a, is_read=False).count() == 0

    # Verify User B notifications are untouched
    assert Notification.objects.filter(recipient=user_b, is_read=False).count() == 1


@pytest.mark.django_db
def test_notification_list_markup_and_modal_support(client):
    """Notifications list markup contains mark-all-read in header, interactive rows, and detail modal."""
    user = UserFactory(password="notif_pass")
    ticket = TicketFactory(title="Broken AC unit")
    notif = Notification.objects.create(
        recipient=user,
        ticket=ticket,
        verb=NotificationVerb.STATUS_CHANGED,
        message="Your ticket has been marked in progress by Caretaker.",
        is_read=False,
    )

    client.login(username=user.login_id, password="notif_pass")
    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    # Card header with Mark all as read button
    assert "notifications-card-header" in content
    assert "mark-all-read-btn" in content
    assert "Mark all as read" in content

    # Interactive row with full message and modal
    assert f'id="notif-row-{notif.id}"' in content
    assert "notification-row" in content
    assert 'data-date="' in content
    assert 'data-time="' in content
    assert f'data-ticket-no="{ticket.ticket_no}"' in content
    assert 'id="notification-detail-modal"' in content
    assert 'id="notif-modal-date"' in content
    assert 'id="notif-modal-time"' in content
    assert 'id="notif-modal-message"' in content


@pytest.mark.django_db
def test_single_notification_mark_read_json(client):
    """Single notification read endpoint returns JSON when requested via AJAX."""
    user = UserFactory(password="single_notif_pass")
    notif = Notification.objects.create(
        recipient=user,
        verb=NotificationVerb.ASSIGNED,
        message="Ticket assigned to technician",
        is_read=False,
    )

    client.login(username=user.login_id, password="single_notif_pass")
    url = reverse("notifications:mark_read", kwargs={"notification_id": notif.id}) + "?format=json"
    response = client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest", HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    assert data.get("status") == "ok"
    assert data.get("is_read") is True
    assert data.get("unread_count") == 0

    notif.refresh_from_db()
    assert notif.is_read is True
