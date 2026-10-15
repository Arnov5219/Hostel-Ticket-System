import time
from unittest.mock import patch
import pytest
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner
from django.urls import reverse
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role, User
from apps.accounts.services import (
    bulk_verify_residents,
    generate_registration_token,
    register_hosteler,
    reject_resident,
    reset_resident_password,
    verify_resident,
)
from apps.hostels.models import GenderType, Hostel, Room
from apps.tickets.factories import TicketFactory
from apps.tickets.models import Category, Priority, Ticket, TicketVisibility


@pytest.fixture
def hostel_setup(db):
    hostel1 = Hostel.objects.create(name="Boys Hostel 1", code="BH-1", gender_type=GenderType.BOYS)
    hostel2 = Hostel.objects.create(name="Boys Hostel 2", code="BH-2", gender_type=GenderType.BOYS)
    room1 = Room.objects.create(hostel=hostel1, room_number="101", floor=1, capacity=2)
    room2 = Room.objects.create(hostel=hostel2, room_number="101", floor=1, capacity=2)

    warden1 = UserFactory(role=Role.WARDEN, hostel=hostel1, login_id="WARDEN1")
    warden2 = UserFactory(role=Role.WARDEN, hostel=hostel2, login_id="WARDEN2")
    admin = UserFactory(role=Role.ADMIN, login_id="ADMIN1")
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel1, login_id="CARETAKER1")

    return {
        "hostel1": hostel1,
        "hostel2": hostel2,
        "room1": room1,
        "room2": room2,
        "warden1": warden1,
        "warden2": warden2,
        "admin": admin,
        "caretaker": caretaker,
    }


def make_valid_ts_token(elapsed_seconds=5):
    """Helper to generate a timestamp token that appears elapsed_seconds in the past."""
    signer = TimestampSigner(salt="accounts.registration")
    past_timestamp = int(timezone.now().timestamp()) - elapsed_seconds
    return signer.sign(str(past_timestamp))


@pytest.mark.django_db
class TestRegistrationService:
    def test_register_hosteler_service_success(self, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]

        data = {
            "login_id": "21bcs001",
            "full_name": "Aarav Sharma",
            "email": "aarav@example.com",
            "phone": "9876543210",
            "password": "SecurePassword123!",
            "hostel": h1,
            "room": r1,
            "ts_token": make_valid_ts_token(5),
            "website": "",
        }

        user = register_hosteler(data)

        assert user.login_id == "21BCS001"  # Uppercased
        assert user.email == "aarav@example.com"
        assert user.role == Role.HOSTELER
        assert user.is_verified is True
        assert user.registration_source == "SELF_REGISTRATION"
        assert user.hostel == h1
        assert user.room == r1
        assert user.check_password("SecurePassword123!")
        assert user.residence_histories.count() == 1

    def test_registration_without_roll_email_phone(self, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]

        data = {
            "full_name": "Priya Patel",
            "password": "SecurePassword123!",
            "hostel": h1,
            "room": r1,
            "ts_token": make_valid_ts_token(5),
            "website": "",
        }

        user = register_hosteler(data)

        assert user.login_id.startswith("STU")
        assert len(user.login_id) == 9  # STU + 6 digits
        assert user.email == ""
        assert user.phone == ""
        assert user.role == Role.HOSTELER
        assert user.is_verified is True
        assert user.hostel == h1
        assert user.room == r1

    def test_honeypot_rejection(self, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]

        data = {
            "login_id": "BOT001",
            "full_name": "Spam Bot",
            "email": "bot@example.com",
            "password": "Password123!",
            "hostel": h1,
            "room": r1,
            "website": "http://spamsite.com",  # Honeypot filled
            "ts_token": make_valid_ts_token(5),
        }

        with pytest.raises(ValidationError, match="Registration rejected"):
            register_hosteler(data)

    def test_timestamp_too_quick(self, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]

        # Token created just 1 second ago (<3s)
        fast_token = make_valid_ts_token(1)

        data = {
            "login_id": "FAST001",
            "full_name": "Fast Submitter",
            "email": "fast@example.com",
            "password": "Password123!",
            "hostel": h1,
            "room": r1,
            "ts_token": fast_token,
            "website": "",
        }

        with pytest.raises(ValidationError, match="Form was submitted too quickly"):
            register_hosteler(data)

    def test_duplicate_roll_and_email(self, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]

        # First registration
        register_hosteler({
            "login_id": "21BCS010",
            "full_name": "Existing Student",
            "email": "existing@example.com",
            "password": "Password123!",
            "hostel": h1,
            "room": r1,
            "ts_token": make_valid_ts_token(5),
            "website": "",
        })

        # Duplicate login_id
        with pytest.raises(ValidationError, match="already registered"):
            register_hosteler({
                "login_id": "21bcs010",  # case insensitive
                "full_name": "Another Student",
                "email": "another@example.com",
                "password": "Password123!",
                "hostel": h1,
                "room": r1,
                "ts_token": make_valid_ts_token(5),
                "website": "",
            })

        # Duplicate email
        with pytest.raises(ValidationError, match="already in use"):
            register_hosteler({
                "login_id": "21BCS099",
                "full_name": "Another Student",
                "email": "EXISTING@example.com",  # case insensitive
                "password": "Password123!",
                "hostel": h1,
                "room": r1,
                "ts_token": make_valid_ts_token(5),
                "website": "",
            })


