import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.accounts.models import Role, ROLE_TO_LEVEL, User
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
