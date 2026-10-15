import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import (
    Announcement,
    AnnouncementKind,
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.hostels.factories import HostelFactory


@pytest.mark.django_db
class TestAnnouncementsViews:
    def test_announcements_hosteler_flow(self, client):
        hostel = HostelFactory()
        user = UserFactory(role=Role.HOSTELER, hostel=hostel)
        ann = AnnouncementFactory(
            all_hostels=True,
            severity=AnnouncementSeverity.URGENT,
            status=AnnouncementStatus.PUBLISHED,
            title="Scheduled Water Maintenance",
        )

        client.force_login(user)

        # 1. Hosteler list page
        resp = client.get(reverse("announcements:list"))
        assert resp.status_code == 200
        assert "Scheduled Water Maintenance" in resp.content.decode()

        # 2. Hosteler detail page marks as read
        resp_detail = client.get(reverse("announcements:detail", kwargs={"announcement_id": ann.id}))
        assert resp_detail.status_code == 200
        assert AnnouncementRead.objects.filter(announcement=ann, user=user).exists()

        # 3. Read endpoint (idempotent dismissal)
        resp_read = client.post(reverse("announcements:read", kwargs={"announcement_id": ann.id}))
        assert resp_read.status_code == 200

    def test_announcements_staff_manage(self, client):
        hostel_a = HostelFactory(name="Hostel One")
        hostel_b = HostelFactory(name="Hostel Two")
        warden_a = UserFactory(role=Role.WARDEN, hostel=hostel_a)

        client.force_login(warden_a)

        # Manage list page
        resp = client.get(reverse("announcements:manage_list"))
        assert resp.status_code == 200

        # Warden creates announcement for own hostel
        create_url = reverse("announcements:manage_create")
        post_data = {
            "title": "Cleanliness drive this Saturday",
            "body": "All residents are requested to keep rooms accessible.",
            "kind": AnnouncementKind.NOTICE,
            "severity": AnnouncementSeverity.INFO,
            "hostels": [hostel_a.id],
            "action": "publish",
        }
        resp_create = client.post(create_url, post_data)
        assert resp_create.status_code in [200, 302]
        created_ann = Announcement.objects.filter(title="Cleanliness drive this Saturday").first()
        assert created_ann is not None
        assert created_ann.status == AnnouncementStatus.PUBLISHED

        # Warden cannot publish to another hostel
        illegal_post = {
            "title": "Illegal announcement",
            "body": "Should fail",
            "kind": AnnouncementKind.NOTICE,
            "severity": AnnouncementSeverity.INFO,
            "hostels": [hostel_b.id],
            "action": "publish",
        }
        resp_illegal = client.post(create_url, illegal_post)
        assert resp_illegal.status_code in [400, 403] or Announcement.objects.filter(title="Illegal announcement").count() == 0
