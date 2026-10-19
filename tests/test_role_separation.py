import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import ROLE_TO_LEVEL, Role, User
from apps.accounts.services.staff import deactivate_staff
from apps.core.permissions import ADMIN_ONLY_CAPABILITIES, Capability, has_capability
from apps.hostels.models import Hostel
from apps.tickets.models import ActivityAction, Category, Ticket, TicketActivity
from apps.tickets.services.escalation import escalate, find_escalation_assignee


@pytest.fixture
def role_users(db):
    hostel = Hostel.objects.create(name="Mandakini Hostel", code="MH")
    hosteler = User.objects.create_user(
        login_id="S100",
        full_name="Student One",
        role=Role.HOSTELER,
        hostel=hostel,
        password="password123",
    )
    caretaker = User.objects.create_user(
        login_id="C100",
        full_name="Caretaker One",
        role=Role.CARETAKER,
        hostel=hostel,
        password="password123",
    )
    warden = User.objects.create_user(
        login_id="W100",
        full_name="Warden One",
        role=Role.WARDEN,
        hostel=hostel,
        password="password123",
    )
    chief_warden = User.objects.create_user(
        login_id="CW100",
        full_name="Chief Warden One",
        role=Role.CHIEF_WARDEN,
        password="password123",
    )
    dean = User.objects.create_user(
        login_id="D100",
        full_name="Dean One",
        role=Role.DEAN,
        password="password123",
    )
    admin = User.objects.create_user(
        login_id="A100",
        full_name="Admin One",
        role=Role.ADMIN,
        is_staff=True,
        password="password123",
    )
    superuser = User.objects.create_user(
        login_id="SU100",
        full_name="Super User",
        role=Role.CHIEF_WARDEN,
        is_superuser=True,
        is_staff=True,
        password="password123",
    )
    return {
        "hostel": hostel,
        "hosteler": hosteler,
        "caretaker": caretaker,
        "warden": warden,
        "chief_warden": chief_warden,
        "dean": dean,
        "admin": admin,
        "superuser": superuser,
    }


@pytest.mark.django_db
class TestRoleHierarchyAndLevels:
    def test_role_to_level_mapping(self, role_users):
        assert ROLE_TO_LEVEL[Role.CARETAKER] == 1
        assert ROLE_TO_LEVEL[Role.WARDEN] == 2
        assert ROLE_TO_LEVEL[Role.CHIEF_WARDEN] == 3
        assert ROLE_TO_LEVEL[Role.DEAN] == 4
        assert Role.ADMIN not in ROLE_TO_LEVEL
        assert Role.HOSTELER not in ROLE_TO_LEVEL

        dean = role_users["dean"]
        admin = role_users["admin"]
        assert dean.escalation_level == 4
        assert admin.escalation_level is None
        assert dean.is_dean is True
        assert dean.is_admin is False
        assert admin.is_admin is True
        assert admin.is_dean is False


@pytest.mark.django_db
class TestCapabilitySeparation:
    def test_admin_only_capabilities_strictly_admin(self, role_users):
        admin = role_users["admin"]
        dean = role_users["dean"]
        cw = role_users["chief_warden"]
        warden = role_users["warden"]

        for cap in ADMIN_ONLY_CAPABILITIES:
            assert has_capability(admin, cap) is True, f"Admin must have {cap}"
            assert has_capability(dean, cap) is False, f"Dean must NOT have {cap}"
            assert has_capability(cw, cap) is False, f"Chief Warden must NOT have {cap}"
            assert has_capability(warden, cap) is False, f"Warden must NOT have {cap}"

    def test_admin_cannot_escalate_or_change_status(self, role_users):
        admin = role_users["admin"]
        dean = role_users["dean"]

        # Admin cannot perform operational ticket workflow
        assert has_capability(admin, Capability.CHANGE_STATUS) is False
        assert has_capability(admin, Capability.ESCALATE) is False

        # Dean CAN change status & reassign, but does not escalate (already top of chain L4)
        assert has_capability(dean, Capability.CHANGE_STATUS) is True
        assert has_capability(dean, Capability.REASSIGN_TICKET) is True
        assert has_capability(dean, Capability.ESCALATE) is False


