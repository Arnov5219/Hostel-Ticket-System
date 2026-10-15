import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role, StaffAuditLog, User
from apps.accounts.services.staff import (
    ActiveTicketsError,
    archive_staff,
    change_login_id,
    create_staff,
    deactivate_staff,
    edit_staff,
    reset_staff_password,
)
from apps.core.navigation import nav_for
from apps.core.permissions import Capability, has_capability
from apps.hostels.factories import HostelFactory
from apps.hostels.models import Hostel
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import (
    CommentReport,
    CommentScope,
    Priority,
    Status,
    Ticket,
    TicketComment,
    TicketVisibility,
)
from apps.tickets.services.community import add_community_comment
from apps.tickets.services.sla import hours_for


@pytest.fixture
def hostel_environment(db):
    hostel = HostelFactory(name="Tagore Bhavan", code="TB")
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, login_id="21BCS001")
    peer_hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, login_id="21BCS002")
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, login_id="TB_CARETAKER")
    warden = UserFactory(role=Role.WARDEN, hostel=hostel, login_id="TB_WARDEN")
    chief_warden = UserFactory(role=Role.CHIEF_WARDEN, login_id="CHIEF_WARDEN_MAIN")
    admin = UserFactory(role=Role.ADMIN, login_id="ADMIN_MAIN")
    category = CategoryFactory(allow_community=True)
    ticket = TicketFactory(
        hostel=hostel,
        reporter=hosteler,
        category=category,
        visibility=TicketVisibility.HOSTEL,
        status=Status.OPEN,
    )
    return {
        "hostel": hostel,
        "hosteler": hosteler,
        "peer_hosteler": peer_hosteler,
        "caretaker": caretaker,
        "warden": warden,
        "chief_warden": chief_warden,
        "admin": admin,
        "category": category,
        "ticket": ticket,
    }


# ==============================================================================
# 1. Route Permissions & Community Lockdown
# ==============================================================================
@pytest.mark.django_db
class TestRoutePermissionsAndCommunityLockdown:
    def test_hosteler_has_access_to_community_routes(self, client, hostel_environment):
        hosteler = hostel_environment["hosteler"]
        ticket = hostel_environment["ticket"]
        client.force_login(hosteler)

        # GET /community/
        assert client.get(reverse("community:feed")).status_code == 200

        # GET /community/feed/
        assert client.get(reverse("community:feed_partial")).status_code == 200

        # GET /tickets/<no>/community-comments/
        comments_url = reverse("tickets:community_comments", kwargs={"ticket_no": ticket.ticket_no})
        assert client.get(comments_url).status_code == 200

        # POST /tickets/<no>/community-comments/
        resp = client.post(comments_url, {"body": "Confirming this issue."})
        assert resp.status_code == 200

    def test_non_hostelers_denied_403_on_community_endpoints(self, client, hostel_environment):
        ticket = hostel_environment["ticket"]
        repost_url = reverse("tickets:repost", kwargs={"ticket_no": ticket.ticket_no})
        comments_url = reverse("tickets:community_comments", kwargs={"ticket_no": ticket.ticket_no})
        feed_url = reverse("community:feed")
        feed_partial_url = reverse("community:feed_partial")

        staff_roles = [
            hostel_environment["caretaker"],
            hostel_environment["warden"],
            hostel_environment["chief_warden"],
            hostel_environment["admin"],
        ]

        for staff in staff_roles:
            client.force_login(staff)

            assert client.get(feed_url).status_code == 403
            assert client.get(feed_partial_url).status_code == 403
            assert client.post(repost_url).status_code == 403
            assert client.get(comments_url).status_code == 403
            assert client.post(comments_url, {"body": "Staff test comment"}).status_code == 403


# ==============================================================================
# 2. Removed Routes Return 404
# ==============================================================================
@pytest.mark.django_db
class TestRemovedRoutesReturn404:
    def test_all_removed_routes_404(self, client, hostel_environment):
        admin = hostel_environment["admin"]
        client.force_login(admin)

        removed_urls = [
            "/manage/rooms/",
            "/manage/residents/",
            "/manage/routing/",
            "/hostels/options/floors/",
            "/hostels/options/rooms/",
        ]
        for url in removed_urls:
            assert client.get(url).status_code == 404, f"Expected 404 for {url}"


