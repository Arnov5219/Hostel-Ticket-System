import pytest

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import (
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.announcements.services import (
    can_publish,
    mark_read,
    publish,
    unread_count,
)
from apps.hostels.factories import HostelFactory
from apps.notifications.models import Notification


@pytest.mark.django_db
class TestAnnouncementsService:
    def test_warden_publishing_scope(self):
        h1 = HostelFactory()
        h2 = HostelFactory()
        warden = UserFactory(role=Role.WARDEN, hostel=h1)
        cw = UserFactory(role=Role.CHIEF_WARDEN)

        # Warden targeting own hostel: allowed
        ann1 = AnnouncementFactory(author=warden, all_hostels=False)
        ann1.hostels.set([h1])
        assert can_publish(warden, ann1) is True

        # Warden targeting all hostels: disallowed
        ann2 = AnnouncementFactory(author=warden, all_hostels=True)
        assert can_publish(warden, ann2) is False

        # Warden targeting another hostel: disallowed
        ann3 = AnnouncementFactory(author=warden, all_hostels=False)
        ann3.hostels.set([h2])
        assert can_publish(warden, ann3) is False

        # Chief Warden targeting anything: allowed
        assert can_publish(cw, ann2) is True

    def test_publish_creates_notifications_and_read_state(self):
        hostel = HostelFactory()
        warden = UserFactory(role=Role.WARDEN, hostel=hostel)
        h1 = UserFactory(role=Role.HOSTELER, hostel=hostel)
        h2 = UserFactory(role=Role.HOSTELER, hostel=hostel)
        other_hosteler = UserFactory(role=Role.HOSTELER, hostel=HostelFactory())

        ann = AnnouncementFactory(
            author=warden,
            title="Water Tank Cleaning Tomorrow",
            body="Water will be shut off between 10am and 2pm.",
            severity=AnnouncementSeverity.URGENT,
            status=AnnouncementStatus.DRAFT,
            all_hostels=False,
        )
        ann.hostels.set([hostel])

        published_ann = publish(ann, actor=warden)
        assert published_ann.status == AnnouncementStatus.PUBLISHED

        # Check notification dispatched to targeted hostelers only
        notifs = Notification.objects.filter(announcement=ann)
        recipients = set(notifs.values_list("recipient_id", flat=True))
        assert recipients == {h1.id, h2.id}
        assert other_hosteler.id not in recipients

        # Check unread count
        assert unread_count(h1) == 1

        # Mark read
        mark_read(h1, ann)
        assert unread_count(h1) == 0
        assert AnnouncementRead.objects.filter(user=h1, announcement=ann).exists()
