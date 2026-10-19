import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.hostels.services import (
    change_hostel_assignments,
)
from apps.tickets.factories import TicketFactory
from apps.tickets.services.escalation import escalate
from apps.tickets.services.routing import assign_initial


@pytest.mark.django_db
class TestHostelResponsibilityAssignments:
    def test_change_caretaker_only(self, client):
        admin = UserFactory(role=Role.ADMIN)
        caretaker1 = UserFactory(role=Role.CARETAKER, escalation_level=1)
        caretaker2 = UserFactory(role=Role.CARETAKER, escalation_level=1)
        warden = UserFactory(role=Role.WARDEN, escalation_level=2)

        hostel = HostelFactory(name="Tagore Bhavan", code="TB-1", responsible_staff=caretaker1, responsible_warden=warden)

        client.force_login(admin)
        url = reverse("hostels:change_responsible_staff", kwargs={"hostel_id": hostel.id})
        response = client.post(url, {
            "responsible_staff": caretaker2.id,
            "responsible_warden": warden.id,
        })
        assert response.status_code == 302

        hostel.refresh_from_db()
        caretaker2.refresh_from_db()
        assert hostel.responsible_staff == caretaker2
        assert hostel.responsible_warden == warden
        assert caretaker2.hostel == hostel

    def test_change_warden_only(self, client):
        admin = UserFactory(role=Role.ADMIN)
        caretaker = UserFactory(role=Role.CARETAKER, escalation_level=1)
        warden1 = UserFactory(role=Role.WARDEN, escalation_level=2)
        warden2 = UserFactory(role=Role.WARDEN, escalation_level=2)

        hostel = HostelFactory(name="Tagore Bhavan", code="TB-2", responsible_staff=caretaker, responsible_warden=warden1)

        client.force_login(admin)
        url = reverse("hostels:change_responsible_staff", kwargs={"hostel_id": hostel.id})
        response = client.post(url, {
            "responsible_staff": caretaker.id,
            "responsible_warden": warden2.id,
        })
        assert response.status_code == 302

        hostel.refresh_from_db()
        warden2.refresh_from_db()
        assert hostel.responsible_staff == caretaker
        assert hostel.responsible_warden == warden2
        assert warden2.hostel == hostel

    def test_change_both_caretaker_and_warden_simultaneously(self, client):
        admin = UserFactory(role=Role.ADMIN)
        caretaker1 = UserFactory(role=Role.CARETAKER, escalation_level=1)
        caretaker2 = UserFactory(role=Role.CARETAKER, escalation_level=1)
        warden1 = UserFactory(role=Role.WARDEN, escalation_level=2)
        warden2 = UserFactory(role=Role.WARDEN, escalation_level=2)

        hostel = HostelFactory(name="Shastri Bhavan", code="SB-1", responsible_staff=caretaker1, responsible_warden=warden1)

        client.force_login(admin)
        url = reverse("hostels:change_responsible_staff", kwargs={"hostel_id": hostel.id})
        response = client.post(url, {
            "responsible_staff": caretaker2.id,
            "responsible_warden": warden2.id,
        })
        assert response.status_code == 302

        hostel.refresh_from_db()
        caretaker2.refresh_from_db()
        warden2.refresh_from_db()
        assert hostel.responsible_staff == caretaker2
        assert hostel.responsible_warden == warden2
        assert caretaker2.hostel == hostel
        assert warden2.hostel == hostel

    def test_unassign_assignments(self, client):
        admin = UserFactory(role=Role.ADMIN)
        caretaker = UserFactory(role=Role.CARETAKER, escalation_level=1)
        warden = UserFactory(role=Role.WARDEN, escalation_level=2)

        hostel = HostelFactory(name="Kalam Bhavan", code="KB-1", responsible_staff=caretaker, responsible_warden=warden)

        client.force_login(admin)
        url = reverse("hostels:change_responsible_staff", kwargs={"hostel_id": hostel.id})
        response = client.post(url, {
            "responsible_staff": "",
            "responsible_warden": "",
        })
        assert response.status_code == 302

        hostel.refresh_from_db()
        assert hostel.responsible_staff is None
        assert hostel.responsible_warden is None

    def test_validation_inactive_staff(self):
        hostel = HostelFactory(name="Test Hostel", code="TH-1")
        inactive_caretaker = UserFactory(role=Role.CARETAKER, is_active=False)
        inactive_warden = UserFactory(role=Role.WARDEN, is_active=False)

        with pytest.raises(ValidationError, match="inactive"):
            change_hostel_assignments(hostel, caretaker=inactive_caretaker, update_caretaker=True, update_warden=False)

        with pytest.raises(ValidationError, match="inactive"):
            change_hostel_assignments(hostel, warden=inactive_warden, update_caretaker=False, update_warden=True)

    def test_validation_wrong_role(self):
        hostel = HostelFactory(name="Test Hostel", code="TH-2")
        hosteler = UserFactory(role=Role.HOSTELER)
        warden = UserFactory(role=Role.WARDEN, escalation_level=2)
        caretaker = UserFactory(role=Role.CARETAKER, escalation_level=1)

        # Cannot assign warden or hosteler as Level 1 Caretaker
        with pytest.raises(ValidationError, match="Level 1"):
            change_hostel_assignments(hostel, caretaker=warden, update_caretaker=True, update_warden=False)

        with pytest.raises(ValidationError, match="Level 1"):
            change_hostel_assignments(hostel, caretaker=hosteler, update_caretaker=True, update_warden=False)

        # Cannot assign caretaker or hosteler as Level 2 Warden
        with pytest.raises(ValidationError, match="Level 2"):
            change_hostel_assignments(hostel, warden=caretaker, update_caretaker=False, update_warden=True)

        with pytest.raises(ValidationError, match="Level 2"):
            change_hostel_assignments(hostel, warden=hosteler, update_caretaker=False, update_warden=True)

    def test_unauthorized_user_cannot_modify(self, client):
        hosteler = UserFactory(role=Role.HOSTELER)
        caretaker = UserFactory(role=Role.CARETAKER)
        hostel = HostelFactory()

        url = reverse("hostels:change_responsible_staff", kwargs={"hostel_id": hostel.id})

        # Anonymous user redirected to login
        response = client.post(url, {"responsible_staff": caretaker.id})
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

        # Hosteler denied
        client.force_login(hosteler)
        response = client.post(url, {"responsible_staff": caretaker.id})
        assert response.status_code == 403

        # Caretaker denied
        client.force_login(caretaker)
        response = client.post(url, {"responsible_staff": caretaker.id})
        assert response.status_code == 403

    def test_page_renders_coverage_statuses_and_actions(self, client):
        admin = UserFactory(role=Role.ADMIN)
        caretaker = UserFactory(role=Role.CARETAKER, full_name="Alice Caretaker", login_id="alice_ct")
        warden = UserFactory(role=Role.WARDEN, full_name="Bob Warden", login_id="bob_warden")

        h_full = HostelFactory(name="Full Coverage Hostel", code="FCH", responsible_staff=caretaker, responsible_warden=warden)
        h_no_ct = HostelFactory(name="No Caretaker Hostel", code="NCH", responsible_staff=None, responsible_warden=warden)
        h_no_w = HostelFactory(name="No Warden Hostel", code="NWH", responsible_staff=caretaker, responsible_warden=None)
        h_empty = HostelFactory(name="Empty Hostel", code="EH", responsible_staff=None, responsible_warden=None)

        client.force_login(admin)
        url = reverse("hostels:manage_responsibility")
        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode("utf-8")
        # Check action button
        assert "Manage Staff" in content
        assert "Change caretaker" not in content

        # Check coverage pills
        assert "Complete Coverage" in content
        assert "Missing Caretaker" in content
        assert "Missing Warden" in content
        assert "Missing Staff" in content

        # Check staff names and IDs
        assert "Alice Caretaker" in content
        assert "alice_ct" in content
        assert "Bob Warden" in content
        assert "bob_warden" in content

        # Check modal structure
        assert "Manage Staff Assignments" in content
        assert "Level 1 Caretaker" in content
        assert "Level 2 Warden" in content
        assert "Save Changes" in content

    def test_ticket_routing_and_escalation_uses_updated_assignments(self):
        caretaker1 = UserFactory(role=Role.CARETAKER, escalation_level=1)
        caretaker2 = UserFactory(role=Role.CARETAKER, escalation_level=1)
        warden1 = UserFactory(role=Role.WARDEN, escalation_level=2)
        warden2 = UserFactory(role=Role.WARDEN, escalation_level=2)

        hostel = HostelFactory(name="Ganga Hostel", code="GH", responsible_staff=caretaker1, responsible_warden=warden1)

        # 1. Initial routing assigns to Caretaker 1
        ticket1 = TicketFactory(hostel=hostel, assigned_to=None)
        assign_initial(ticket1)
        assert ticket1.assigned_to == caretaker1

        # 2. Update assignments to Caretaker 2 and Warden 2
        change_hostel_assignments(hostel, caretaker=caretaker2, warden=warden2)
        hostel.refresh_from_db()

        # 3. New ticket routes to Caretaker 2
        ticket2 = TicketFactory(hostel=hostel, assigned_to=None)
        assign_initial(ticket2)
        assert ticket2.assigned_to == caretaker2

        # 4. Escalating ticket2 from L1 to L2 escalates directly to Warden 2
        escalated_ticket = escalate(ticket2)
        assert escalated_ticket.current_level == 2
        assert escalated_ticket.assigned_to == warden2
