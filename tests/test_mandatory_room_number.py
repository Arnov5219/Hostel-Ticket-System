import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.hostels.models import Room
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.forms import TicketCreateForm
from apps.tickets.models import Status, Ticket
from apps.tickets.services.status import change_status


@pytest.mark.django_db
class TestMandatoryRoomNumberField:
    """Tests for mandatory Room Number field on Raise Ticket page and ticket details."""

    def test_room_number_rendered_in_raise_ticket_form(self, client):
        """Room Number field must be rendered with label 'Room Number *' and placeholder 'e.g. Room 204'."""
        hostel = HostelFactory(name="Ganga Hostel", code="GNG")
        student = UserFactory(role=Role.HOSTELER, hostel=hostel, password="student_pass")
        client.login(username=student.login_id, password="student_pass")

        response = client.get(reverse("tickets:create"))
        assert response.status_code == 200
        content = response.content.decode("utf-8")

        # Must include label, placeholder, and required marker
        assert "Room Number *" in content
        assert "e.g. Room 204" in content
        assert "id_room_number" in content
        assert 'name="room_number"' in content

        # Check positioning: Room Number must appear below Assigned Hostel and above Category
        assigned_hostel_pos = content.find("ASSIGNED HOSTEL")
        room_number_pos = content.find("Room Number *")
        category_pos = content.find("Category *")

        assert assigned_hostel_pos != -1
        assert room_number_pos != -1
        assert category_pos != -1
        assert assigned_hostel_pos < room_number_pos < category_pos

    def test_submission_blocked_when_room_number_empty(self, client):
        """Submitting form with empty room_number must be rejected by backend validation."""
        hostel = HostelFactory()
        caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
        hostel.responsible_staff = caretaker
        hostel.save()
        student = UserFactory(role=Role.HOSTELER, hostel=hostel, password="student_pass")
        category = CategoryFactory()

        client.login(username=student.login_id, password="student_pass")
        response = client.post(
            reverse("tickets:create"),
            {
                "category": category.id,
                "room_number": "",
                "title": "Broken window latch",
                "description": "The window in room latch is loose",
                "priority": "MEDIUM",
                "hostel": hostel.id,
            },
        )

        assert response.status_code == 200  # Re-rendered with errors
        assert Ticket.objects.filter(reporter=student).count() == 0
        content = response.content.decode("utf-8")
        assert "Room number is required" in content

    def test_submission_rejected_when_room_number_is_only_whitespace(self, client):
        """Submitting form with only spaces in room_number must be rejected."""
        hostel = HostelFactory()
        caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
        hostel.responsible_staff = caretaker
        hostel.save()
        student = UserFactory(role=Role.HOSTELER, hostel=hostel, password="student_pass")
        category = CategoryFactory()

        client.login(username=student.login_id, password="student_pass")
        response = client.post(
            reverse("tickets:create"),
            {
                "category": category.id,
                "room_number": "     ",
                "title": "Water dripping from pipe",
                "description": "Pipe dripping continuously",
                "priority": "MEDIUM",
                "hostel": hostel.id,
            },
        )

        assert response.status_code == 200
        assert Ticket.objects.filter(reporter=student).count() == 0
        content = response.content.decode("utf-8")
        assert "Room number is required" in content

    @pytest.mark.parametrize(
        "input_room, expected_room",
        [
            ("204", "204"),
            ("Room 101", "Room 101"),
            ("A-12", "A-12"),
            ("G-05", "G-05"),
            ("  Room 305  ", "Room 305"),
        ],
    )
    def test_submission_successful_with_valid_room_number(self, client, input_room, expected_room):
        """Valid room numbers must be saved correctly and trimmed."""
        hostel = HostelFactory(code="KB", name="Kaveri Boys Hostel")
        caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
        hostel.responsible_staff = caretaker
        hostel.save()
        student = UserFactory(role=Role.HOSTELER, hostel=hostel, password="student_pass")
        category = CategoryFactory(name="Electrical")

        client.login(username=student.login_id, password="student_pass")
        response = client.post(
            reverse("tickets:create"),
            {
                "category": category.id,
                "room_number": input_room,
                "title": f"Switch malfunction in {expected_room}",
                "description": "Main light switch sparked when turned on",
                "priority": "HIGH",
                "hostel": hostel.id,
            },
        )

        assert response.status_code == 302
        ticket = Ticket.objects.filter(reporter=student, title__contains="Switch malfunction").first()
        assert ticket is not None
        assert ticket.room_number == expected_room

    def test_room_number_displayed_in_ticket_details(self, client):
        """Ticket details view must display the room number in header and context details."""
        hostel = HostelFactory(code="KV", name="Kaveri")
        caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="ct_pwd")
        student = UserFactory(role=Role.HOSTELER, hostel=hostel, password="student_pass")
        ticket = TicketFactory(
            hostel=hostel,
            reporter=student,
            assigned_to=caretaker,
            room_number="Room 204",
            title="Ceiling fan wobbling",
        )

        client.login(username=student.login_id, password="student_pass")
        response = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
        assert response.status_code == 200
        content = response.content.decode("utf-8")

        # Must display room number badge in header
        assert "Room 204" in content
        # Must display room number in context details card
        assert "ROOM NUMBER" in content

    def test_room_number_preserved_across_status_change(self):
        """Changing ticket status must preserve the room number."""
        hostel = HostelFactory()
        caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
        ticket = TicketFactory(hostel=hostel, assigned_to=caretaker, room_number="B-302", status=Status.ASSIGNED)

        change_status(ticket, Status.IN_PROGRESS, actor=caretaker)
        ticket.refresh_from_db()
        assert ticket.status == Status.IN_PROGRESS
        assert ticket.room_number == "B-302"

        change_status(ticket, Status.RESOLVED, actor=caretaker)
        ticket.refresh_from_db()
        assert ticket.status == Status.RESOLVED
        assert ticket.room_number == "B-302"

    def test_form_initializes_with_user_assigned_room(self):
        """If a hosteler has an assigned room, form initializes room_number field with it."""
        hostel = HostelFactory()
        room = Room.objects.create(hostel=hostel, room_number="312", floor=3, capacity=2)
        student = UserFactory(role=Role.HOSTELER, hostel=hostel, room=room)

        form = TicketCreateForm(user=student)
        assert form.fields["room_number"].initial == "312"

    def test_search_quick_includes_room_number(self, client):
        """Quick search API endpoint must include room_number in results and support searching by room."""
        hostel = HostelFactory()
        caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="staff_pass")
        TicketFactory(hostel=hostel, room_number="404-B", title="Broken chair leg")

        client.login(username=caretaker.login_id, password="staff_pass")
        response = client.get(reverse("tickets:search_quick") + "?q=404-B")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        assert data["results"][0]["room_number"] == "404-B"