@pytest.mark.django_db
class TestRegistrationView:
    def test_get_register_page(self, client, hostel_setup):
        url = reverse("accounts:register")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Hosteler Registration" in content
        assert "ts_token" in content
        assert "BH-1" in content

    def test_post_registration_success(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]

        url = reverse("accounts:register")
        post_data = {
            "full_name": "Rohan Verma",
            "login_id": "22BCS045",
            "email": "rohan@example.com",
            "phone": "9876543211",
            "hostel": h1.id,
            "password": "Password@123",
            "confirm_password": "Password@123",
            "ts_token": make_valid_ts_token(10),
            "website": "",
        }

        response = client.post(url, post_data, follow=True)
        assert response.status_code == 200

        user = User.objects.filter(login_id="22BCS045").first()
        assert user is not None
        assert user.role == Role.HOSTELER
        assert user.is_verified is True
        assert user.hostel == h1

    def test_post_registration_without_optional_fields(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]

        url = reverse("accounts:register")
        post_data = {
            "full_name": "Dev Sharma",
            "login_id": "",
            "email": "",
            "phone": "",
            "hostel": h1.id,
            "password": "Password@123",
            "confirm_password": "Password@123",
            "ts_token": make_valid_ts_token(10),
            "website": "",
        }

        response = client.post(url, post_data, follow=True)
        assert response.status_code == 200

        user = User.objects.filter(full_name="Dev Sharma").first()
        assert user is not None
        assert user.login_id.startswith("STU")
        assert user.email == ""
        assert user.phone == ""
        assert user.hostel == h1

    def test_login_with_email(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        user = User.objects.create_user(
            login_id="STU999001",
            email="student@univ.edu",
            password="SecurePassword123!",
            full_name="Test Student",
            role=Role.HOSTELER,
            hostel=h1,
            room=r1,
        )

        login_url = reverse("accounts:login")
        # Log in using email instead of login_id
        response = client.post(
            login_url,
            {"login_id": "student@univ.edu", "password": "SecurePassword123!"},
            follow=True,
        )
        assert response.status_code == 200
        assert response.context["user"].is_authenticated
        assert response.context["user"].id == user.id


@pytest.mark.django_db
class TestWardenResidentVerification:
    def test_manage_residents_removed_returns_404(self, client, hostel_setup):
        client.force_login(hostel_setup["warden1"])
        assert client.get("/manage/residents/").status_code == 404

        client.force_login(hostel_setup["admin"])
        assert client.get("/manage/residents/").status_code == 404

    def test_cli_reset_user_password(self, hostel_setup):
        from io import StringIO
        from django.core.management import call_command
        student = UserFactory(role=Role.HOSTELER, login_id="STU_RESET_CLI")
        out = StringIO()
        call_command("reset_user_password", student.login_id, stdout=out)
        student.refresh_from_db()
        assert student.must_change_password is True
        assert "Password reset successfully" in out.getvalue()

    def test_cli_import_allowed_roll_numbers(self):
        import tempfile
        import os
        from io import StringIO
        from django.core.management import call_command
        from apps.accounts.models import AllowedRollNumber

        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as f:
            f.write("21BCS901\n21BCS902\n")
            f_path = f.name

        try:
            out = StringIO()
            call_command("import_allowed_roll_numbers", f_path, stdout=out)
            assert AllowedRollNumber.objects.filter(roll_no="21BCS901").exists()
            assert AllowedRollNumber.objects.filter(roll_no="21BCS902").exists()
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)


@pytest.mark.django_db
class TestResidentCommunityParticipation:
    def test_resident_can_repost_and_comment_without_verification(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        creator = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1)
        ticket = TicketFactory(
            reporter=creator,
            hostel=h1,
            room=r1,
            visibility=TicketVisibility.HOSTEL,
        )

        user = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1)
        client.force_login(user)

        # Repost succeeds immediately
        repost_url = reverse("tickets:repost", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(repost_url)
        assert resp.status_code == 200

        # Comment succeeds immediately
        comment_url = reverse("tickets:community_comments", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(comment_url, {"body": "I have this issue too!"})
        assert resp.status_code == 200
        assert "I have this issue too!" in resp.content.decode("utf-8")