@pytest.mark.django_db
class TestEscalationToDean:
    def test_level_4_escalates_to_dean(self, role_users):
        hostel = role_users["hostel"]
        dean = role_users["dean"]
        cw = role_users["chief_warden"]

        category, _ = Category.objects.get_or_create(name="Electrical")
        ticket = Ticket.objects.create(
            ticket_no="TICK-ESC-1",
            title="Broken switchboard",
            description="Sparking",
            category=category,
            hostel=hostel,
            reporter=role_users["hosteler"],
            current_level=3,
        )

        assignee, is_fallback = find_escalation_assignee(ticket, 4)
        assert assignee == dean
        assert is_fallback is False

        escalate(ticket, actor=cw)
        ticket.refresh_from_db()
        assert ticket.current_level == 4
        assert ticket.assigned_to == dean

    def test_level_4_fallback_to_admin_when_no_dean(self, role_users):
        hostel = role_users["hostel"]
        role_users["dean"].delete()
        admin = role_users["admin"]
        cw = role_users["chief_warden"]

        category, _ = Category.objects.get_or_create(name="Electrical")
        ticket = Ticket.objects.create(
            ticket_no="TICK-ESC-2",
            title="Transformer blast",
            description="Total power failure",
            category=category,
            hostel=hostel,
            reporter=role_users["hosteler"],
            current_level=3,
        )

        assignee, is_fallback = find_escalation_assignee(ticket, 4)
        assert assignee == admin
        assert is_fallback is True

        escalate(ticket, actor=cw)
        ticket.refresh_from_db()
        assert ticket.current_level == 4
        assert ticket.assigned_to == admin

        # Check fallback activity logged
        fallback_log = TicketActivity.objects.filter(
            ticket=ticket, action=ActivityAction.LEVEL4_FALLBACK
        ).exists()
        assert fallback_log is True


@pytest.mark.django_db
class TestAdminOperationalRestrictions:
    def test_admin_cannot_post_comment_or_status(self, client, role_users):
        admin = role_users["admin"]
        category, _ = Category.objects.get_or_create(name="Plumbing")
        ticket = Ticket.objects.create(
            ticket_no="TICK-RESTRICT-1",
            title="Water leakage",
            description="Water leaking in corridor",
            category=category,
            hostel=role_users["hostel"],
            reporter=role_users["hosteler"],
            status="OPEN",
        )

        client.force_login(admin)

        # Status change forbidden
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": "IN_PROGRESS"},
        )
        assert res.status_code == 403

        # Comment forbidden
        res = client.post(
            reverse("tickets:comment", kwargs={"ticket_no": ticket.ticket_no}),
            {"content": "Admin commenting here"},
        )
        assert res.status_code == 403


@pytest.mark.django_db
class TestStaffDeactivationProtection:
    def test_cannot_deactivate_last_admin(self, role_users):
        admin = role_users["admin"]
        superuser = role_users["superuser"]
        # Only 1 admin exists in the system (A100)
        with pytest.raises(ValidationError, match="Cannot deactivate the last active Admin."):
            deactivate_staff(actor=superuser, target=admin)

    def test_cannot_deactivate_last_dean_without_fallback_flag(self, role_users):
        dean = role_users["dean"]
        admin = role_users["admin"]
        with pytest.raises(ValidationError, match="Cannot deactivate the last active Dean without admin fallback confirmation."):
            deactivate_staff(actor=admin, target=dean, allow_admin_fallback=False)

        # With fallback allowed, it succeeds
        deactivate_staff(actor=admin, target=dean, allow_admin_fallback=True)
        dean.refresh_from_db()
        assert dean.is_active is False


@pytest.mark.django_db
class TestNavigationMatrix:
    def test_navigation_roles(self, role_users):
        from apps.core.navigation import nav_for

        admin_nav = nav_for(role_users["admin"])
        dean_nav = nav_for(role_users["dean"])
        cw_nav = nav_for(role_users["chief_warden"])
        warden_nav = nav_for(role_users["warden"])

        admin_keys = [item.key for item in admin_nav["sidebar_items"]]
        dean_keys = [item.key for item in dean_nav["sidebar_items"]]
        cw_keys = [item.key for item in cw_nav["sidebar_items"]]
        warden_keys = [item.key for item in warden_nav["sidebar_items"]]

        # Admin: has manage items and trash, but NO kanban
        assert "manage_hostels" in admin_keys
        assert "manage_staff" in admin_keys
        assert "manage_responsibility" in admin_keys
        assert "manage_settings" not in admin_keys
        assert "trash" in admin_keys
        assert "kanban" not in admin_keys

        # Dean & Chief Warden: operational workflow (kanban), NO manage items, NO trash
        for keys in [dean_keys, cw_keys]:
            assert "kanban" in keys
            assert "manage_hostels" not in keys
            assert "manage_staff" not in keys
            assert "manage_responsibility" not in keys
            assert "manage_settings" not in keys
            assert "trash" not in keys

        # Warden: has kanban, NO trash, NO manage items
        assert "kanban" in warden_keys
        assert "trash" not in warden_keys
        assert "manage_hostels" not in warden_keys


