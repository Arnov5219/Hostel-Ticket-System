import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import ResidenceHistory, Role, User
from apps.accounts.services import set_residence
from apps.hostels.models import GenderType, Hostel, Room
from apps.tickets.models import Category, Priority, Ticket
from apps.tickets.services.location import validate_location


@pytest.fixture
def residence_hierarchy(db):
    hostel1 = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hostel2 = Hostel.objects.create(name="Hostel Two", code="H2", gender_type=GenderType.BOYS)

    room1 = Room.objects.create(hostel=hostel1, room_number="101", floor=1, capacity=2)
    room2 = Room.objects.create(hostel=hostel2, room_number="201", floor=2, capacity=1)

    return {
        "hostel1": hostel1,
        "hostel2": hostel2,
        "room1": room1,
        "room2": room2,
    }


@pytest.fixture
def student_user(db, residence_hierarchy):
    return User.objects.create_user(
        login_id="std_test_01",
        full_name="Test Hosteler",
        role=Role.HOSTELER,
        password="password123",
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        login_id="ct_test_01",
        full_name="Test Caretaker",
        role=Role.CARETAKER,
        password="password123",
    )


@pytest.mark.django_db
class TestResidenceService:
    def test_set_residence_success_and_history(self, student_user, residence_hierarchy):
        h1 = residence_hierarchy["hostel1"]
        r1 = residence_hierarchy["room1"]

        assert not student_user.has_residence

        user = set_residence(student_user, h1, r1)

        assert user.has_residence
        assert user.hostel == h1
        assert user.room == r1
        assert user.residence_set_at is not None

        history = ResidenceHistory.objects.filter(user=user)
        assert history.count() == 1
        record = history.first()
        assert record.hostel == h1
        assert record.room == r1
        assert record.changed_by == user

    def test_set_residence_inactive_hostel_rejected(self, student_user, residence_hierarchy):
        h1 = residence_hierarchy["hostel1"]
        h1.is_active = False
        h1.save()

        with pytest.raises(ValidationError) as exc:
            set_residence(student_user, h1)
        assert "currently inactive" in str(exc.value)


@pytest.mark.django_db
class TestResidenceMiddlewareGate:
    def test_unassigned_hosteler_redirected_to_onboarding(self, client, student_user):
        client.force_login(student_user)

        # Accessing dashboard should redirect to onboarding
        response = client.get(reverse("dashboard:index"))
        assert response.status_code == 302
        assert response.url == reverse("accounts:onboarding")

    def test_unassigned_hosteler_htmx_gets_hx_redirect(self, client, student_user):
        client.force_login(student_user)

        response = client.get(reverse("dashboard:index"), HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert response["HX-Redirect"] == reverse("accounts:onboarding")

    def test_allowed_paths_accessible_during_onboarding(self, client, student_user, residence_hierarchy):
        client.force_login(student_user)

        # Onboarding page itself
        resp = client.get(reverse("accounts:onboarding"))
        assert resp.status_code == 200

        # Theme endpoint
        resp_t = client.post(reverse("accounts:theme"), {"theme": "DARK"})
        assert resp_t.status_code == 204

    def test_staff_not_blocked_by_residence_gate(self, client, staff_user):
        client.force_login(staff_user)

        response = client.get(reverse("dashboard:index"))
        assert response.status_code == 200

    def test_assigned_hosteler_not_blocked(self, client, student_user, residence_hierarchy):
        set_residence(
            student_user,
            residence_hierarchy["hostel1"],
        )
        client.force_login(student_user)

        response = client.get(reverse("dashboard:index"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestLocationValidationAndTicketForm:
    def test_validate_location_service(self, residence_hierarchy, student_user):
        h1 = residence_hierarchy["hostel1"]

        h, r, outside = validate_location(h1.id, reporter=student_user)
        assert h == h1
        assert not outside

    def test_validate_location_outside_hostel_detected(self, residence_hierarchy, student_user):
        # Set student user to hostel 1
        set_residence(
            student_user,
            residence_hierarchy["hostel1"],
        )

        # Validate ticket raised in hostel 2
        h2 = residence_hierarchy["hostel2"]

        h, r, outside = validate_location(h2.id, reporter=student_user)
        assert outside is True

    def test_raise_ticket_creates_location_and_outside_flag(self, client, student_user, residence_hierarchy):
        set_residence(
            student_user,
            residence_hierarchy["hostel1"],
        )
        client.force_login(student_user)

        cat = Category.objects.create(name="Furniture & Fixtures")
        h2 = residence_hierarchy["hostel2"]

        post_data = {
            "title": "Broken desk in other hostel",
            "category": cat.id,
            "priority": Priority.LOW,
            "description": "Desk leg cracked during visit in room 201.",
            "hostel": h2.id,
            "different_hostel": True,
        }

        resp = client.post(reverse("tickets:create"), post_data)
        assert resp.status_code == 302

        ticket = Ticket.objects.get(title="Broken desk in other hostel")
        assert ticket.hostel == h2
        assert ticket.outside_own_hostel is True