# ==============================================================================
# 3. Chief Warden Administrative Parity
# ==============================================================================
@pytest.mark.django_db
class TestChiefWardenAdministrativeParity:
    def test_chief_warden_capabilities(self, hostel_environment):
        cw = hostel_environment["chief_warden"]

        assert has_capability(cw, Capability.MANAGE_HOSTELS)
        assert has_capability(cw, Capability.MANAGE_STAFF)
        assert has_capability(cw, Capability.MANAGE_RESPONSIBILITY)
        assert has_capability(cw, Capability.MANAGE_TICKET_SETTINGS)
        assert has_capability(cw, Capability.VIEW_ALL_TICKETS)

        # Role identity preserved
        assert cw.role == Role.CHIEF_WARDEN
        assert cw.role != Role.ADMIN
        assert cw.escalation_level == 3

    def test_chief_warden_management_views_access(self, client, hostel_environment):
        cw = hostel_environment["chief_warden"]
        client.force_login(cw)

        assert client.get(reverse("hostels:manage_hostels")).status_code == 200
        assert client.get(reverse("hostels:manage_staff")).status_code == 200
        assert client.get(reverse("hostels:manage_responsibility")).status_code == 200
        assert client.get(reverse("tickets:manage_settings")).status_code == 200

    def test_chief_warden_cannot_manage_admin_users(self, client, hostel_environment):
        cw = hostel_environment["chief_warden"]
        admin = hostel_environment["admin"]
        client.force_login(cw)

        # Attempt to reset password of admin user -> 403 Forbidden
        url = reverse("hostels:reset_password", kwargs={"user_id": admin.id})
        resp = client.post(url, {"actor_password": "any"})
        assert resp.status_code == 403


# ==============================================================================
# 4. Staff Management Lifecycle & Audit
# ==============================================================================
@pytest.mark.django_db
class TestStaffManagementLifecycle:
    def test_create_and_edit_staff(self, hostel_environment):
        admin = hostel_environment["admin"]
        hostel = hostel_environment["hostel"]

        staff, temp_pw = create_staff(
            actor=admin,
            role=Role.CARETAKER,
            login_id="CT_NEW_01",
            full_name="New Caretaker",
            password="SecurePass@123",
            phone="9876543210",
            email="caretaker@hostel.edu",
            hostel=hostel,
        )
        assert staff.login_id == "CT_NEW_01"
        assert staff.hostel == hostel
        assert staff.escalation_level == 1
        assert staff.is_active is True

        # Audit log verification
        log = StaffAuditLog.objects.filter(target=staff, action="CREATED").first()
        assert log is not None
        assert log.actor == admin

        # Edit staff
        edited = edit_staff(
            actor=admin,
            target=staff,
            full_name="Updated Caretaker Name",
            phone="9999999999",
            email="newemail@hostel.edu",
        )
        assert edited.full_name == "Updated Caretaker Name"
        assert edited.phone == "9999999999"

    def test_change_login_id(self, hostel_environment):
        admin = hostel_environment["admin"]
        staff = hostel_environment["caretaker"]

        updated = change_login_id(admin, staff, "CT_RENAMED")
        assert updated.login_id == "CT_RENAMED"

        log = StaffAuditLog.objects.filter(target=staff, action="LOGIN_ID_CHANGED").first()
        assert log is not None
        assert log.details["to"] == "CT_RENAMED"

    def test_reset_staff_password_generates_one_time_temp(self, hostel_environment):
        admin = hostel_environment["admin"]
        admin.set_password("AdminPass123!")
        admin.save()
        staff = hostel_environment["caretaker"]
        old_version = staff.session_version

        temp_pw = reset_staff_password(actor=admin, target=staff, actor_password="AdminPass123!")
        staff.refresh_from_db()

        assert len(temp_pw) >= 12
        assert staff.check_password(temp_pw)
        assert staff.must_change_password is True
        assert staff.session_version == old_version + 1
        assert staff.last_password_reset_by == admin
        assert staff.last_password_reset_at is not None

        # Verify plaintext password is NEVER stored in audit log
        log = StaffAuditLog.objects.filter(target=staff, action="PASSWORD_RESET").first()
        assert log is not None
        assert temp_pw not in str(log.details)

    def test_deactivate_staff_guard_and_reassignment(self, hostel_environment):
        admin = hostel_environment["admin"]
        hostel = hostel_environment["hostel"]
        staff = hostel_environment["caretaker"]
        replacement = UserFactory(role=Role.CARETAKER, hostel=hostel, login_id="CT_REPLACE_01")

        # Staff has 1 active ticket assigned
        ticket = hostel_environment["ticket"]
        ticket.assigned_to = staff
        ticket.status = Status.IN_PROGRESS
        ticket.save()

        # Attempt deactivation without replacement -> ActiveTicketsError
        with pytest.raises(ActiveTicketsError) as exc:
            deactivate_staff(actor=admin, target=staff, reason="Leaving job", replacement=None)
        assert "has 1 active ticket" in str(exc.value)

        # Deactivation WITH replacement and NO reason -> succeeds and reassigns atomically
        deactivated = deactivate_staff(
            actor=admin,
            target=staff,
            reason="",
            replacement=replacement,
        )
        assert deactivated.is_active is False

        ticket.refresh_from_db()
        assert ticket.assigned_to == replacement

        # Verify ticket activity logged with fallback note
        reassign_act = ticket.activities.filter(action="REASSIGNED").last()
        assert reassign_act is not None
        assert str(replacement.login_id) in reassign_act.to_value

        # Archive staff without reason -> succeeds without ValidationError
        archived = archive_staff(admin, staff, reason="")
        assert archived.archived_at is not None
        assert archived.is_active is False


