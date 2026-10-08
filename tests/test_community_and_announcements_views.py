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
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import (
    CommentScope,
    CriticalityRule,
    Priority,
    Status,
    TicketComment,
    TicketRepost,
    TicketVisibility,
)


@pytest.mark.django_db
class TestCommunityFeedViews:
    def test_community_feed_page_and_partial(self, client):
        hostel_a = HostelFactory(name="Hostel Alpha")
        hostel_b = HostelFactory(name="Hostel Beta")

        hosteler_a = UserFactory(role=Role.HOSTELER, hostel=hostel_a)
        other_hosteler_a = UserFactory(role=Role.HOSTELER, hostel=hostel_a, full_name="Alpha Friend")
        hosteler_b = UserFactory(role=Role.HOSTELER, hostel=hostel_b)

        cat = CategoryFactory(name="Plumbing", allow_community=True)

        # Ticket in hostel A (shared)
        t_a = TicketFactory(
            hostel=hostel_a,
            reporter=other_hosteler_a,
            category=cat,
            visibility=TicketVisibility.HOSTEL,
            title="Alpha shared leak",
        )
        # Ticket in hostel B (shared)
        t_b = TicketFactory(
            hostel=hostel_b,
            reporter=hosteler_b,
            category=cat,
            visibility=TicketVisibility.HOSTEL,
            title="Beta shared leak",
        )
        # Ticket in hostel A (private)
        t_priv = TicketFactory(
            hostel=hostel_a,
            reporter=other_hosteler_a,
            category=cat,
            visibility=TicketVisibility.PRIVATE,
            title="Alpha private issue",
        )

        client.force_login(hosteler_a)

        # Full feed page
        resp = client.get(reverse("community:feed"))
        assert resp.status_code == 200
        assert "Alpha shared leak" in resp.content.decode()
        assert "Beta shared leak" not in resp.content.decode()
        assert "Alpha private issue" not in resp.content.decode()

        # Feed partial for HTMX
        resp_partial = client.get(reverse("community:feed_partial"))
        assert resp_partial.status_code == 200
        assert "Alpha shared leak" in resp_partial.content.decode()

    def test_feed_privacy_reporter_anonymity(self, client):
        hostel = HostelFactory()
        user_me = UserFactory(role=Role.HOSTELER, hostel=hostel)
        secret_reporter = UserFactory(
            role=Role.HOSTELER,
            hostel=hostel,
            login_id="SECRET_ROLL_999",
            full_name="Secret Jane Doe",
        )
        cat = CategoryFactory(allow_community=True)

        TicketFactory(
            hostel=hostel,
            reporter=secret_reporter,
            category=cat,
            visibility=TicketVisibility.HOSTEL,
            show_reporter_name=False,
            title="Mysterious Broken Tap",
        )

        client.force_login(user_me)
        resp = client.get(reverse("community:feed"))
        content = resp.content.decode()

        # Privacy invariant: never leak reporter identity when not opted in
        assert "Secret Jane Doe" not in content
        assert "SECRET_ROLL_999" not in content
        assert "A hosteler" in content

    def test_toggle_repost_htmx_endpoint(self, client):
        hostel = HostelFactory()
        author = UserFactory(role=Role.HOSTELER, hostel=hostel)
        peer = UserFactory(role=Role.HOSTELER, hostel=hostel)
        ticket = TicketFactory(
            hostel=hostel,
            reporter=author,
            visibility=TicketVisibility.HOSTEL,
            status=Status.OPEN,
            base_priority=Priority.LOW,
            priority=Priority.LOW,
        )

        client.force_login(peer)
        repost_url = reverse("tickets:repost", kwargs={"ticket_no": ticket.ticket_no})

        # 1. Repost
        resp = client.post(repost_url, {"note": "Having this too"})
        assert resp.status_code == 200
        assert "Reposted" in resp.content.decode()
        ticket.refresh_from_db()
        assert ticket.repost_count == 1

        # 2. Undo repost
        resp_undo = client.post(repost_url)
        assert resp_undo.status_code == 200
        ticket.refresh_from_db()
        assert ticket.repost_count == 0

        # 3. Author cannot repost own ticket
        client.force_login(author)
        resp_own = client.post(repost_url)
        assert resp_own.status_code == 400
        assert "cannot repost your own ticket" in resp_own.content.decode().lower()

    def test_community_comments_and_moderation(self, client):
        hostel = HostelFactory()
        author = UserFactory(role=Role.HOSTELER, hostel=hostel)
        peer = UserFactory(role=Role.HOSTELER, hostel=hostel)
        warden = UserFactory(role=Role.WARDEN, hostel=hostel)

        ticket = TicketFactory(hostel=hostel, reporter=author, visibility=TicketVisibility.HOSTEL)

        # Peer comments
        client.force_login(peer)
        comments_url = reverse("tickets:community_comments", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(comments_url, {"body": "Happening in floor 2 as well."})
        assert resp.status_code == 200
        assert "Happening in floor 2 as well." in resp.content.decode()

        comment = TicketComment.objects.filter(ticket=ticket, scope=CommentScope.COMMUNITY).first()
        assert comment is not None
        assert comment.is_official is False

        # Warden replies officially
        client.force_login(warden)
        resp_staff = client.post(comments_url, {"body": "Electrician has been informed."})
        assert resp_staff.status_code == 200
        staff_comment = TicketComment.objects.filter(author=warden).first()
        assert staff_comment.is_official is True

        # Warden hides inappropriate comment
        hide_url = reverse("community:hide_comment", kwargs={"comment_id": comment.id})
        resp_hide = client.post(hide_url, {"reason": "Spam content"})
        assert resp_hide.status_code == 200
        comment.refresh_from_db()
        assert comment.is_hidden is True
        assert comment.hidden_reason == "Spam content"

    def test_hide_ticket_staff_view(self, client):
        hostel = HostelFactory()
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        warden = UserFactory(role=Role.WARDEN, hostel=hostel)
        ticket = TicketFactory(hostel=hostel, reporter=reporter, visibility=TicketVisibility.HOSTEL)

        client.force_login(warden)
        hide_ticket_url = reverse("community:hide_ticket", kwargs={"ticket_no": ticket.ticket_no})

        # Remove from community
        resp = client.post(hide_ticket_url, {"hidden": "true", "reason": "Not appropriate for feed"})
        assert resp.status_code == 200
        ticket.refresh_from_db()
        assert ticket.community_hidden is True

        # Hosteler can no longer see it in feed
        hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
        client.force_login(hosteler)
        resp_feed = client.get(reverse("community:feed"))
        assert ticket.title not in resp_feed.content.decode()

    def test_similar_issues_endpoint(self, client):
        hostel = HostelFactory()
        user = UserFactory(role=Role.HOSTELER, hostel=hostel)
        cat = CategoryFactory(name="Electrical", allow_community=True)

        existing = TicketFactory(
            hostel=hostel,
            category=cat,
            visibility=TicketVisibility.HOSTEL,
            title="Corridor light flickering and sparks",
        )

        client.force_login(user)
        similar_url = reverse("community:similar")
        resp = client.get(similar_url, {"title": "light flickering", "category_id": cat.id})
        assert resp.status_code == 200
        assert existing.ticket_no in resp.content.decode()


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


@pytest.mark.django_db
class TestCriticalityAndStaffVisibility:
    def test_manage_criticality_admin_only(self, client):
        admin_user = UserFactory(role=Role.ADMIN)
        hosteler = UserFactory(role=Role.HOSTELER)

        # Hosteler denied
        client.force_login(hosteler)
        resp_denied = client.get(reverse("tickets:manage_criticality"))
        assert resp_denied.status_code == 403

        # Admin access granted
        client.force_login(admin_user)
        resp = client.get(reverse("tickets:manage_criticality"))
        assert resp.status_code == 200
        assert "Criticality Escalation Rules" in resp.content.decode()

        # Admin adds rule
        post_data = {
            "action": "add_rule",
            "min_reposts": 15,
            "bump_levels": 3,
            "force_priority": "",
            "notify_level": 3,
        }
        resp_add = client.post(reverse("tickets:manage_criticality"), post_data)
        assert resp_add.status_code == 302
        assert CriticalityRule.objects.filter(min_reposts=15, notify_level=3).exists()

        # Admin resets defaults
        resp_reset = client.post(reverse("tickets:manage_criticality"), {"action": "reset_defaults"})
        assert resp_reset.status_code == 302
        assert CriticalityRule.objects.filter(min_reposts=3).exists()
        assert CriticalityRule.objects.filter(min_reposts=6).exists()
        assert CriticalityRule.objects.filter(min_reposts=10).exists()

    def test_staff_dashboard_and_ticket_detail_panels(self, client):
        hostel = HostelFactory(name="Staff Hostel")
        warden = UserFactory(role=Role.WARDEN, hostel=hostel)
        reporter = UserFactory(role=Role.HOSTELER, hostel=hostel)
        peer = UserFactory(role=Role.HOSTELER, hostel=hostel, login_id="PEER_101", full_name="Peer Student")

        ticket = TicketFactory(
            hostel=hostel,
            reporter=reporter,
            visibility=TicketVisibility.HOSTEL,
            title="Shared Water Dispenser Leaking",
            repost_count=1,
            base_priority=Priority.LOW,
            priority=Priority.MEDIUM,
        )
        TicketRepost.objects.create(ticket=ticket, user=peer, note="Dispenser flooded room 102")

        client.force_login(warden)

        # 1. Staff dashboard shows most reported issue
        resp_dash = client.get(reverse("dashboard:index"))
        assert resp_dash.status_code == 200
        content_dash = resp_dash.content.decode()
        assert "Most-reported issues" in content_dash
        assert "Shared Water Dispenser Leaking" in content_dash

        # 2. Staff ticket detail shows Community Impact panel
        resp_detail = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
        assert resp_detail.status_code == 200
        content_detail = resp_detail.content.decode()
        assert "Community Impact" in content_detail
        assert "Peer Student" in content_detail
        assert "Dispenser flooded room 102" in content_detail
        assert "PEER_101" in content_detail
