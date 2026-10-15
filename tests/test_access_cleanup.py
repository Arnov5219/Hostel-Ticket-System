import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role, StaffAuditLog
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
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import (
    Priority,
    Status,
    TicketVisibility,
)
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
    category = CategoryFactory()
    ticket = TicketFactory(
        hostel=hostel,
        reporter=hosteler,
        category=category,
        visibility=TicketVisibility.PRIVATE,
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
# 3. Chief Warden Admin Controls Stripped (Section 2 & 7.2)
# ==============================================================================
@pytest.mark.django_db
class TestChiefWardenAdministrativeParity:
    def test_chief_warden_capabilities(self, hostel_environment):
        cw = hostel_environment["chief_warden"]
        admin = hostel_environment["admin"]

        # Admin controls stripped from Chief Warden
        assert not has_capability(cw, Capability.MANAGE_HOSTELS)
        assert not has_capability(cw, Capability.MANAGE_STAFF)
        assert not has_capability(cw, Capability.MANAGE_RESPONSIBILITY)
        assert not has_capability(cw, Capability.MANAGE_TICKET_SETTINGS)
        assert has_capability(cw, Capability.VIEW_ALL_TICKETS)

        # Admin holds the admin capabilities
        assert has_capability(admin, Capability.MANAGE_HOSTELS)
        assert has_capability(admin, Capability.MANAGE_STAFF)
        assert has_capability(admin, Capability.MANAGE_RESPONSIBILITY)
        assert has_capability(admin, Capability.MANAGE_TICKET_SETTINGS)

        # Role identity preserved
        assert cw.role == Role.CHIEF_WARDEN
        assert cw.role != Role.ADMIN
        assert cw.escalation_level == 3
        assert admin.escalation_level is None

    def test_chief_warden_management_views_access(self, client, hostel_environment):
        cw = hostel_environment["chief_warden"]
        admin = hostel_environment["admin"]

        # Chief Warden is blocked (403) from /manage/*
        client.force_login(cw)
        assert client.get(reverse("hostels:manage_hostels")).status_code == 403
        assert client.get(reverse("hostels:manage_staff")).status_code == 403
        assert client.get(reverse("hostels:manage_responsibility")).status_code == 403
        assert client.get(reverse("tickets:manage_settings")).status_code == 403

        # Admin has 200 on /manage/*
        client.force_login(admin)
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
# 5. Ticket Settings Page
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


# ==============================================================================
# 6. Fallback SLA Defaults
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
# 7. Unified Navigation Structure
# ==============================================================================
@pytest.mark.django_db
class TestUnifiedNavigation:
    def test_hosteler_navigation(self, hostel_environment):
        hosteler = hostel_environment["hosteler"]
        nav = nav_for(hosteler)
        sidebar_keys = [item.key for item in nav["sidebar_items"]]

        assert "home" in sidebar_keys
        assert "community" not in sidebar_keys
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
