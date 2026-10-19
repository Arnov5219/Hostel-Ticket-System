import os
from pathlib import Path

import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.notifications.models import Notification, NotificationVerb
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import (
    ActivityAction,
    CommentScope,
    Priority,
    Status,
    Ticket,
    TicketActivity,
    TicketComment,
    TicketRepost,
)
from apps.tickets.services.deletion import can_delete, soft_delete


@pytest.fixture
def removal_fixture(db):
    hostel = HostelFactory(name="Removal Test Hostel", code="RTH")
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, login_id="hosteler_removal")
    peer = UserFactory(role=Role.HOSTELER, hostel=hostel, login_id="peer_removal")
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, login_id="caretaker_removal")
    warden = UserFactory(role=Role.WARDEN, hostel=hostel, login_id="warden_removal")
    chief_warden = UserFactory(role=Role.CHIEF_WARDEN, login_id="cw_removal")
    admin = UserFactory(role=Role.ADMIN, login_id="admin_removal")
    category = CategoryFactory(name="Electrical RTH")
    ticket = TicketFactory(
        hostel=hostel,
        reporter=hosteler,
        category=category,
        title="Legacy Light Issue",
        priority=Priority.MEDIUM,
        status=Status.OPEN,
    )
    return {
        "hostel": hostel,
        "hosteler": hosteler,
        "peer": peer,
        "caretaker": caretaker,
        "warden": warden,
        "chief_warden": chief_warden,
        "admin": admin,
        "category": category,
        "ticket": ticket,
    }


# ==============================================================================
# a) Route Matrix Test (all removed routes return 404 for all roles)
# ==============================================================================
@pytest.mark.django_db
class TestRemovedRouteMatrix:
    REMOVED_PATHS = [
        "/community/",
        "/community/feed/",
        "/community/similar-issues/",
        "/manage/criticality/",
    ]

    def test_removed_routes_404_matrix(self, client, removal_fixture):
        ticket = removal_fixture["ticket"]
        all_removed_paths = self.REMOVED_PATHS + [
            f"/tickets/{ticket.ticket_no}/repost/",
            f"/tickets/{ticket.ticket_no}/community-comments/",
        ]

        roles = [
            ("anonymous", None),
            ("hosteler", removal_fixture["hosteler"]),
            ("caretaker", removal_fixture["caretaker"]),
            ("warden", removal_fixture["warden"]),
            ("chief_warden", removal_fixture["chief_warden"]),
            ("admin", removal_fixture["admin"]),
        ]

        for role_name, user in roles:
            if user:
                client.force_login(user)
            else:
                client.logout()

            for path in all_removed_paths:
                # Test GET
                resp_get = client.get(path)
                assert resp_get.status_code == 404, (
                    f"Expected 404 for GET {path} as {role_name}, got {resp_get.status_code}"
                )
                # Test POST
                resp_post = client.post(path, {})
                assert resp_post.status_code == 404, (
                    f"Expected 404 for POST {path} as {role_name}, got {resp_post.status_code}"
                )


# ==============================================================================
# b) Grep Guard Test
# ==============================================================================
def test_grep_guard_no_community_terms():
    """
    Fails if 'community', 'repost', 'criticality', or 'affected_count' appear
    in apps/, templates/, or static/, except in migrations and model files
    carrying the DEPRECATED comment.
    """
    base_dir = Path(__file__).resolve().parent.parent
    target_dirs = [base_dir / "apps", base_dir / "templates", base_dir / "static"]
    forbidden_terms = ["community", "repost", "criticality", "affected_count"]
    deprecated_marker = "# DEPRECATED: Community removed, kept for historical data, no UI"

    violations = []

    for target_dir in target_dirs:
        for root, dirs, files in os.walk(target_dir):
            root_path = Path(root)
            # Skip migrations directories
            if "migrations" in root_path.parts:
                continue
            if "__pycache__" in root_path.parts:
                continue

            for file in files:
                file_path = root_path / file
                # Ignore binary / media files
                if file_path.suffix in [".pyc", ".png", ".jpg", ".jpeg", ".ico", ".webmanifest"]:
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # If this is a model file carrying the DEPRECATED comment, it is exempt
                if deprecated_marker in content and file_path.name in ["models.py", "admin.py"]:
                    continue

                content_lower = content.lower()
                for term in forbidden_terms:
                    if term in content_lower:
                        # Find line numbers
                        for line_no, line in enumerate(content.splitlines(), start=1):
                            if term in line.lower():
                                rel_path = file_path.relative_to(base_dir)
                                violations.append(f"{rel_path}:{line_no} contains '{term}': {line.strip()[:80]}")

    assert not violations, "Grep guard violations found:\n" + "\n".join(violations)