@pytest.mark.django_db
class TestManageRouteSecurity:
    def test_non_admin_cannot_access_manage_routes(self, client, role_users):
        manage_routes = [
            "/manage/hostels/",
            "/manage/staff/",
            "/manage/responsibility/",
            "/manage/trash/",
        ]

        # Admin has 200 on all
        client.force_login(role_users["admin"])
        for route in manage_routes:
            res = client.get(route)
            assert res.status_code == 200, f"Admin must have 200 on {route}, got {res.status_code}"

        # Dean gets 403 on all
        client.force_login(role_users["dean"])
        for route in manage_routes:
            res = client.get(route)
            assert res.status_code == 403, f"Dean must be blocked (403) from {route}, got {res.status_code}"

        # Chief Warden gets 403 on all
        client.force_login(role_users["chief_warden"])
        for route in manage_routes:
            res = client.get(route)
            assert res.status_code == 403, f"Chief Warden must be blocked (403) from {route}, got {res.status_code}"

        # Hosteler gets 403 on all
        client.force_login(role_users["hosteler"])
        for route in manage_routes:
            res = client.get(route)
            assert res.status_code == 403, f"Hosteler must be blocked (403) from {route}, got {res.status_code}"


@pytest.mark.django_db
class TestDemoAccountsManagement:
    def test_seed_demo_accounts_creates_l0_to_l5(self, settings):
        from django.core.management import call_command

        from apps.accounts.models import Role, User

        settings.DEBUG = True
        call_command("seed_demo_accounts")

        expected_roles = {
            "L0": (Role.HOSTELER, None),
            "L1": (Role.CARETAKER, 1),
            "L2": (Role.WARDEN, 2),
            "L3": (Role.CHIEF_WARDEN, 3),
            "L4": (Role.DEAN, 4),
            "L5": (Role.ADMIN, None),
        }

        for login_id, (role, level) in expected_roles.items():
            u = User.objects.get(login_id=login_id)
            assert u.role == role
            assert u.escalation_level == level
            assert u.is_demo is True
            assert u.check_password("me1234") is True

    def test_seed_demo_accounts_guard_in_production(self, settings):
        import os

        from django.core.management import call_command
        from django.core.management.base import CommandError

        settings.DEBUG = False
        old_env = os.environ.get("ENABLE_DEMO_ACCOUNTS")
        try:
            if "ENABLE_DEMO_ACCOUNTS" in os.environ:
                del os.environ["ENABLE_DEMO_ACCOUNTS"]
            with pytest.raises(CommandError, match="Refusing to seed demo accounts in non-DEBUG environment"):
                call_command("seed_demo_accounts")
        finally:
            if old_env is not None:
                os.environ["ENABLE_DEMO_ACCOUNTS"] = old_env

    def test_purge_demo_accounts_dry_run_and_confirm(self, settings):
        from django.core.management import call_command

        from apps.accounts.models import User

        settings.DEBUG = True
        call_command("seed_demo_accounts")
        assert User.objects.filter(is_demo=True).count() >= 6

        # Dry run does not delete
        call_command("purge_demo_accounts")
        assert User.objects.filter(is_demo=True).count() >= 6

        # With confirm, deletes demo accounts
        call_command("purge_demo_accounts", confirm=True)
        assert User.objects.filter(is_demo=True).count() == 0

    def test_deploy_check_catches_demo_accounts_in_prod(self, settings):
        from apps.accounts.apps import check_demo_accounts_in_production
        from apps.accounts.models import User

        User.objects.create_user(
            login_id="L0",
            role="HOSTELER",
            password="password123",
            is_demo=True,
        )

        settings.DEBUG = False
        import os
        old_env = os.environ.get("ALLOW_DEMO_ACCOUNTS")
        try:
            if "ALLOW_DEMO_ACCOUNTS" in os.environ:
                del os.environ["ALLOW_DEMO_ACCOUNTS"]

            errors = check_demo_accounts_in_production(None)
            assert len(errors) == 1
            assert errors[0].id == "accounts.E001"

            # When ALLOW_DEMO_ACCOUNTS=1, it should not error
            os.environ["ALLOW_DEMO_ACCOUNTS"] = "1"
            errors = check_demo_accounts_in_production(None)
            assert len(errors) == 0
        finally:
            if old_env is not None:
                os.environ["ALLOW_DEMO_ACCOUNTS"] = old_env
            elif "ALLOW_DEMO_ACCOUNTS" in os.environ:
                del os.environ["ALLOW_DEMO_ACCOUNTS"]


