import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.tickets.factories import CategoryFactory
from apps.tickets.models import ActivityAction, Status, Ticket, TicketActivity
from apps.tickets.services.numbering import generate_ticket_number


@pytest.fixture
def ticket_env():
    hostel = HostelFactory(code="BH-TEST", name="Test Hostel")
    category = CategoryFactory(name="Electrical")

    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="pwd")
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="pwd", escalation_level=1)
    warden = UserFactory(role=Role.WARDEN, hostel=hostel, password="pwd", escalation_level=2)
    chief_warden = UserFactory(role=Role.CHIEF_WARDEN, password="pwd", escalation_level=3)
    dean = UserFactory(role=Role.DEAN, password="pwd", escalation_level=4)
    admin = UserFactory(role=Role.ADMIN, password="pwd", is_staff=True, is_superuser=True)

    ticket = Ticket.objects.create(
        ticket_no=generate_ticket_number(),
        title="Switch sparking",
        description="Room 101 sparking switch",
        category=category,
        priority="MEDIUM",
        status=Status.ASSIGNED,
        reporter=hosteler,
        hostel=hostel,
        assigned_to=caretaker,
        current_level=1,
    )

    return {
        "hostel": hostel,
        "category": category,
        "hosteler": hosteler,
        "caretaker": caretaker,
        "warden": warden,
        "chief_warden": chief_warden,
        "dean": dean,
        "admin": admin,
        "ticket": ticket,
    }


@pytest.mark.django_db
class TestAuthorityStatusTransitions:
    """Tests all authority roles (L1 Caretaker, L2 Warden, L3 Chief Warden, L4 Dean, L5 Admin)

    can update ticket status across allowed transitions:
    - Assigned -> In Progress
    - In Progress -> On Hold
    - On Hold -> In Progress
    - In Progress -> Resolved
    """

    def test_caretaker_status_transitions(self, client, ticket_env):
        user = ticket_env["caretaker"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        # 1. Assigned -> In Progress
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS, "note": "Inspecting switch"},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

        # 2. In Progress -> On Hold
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.ON_HOLD, "note": "Waiting for spare parts"},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.ON_HOLD

        # 3. On Hold -> In Progress
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS, "note": "Parts arrived, resuming work"},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

        # 4. In Progress -> Resolved
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.RESOLVED, "note": "Switch replaced and tested"},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.RESOLVED
        assert ticket.resolved_at is not None

    def test_warden_status_transitions(self, client, ticket_env):
        user = ticket_env["warden"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.ON_HOLD, "note": "Waiting for spare parts or approval."},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.ON_HOLD

    def test_chief_warden_status_transitions(self, client, ticket_env):
        user = ticket_env["chief_warden"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

    def test_dean_status_transitions(self, client, ticket_env):
        user = ticket_env["dean"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

    def test_admin_status_transitions(self, client, ticket_env):
        user = ticket_env["admin"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

    def test_hosteler_cannot_arbitrarily_change_status(self, client, ticket_env):
        student = ticket_env["hosteler"]
        ticket = ticket_env["ticket"]
        client.login(username=student.login_id, password="pwd")

        # Hosteler cannot set Assigned -> In Progress or On Hold
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS},
        )
        assert res.status_code == 403
        ticket.refresh_from_db()
        assert ticket.status == Status.ASSIGNED

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.ON_HOLD},
        )
        assert res.status_code == 403
        ticket.refresh_from_db()
        assert ticket.status == Status.ASSIGNED

    def test_audit_timeline_recorded_for_status_changes(self, client, ticket_env):
        user = ticket_env["caretaker"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS, "note": "Checked the main switchboard"},
        )

        activity = TicketActivity.objects.filter(
            ticket=ticket,
            action=ActivityAction.STATUS_CHANGED,
            from_value=Status.ASSIGNED,
            to_value=Status.IN_PROGRESS,
        ).first()
        assert activity is not None
        assert activity.actor == user
        assert "Checked the main switchboard" in activity.note

    def test_ticket_detail_ui_shows_update_status_for_authority(self, client, ticket_env):
        caretaker = ticket_env["caretaker"]
        ticket = ticket_env["ticket"]
        client.login(username=caretaker.login_id, password="pwd")

        res = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
        assert res.status_code == 200
        content = res.content.decode()
        assert "Update Status" in content
        assert "Save Status" in content
        assert "status-cards-grid" in content
        assert "status-option-card" in content
        assert "Waiting to be started" in content
        assert "Work is underway" in content
        assert "Temporarily paused" in content
        assert "Issue fixed" in content
        assert "status-suggestion-chip" in content

    def test_ticket_detail_ui_hides_update_status_form_for_hosteler(self, client, ticket_env):
        student = ticket_env["hosteler"]
        ticket = ticket_env["ticket"]
        client.login(username=student.login_id, password="pwd")

        res = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
        assert res.status_code == 200
        content = res.content.decode()
        assert '<form method="post"' not in content or 'id="ticket-status-form"' not in content
        assert "Ticket status is managed by campus authority staff" in content

    def test_status_note_is_optional_for_all_transitions(self, client, ticket_env):
        user = ticket_env["caretaker"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        # First move to IN_PROGRESS without note
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.IN_PROGRESS, "note": ""},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS

        # Move to ON_HOLD without note
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.ON_HOLD, "note": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert res.status_code == 200 or res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.ON_HOLD

        # Move to RESOLVED without note
        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.RESOLVED, "note": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert res.status_code == 200 or res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.RESOLVED

    def test_authority_can_reject_ticket(self, client, ticket_env):
        user = ticket_env["caretaker"]
        ticket = ticket_env["ticket"]
        client.login(username=user.login_id, password="pwd")

        res = client.post(
            reverse("tickets:change_status", kwargs={"ticket_no": ticket.ticket_no}),
            {"status": Status.REJECTED, "note": "Duplicate issue"},
        )
        assert res.status_code == 302
        ticket.refresh_from_db()
        assert ticket.status == Status.REJECTED