# ==============================================================================
# c) Legacy Data Test
# ==============================================================================
@pytest.mark.django_db
class TestLegacyDataRendering:
    def test_legacy_data_does_not_break_rendering(self, client, removal_fixture):
        ticket = removal_fixture["ticket"]
        hosteler = removal_fixture["hosteler"]
        peer = removal_fixture["peer"]
        warden = removal_fixture["warden"]

        # 1. Create legacy TicketRepost
        TicketRepost.objects.create(ticket=ticket, user=peer, note="Legacy repost note")
        ticket.repost_count = 3
        ticket.save(update_fields=["repost_count"])

        # 2. Create legacy COMMUNITY comment
        TicketComment.objects.create(
            ticket=ticket,
            author=peer,
            body="Legacy community comment text",
            scope=CommentScope.COMMUNITY,
        )

        # 3. Create regular comment
        TicketComment.objects.create(
            ticket=ticket,
            author=hosteler,
            body="Legitimate reporter message",
            scope=CommentScope.PRIVATE,
        )

        # 4. Create legacy activities
        TicketActivity.objects.create(
            ticket=ticket,
            actor=peer,
            action="REPOSTED",
            note="Legacy repost activity",
        )
        TicketActivity.objects.create(
            ticket=ticket,
            actor=peer,
            action="COMMUNITY_COMMENT",
            note="Legacy community comment activity",
        )
        TicketActivity.objects.create(
            ticket=ticket,
            actor=hosteler,
            action=ActivityAction.COMMENTED,
            note="Legitimate activity note",
        )

        # Test Hosteler Ticket List
        client.force_login(hosteler)
        resp_list = client.get(reverse("tickets:list"))
        assert resp_list.status_code == 200
        content_list = resp_list.content.decode()
        assert "Affected" not in content_list
        assert "repost" not in content_list.lower()

        # Test Hosteler Ticket Detail
        resp_detail = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
        assert resp_detail.status_code == 200
        content_detail = resp_detail.content.decode()
        assert "Community Impact" not in content_detail
        assert "Legacy community comment text" not in content_detail
        assert "Legacy repost note" not in content_detail
        assert "Legitimate reporter message" not in content_detail
        assert "Legitimate activity note" in content_detail
        assert ticket.description in content_detail

        # Test Staff Kanban
        client.force_login(warden)
        resp_kanban = client.get(reverse("tickets:kanban"))
        assert resp_kanban.status_code == 200
        content_kanban = resp_kanban.content.decode()
        assert "affected" not in content_kanban.lower()

        # Test Staff Dashboard
        resp_dash = client.get(reverse("dashboard:index"))
        assert resp_dash.status_code == 200
        content_dash = resp_dash.content.decode()
        assert "Most-reported issues" not in content_dash

        # Test Hosteler Home
        client.force_login(hosteler)
        resp_home = client.get(reverse("core:home"), follow=True)
        assert resp_home.status_code == 200
        content_home = resp_home.content.decode()
        assert "Community" not in content_home
        assert "feed" not in content_home.lower()


