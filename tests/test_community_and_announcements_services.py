import pytest
from datetime import timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import (
    AnnouncementKind,
    AnnouncementRead,
    AnnouncementSeverity,
    AnnouncementStatus,
)
from apps.announcements.services import (
    archive,
    audience_users,
    can_publish,
    mark_read,
    publish,
    schedule,
    unread_count,
    visible_to,
)
from apps.hostels.factories import HostelFactory
from apps.notifications.models import Notification, NotificationVerb
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import (
    CommentScope,
    CriticalityRule,
    Priority,
    Status,
    TicketActivity,
    TicketComment,
    TicketRepost,
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
from apps.tickets.services.criticality import recompute_criticality


@pytest.mark.django_db
class TestRepostService:
    def test_repost_creation_and_undo(self):
        hostel = HostelFactory()
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
        ticket = TicketFactory(
            hostel=hostel,
            reporter=reporter,
            visibility=TicketVisibility.HOSTEL,
            status=Status.OPEN,
            base_priority=Priority.LOW,
            priority=Priority.LOW,
        )

        # Repost
        result = toggle_repost(hosteler, ticket, note="Same here!")
        assert result["reposted"] is True
        assert result["repost_count"] == 1
        assert result["affected_count"] == 2
        assert hosteler in ticket.followers.all()
        assert TicketRepost.objects.filter(ticket=ticket, user=hosteler).exists()

        # Check notification sent to reporter
        notif = Notification.objects.filter(recipient=reporter, ticket=ticket).first()
        assert notif is not None
        assert notif.verb == NotificationVerb.REPOSTED

        # Undo repost
        undo_result = toggle_repost(hosteler, ticket)
        assert undo_result["reposted"] is False
        assert undo_result["repost_count"] == 0
        assert undo_result["affected_count"] == 1
        assert hosteler not in ticket.followers.all()
        assert not TicketRepost.objects.filter(ticket=ticket, user=hosteler).exists()

    def test_cannot_repost_own_ticket(self):
        hostel = HostelFactory()
        hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
        ticket = TicketFactory(hostel=hostel, reporter=hosteler, visibility=TicketVisibility.HOSTEL)

        with pytest.raises(ValidationError, match="cannot repost your own ticket"):
            toggle_repost(hosteler, ticket)

    def test_cannot_repost_other_hostel_ticket(self):
        h1 = HostelFactory()
        h2 = HostelFactory()
        hosteler1 = UserFactory(role=Role.HOSTELER, hostel=h1)
        hosteler2 = UserFactory(role=Role.HOSTELER, hostel=h2)
        ticket = TicketFactory(hostel=h2, reporter=hosteler2, visibility=TicketVisibility.HOSTEL)

        with pytest.raises(PermissionDenied):
            toggle_repost(hosteler1, ticket)

    def test_cannot_repost_inactive_ticket(self):
        hostel = HostelFactory()
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
        ticket = TicketFactory(
            hostel=hostel,
            reporter=reporter,
            visibility=TicketVisibility.HOSTEL,
            status=Status.RESOLVED,
        )

        with pytest.raises(ValidationError, match="no longer active"):
            toggle_repost(hosteler, ticket)


@pytest.mark.django_db
class TestCriticalityService:
    def test_priority_ladder_and_thresholds(self):
        hostel = HostelFactory()
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        ticket = TicketFactory(
            hostel=hostel,
            reporter=reporter,
            visibility=TicketVisibility.HOSTEL,
            base_priority=Priority.LOW,
            priority=Priority.LOW,
            status=Status.OPEN,
            level_started_at=timezone.now(),
        )

        # Base is LOW (1). Threshold 3 -> +1 level -> MEDIUM (2)
        ticket.repost_count = 3
        recompute_criticality(ticket)
        assert ticket.priority == Priority.MEDIUM

        # Threshold 6 -> +2 levels from base -> HIGH (3)
        ticket.repost_count = 6
        recompute_criticality(ticket)
        assert ticket.priority == Priority.HIGH

        # Threshold 10 -> Force URGENT (4)
        ticket.repost_count = 10
        recompute_criticality(ticket)
        assert ticket.priority == Priority.URGENT

        # Removing reposts lowers back down to base
        ticket.repost_count = 0
        recompute_criticality(ticket)
        assert ticket.priority == Priority.LOW

    def test_never_lowers_below_base_priority(self):
        hostel = HostelFactory()
        ticket = TicketFactory(
            hostel=hostel,
            base_priority=Priority.HIGH,
            priority=Priority.HIGH,
            repost_count=0,
        )
        recompute_criticality(ticket)
        assert ticket.priority == Priority.HIGH

        # Even with 3 reposts (+1 from LOW, but base is already HIGH), priority is at least HIGH
        ticket.repost_count = 3
        recompute_criticality(ticket)
        assert ticket.priority in [Priority.HIGH, Priority.URGENT]


@pytest.mark.django_db
class TestCommunityFeedAndComments:
    def test_feed_queryset_filtering(self):
        hostel1 = HostelFactory()
        hostel2 = HostelFactory()
        user1 = UserFactory(role=Role.HOSTELER, hostel=hostel1)
        other_user1 = UserFactory(role=Role.HOSTELER, hostel=hostel1)
        user2 = UserFactory(role=Role.HOSTELER, hostel=hostel2)

        cat_allowed = CategoryFactory(allow_community=True)
        cat_disallowed = CategoryFactory(allow_community=False)

        # 1. Shared in same hostel (should show)
        t1 = TicketFactory(
            hostel=hostel1,
            reporter=other_user1,
            category=cat_allowed,
            visibility=TicketVisibility.HOSTEL,
            community_hidden=False,
            status=Status.OPEN,
        )

        # 2. Private in same hostel (should not show)
        TicketFactory(
            hostel=hostel1,
            reporter=other_user1,
            category=cat_allowed,
            visibility=TicketVisibility.PRIVATE,
        )

        # 3. Disallowed category (should not show)
        TicketFactory(
            hostel=hostel1,
            reporter=other_user1,
            category=cat_disallowed,
            visibility=TicketVisibility.HOSTEL,
        )

        # 4. Hidden ticket (should not show)
        TicketFactory(
            hostel=hostel1,
            reporter=other_user1,
            category=cat_allowed,
            visibility=TicketVisibility.HOSTEL,
            community_hidden=True,
        )

        # 5. User's own ticket (should not show in community feed)
        TicketFactory(
            hostel=hostel1,
            reporter=user1,
            category=cat_allowed,
            visibility=TicketVisibility.HOSTEL,
        )

        # 6. Different hostel (should not show)
        TicketFactory(
            hostel=hostel2,
            reporter=user2,
            category=cat_allowed,
            visibility=TicketVisibility.HOSTEL,
        )

        feed = feed_queryset(user1)
        assert list(feed) == [t1]

    def test_community_comments_and_moderation(self):
        hostel = HostelFactory()
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
        warden = UserFactory(role=Role.WARDEN, hostel=hostel)
        ticket = TicketFactory(hostel=hostel, reporter=reporter, visibility=TicketVisibility.HOSTEL)

        # Add hosteler comment
        c1 = add_community_comment(hosteler, ticket, "Water is also brown on floor 3.")
        assert c1.scope == CommentScope.COMMUNITY
        assert c1.is_official is False

        # Add staff comment (official reply)
        c2 = add_community_comment(warden, ticket, "Plumber has arrived.")
        assert c2.scope == CommentScope.COMMUNITY
        assert c2.is_official is True

        # Moderate (hide) comment
        hide_comment(warden, c1, reason="Inappropriate language")
        c1.refresh_from_db()
        assert c1.is_hidden is True
        assert c1.hidden_by == warden

    def test_similar_open_tickets(self):
        hostel = HostelFactory()
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
        cat = CategoryFactory()

        t1 = TicketFactory(
            hostel=hostel,
            reporter=reporter,
            category=cat,
            title="Ceiling fan regulator broken in room 102",
            visibility=TicketVisibility.HOSTEL,
            status=Status.OPEN,
        )

        similar = similar_open_tickets(hosteler, "Fan regulator not working", category=cat)
        assert t1 in similar


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