# ==============================================================================
# 5. Resident Comment Self-Moderation
# ==============================================================================
@pytest.mark.django_db
class TestResidentSelfModeration:
    def test_comment_reporting_and_auto_hide_at_three(self, client, hostel_environment):
        ticket = hostel_environment["ticket"]
        author = hostel_environment["hosteler"]
        reporter1 = hostel_environment["peer_hosteler"]
        reporter2 = UserFactory(role=Role.HOSTELER, hostel=ticket.hostel, login_id="21BCS003")
        reporter3 = UserFactory(role=Role.HOSTELER, hostel=ticket.hostel, login_id="21BCS004")

        # Author creates community comment
        comment = add_community_comment(author, ticket, "Notice on 2nd floor.")
        assert comment.is_hidden is False

        # Report 1
        client.force_login(reporter1)
        resp1 = client.post(reverse("community:report_comment", kwargs={"comment_id": comment.id}))
        assert resp1.status_code == 200
        comment.refresh_from_db()
        assert comment.is_hidden is False

        # Report 2
        client.force_login(reporter2)
        resp2 = client.post(reverse("community:report_comment", kwargs={"comment_id": comment.id}))
        assert resp2.status_code == 200
        comment.refresh_from_db()
        assert comment.is_hidden is False

        # Report 3 -> auto-hidden
        client.force_login(reporter3)
        resp3 = client.post(reverse("community:report_comment", kwargs={"comment_id": comment.id}))
        assert resp3.status_code == 200
        comment.refresh_from_db()
        assert comment.is_hidden is True
        assert comment.hidden_reason == "Reported by residents"


# ==============================================================================
# 6. Ticket Settings Page
# ==============================================================================
@pytest.mark.django_db
class TestTicketSettingsPage:
    def test_ticket_settings_crud_actions(self, client, hostel_environment):
        admin = hostel_environment["admin"]
        client.force_login(admin)

        # GET settings page
        resp = client.get(reverse("tickets:manage_settings"))
        assert resp.status_code == 200

        # POST add tag
        tag_post = {"action": "add_tag", "name": "UrgentWater", "color": "#ff0000"}
        resp_tag = client.post(reverse("tickets:manage_settings"), tag_post)
        assert resp_tag.status_code == 302
        from apps.tickets.models import Tag
        assert Tag.objects.filter(name="UrgentWater").exists()

        # POST add criticality rule
        rule_post = {
            "action": "add_rule",
            "min_reposts": 8,
            "bump_levels": 2,
            "force_priority": "URGENT",
            "notify_level": 2,
        }
        resp_rule = client.post(reverse("tickets:manage_settings"), rule_post)
        assert resp_rule.status_code == 302
        from apps.tickets.models import CriticalityRule
        assert CriticalityRule.objects.filter(min_reposts=8).exists()


# ==============================================================================
# 7. Fallback SLA Defaults
# ==============================================================================
@pytest.mark.django_db
class TestSlaFallbackDefaults:
    def test_hours_for_fallback_table(self):
        # In a blank DB without custom SLAPolicy rows, hours_for still provides correct SLA defaults
        assert hours_for(Priority.URGENT, 1) == 2
        assert hours_for(Priority.HIGH, 1) == 8
        assert hours_for(Priority.MEDIUM, 1) == 24
        assert hours_for(Priority.LOW, 1) == 48

        assert hours_for(Priority.URGENT, 2) == 2
        assert hours_for(Priority.HIGH, 3) == 12
        assert hours_for(Priority.MEDIUM, 4) == 24


# ==============================================================================
# 8. Unified Navigation Structure
# ==============================================================================
@pytest.mark.django_db
class TestUnifiedNavigation:
    def test_hosteler_navigation(self, hostel_environment):
        hosteler = hostel_environment["hosteler"]
        nav = nav_for(hosteler)
        sidebar_keys = [item.key for item in nav["sidebar_items"]]

        assert "home" in sidebar_keys
        assert "community" in sidebar_keys
        assert "tickets" in sidebar_keys
        assert "manage_hostels" not in sidebar_keys

    def test_staff_navigation_excludes_community(self, hostel_environment):
        caretaker = hostel_environment["caretaker"]
        nav = nav_for(caretaker)
        sidebar_keys = [item.key for item in nav["sidebar_items"]]
        mobile_keys = [item.key for item in nav["mobile_bar_items"]]

        assert "community" not in sidebar_keys
        assert "community" not in mobile_keys
        assert "home" in sidebar_keys
        assert "tickets" in sidebar_keys
        assert "kanban" in sidebar_keys

    def test_admin_navigation_includes_cleaned_manage_items(self, hostel_environment):
        admin = hostel_environment["admin"]
        nav = nav_for(admin)
        sidebar_keys = [item.key for item in nav["sidebar_items"]]

        assert "manage_hostels" in sidebar_keys
        assert "manage_staff" in sidebar_keys
        assert "manage_responsibility" in sidebar_keys
        assert "manage_settings" in sidebar_keys

        # Ensure obsolete subnavs are gone
        assert "manage_rooms" not in sidebar_keys
        assert "manage_residents" not in sidebar_keys
        assert "manage_routing" not in sidebar_keys