# ==============================================================================
# d) Priority Test
# ==============================================================================
@pytest.mark.django_db
class TestPriorityHandling:
    def test_new_tickets_use_priority_only(self, client, removal_fixture):
        hosteler = removal_fixture["hosteler"]
        category = removal_fixture["category"]
        client.force_login(hosteler)

        resp = client.post(
            reverse("tickets:create"),
            {
                "title": "Broken window hinge",
                "room_number": "101",
                "description": "Window rattles in heavy wind.",
                "category": category.id,
                "hostel": hosteler.hostel.id,
                "priority": Priority.HIGH,
            },
        )
        assert resp.status_code == 302
        new_ticket = Ticket.objects.get(title="Broken window hinge")
        assert new_ticket.priority == Priority.HIGH
        assert new_ticket.base_priority == Priority.HIGH
        assert new_ticket.visibility == "PRIVATE"

    def test_existing_priority_unchanged(self, removal_fixture):
        ticket = removal_fixture["ticket"]
        ticket.priority = Priority.URGENT
        ticket.base_priority = Priority.LOW
        ticket.save()

        # Verify priority is preserved and no recomputation alters it
        ticket.refresh_from_db()
        assert ticket.priority == Priority.URGENT
        assert ticket.base_priority == Priority.LOW


# ==============================================================================
# e) Notification Test
# ==============================================================================
@pytest.mark.django_db
class TestNotificationExclusion:
    def test_legacy_notifications_excluded_from_list_and_count(self, client, removal_fixture):
        hosteler = removal_fixture["hosteler"]
        ticket = removal_fixture["ticket"]

        # Create legacy notifications
        Notification.all_objects.create(
            recipient=hosteler,
            ticket=ticket,
            verb="REPOSTED",
            message="Your ticket was reposted.",
            is_read=False,
        )
        Notification.all_objects.create(
            recipient=hosteler,
            ticket=ticket,
            verb="COMMUNITY_COMMENT",
            message="Someone commented on your ticket.",
            is_read=False,
        )
        Notification.all_objects.create(
            recipient=hosteler,
            ticket=ticket,
            verb="PRIORITY_RAISED",
            message="Priority auto-raised by reposts.",
            is_read=False,
        )
        Notification.all_objects.create(
            recipient=hosteler,
            ticket=ticket,
            verb="CRITICAL_ISSUE",
            message="Critical threshold crossed.",
            is_read=False,
        )

        # Create 1 valid notification
        valid_notif = Notification.objects.create(
            recipient=hosteler,
            ticket=ticket,
            verb=NotificationVerb.STATUS_CHANGED,
            message="Ticket status changed to Assigned.",
            is_read=False,
        )

        # Active notifications query should only have 1
        active_notifs = Notification.objects.filter(recipient=hosteler)
        assert active_notifs.count() == 1
        assert active_notifs.first() == valid_notif

        # Notification list view
        client.force_login(hosteler)
        resp = client.get(reverse("notifications:list"))
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Ticket status changed to Assigned." in content
        assert "Your ticket was reposted." not in content
        assert "Someone commented on your ticket." not in content
        assert "Priority auto-raised by reposts." not in content


# ==============================================================================
# f) Delete Ticket Without Repost Conditions
# ==============================================================================
@pytest.mark.django_db
class TestDeleteWithoutRepostConditions:
    def test_hosteler_can_delete_with_reposts_present(self, removal_fixture):
        hosteler = removal_fixture["hosteler"]
        peer = removal_fixture["peer"]
        ticket = removal_fixture["ticket"]

        # Ticket has reposts
        TicketRepost.objects.create(ticket=ticket, user=peer, note="Me too")
        ticket.repost_count = 10
        ticket.save()

        # can_delete allows hosteler deletion when OPEN and no staff comments
        allowed, reason = can_delete(hosteler, ticket)
        assert allowed is True
        assert reason == ""

        # Perform soft delete
        soft_delete(ticket, actor=hosteler, reason="No longer needed")
        ticket.refresh_from_db()
        assert ticket.is_deleted is True
        assert ticket.delete_reason == "No longer needed"
