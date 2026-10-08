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
        assert user.is_verified is False
        assert user.registration_source == "SELF_REGISTRATION"
        assert user.hostel == h1
        assert user.room == r1
        assert user.check_password("SecurePassword123!")
        assert user.residence_histories.count() == 1

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

    def test_room_hostel_mismatch(self, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r2 = hostel_setup["room2"]  # belongs to hostel2!

        data = {
            "login_id": "MISMATCH01",
            "full_name": "Mismatch Student",
            "email": "mismatch@example.com",
            "password": "Password123!",
            "hostel": h1,
            "room": r2,
            "ts_token": make_valid_ts_token(5),
            "website": "",
        }

        with pytest.raises(ValidationError, match="does not belong to"):
            register_hosteler(data)


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
            "floor": 1,
            "room": r1.id,
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
        assert user.is_verified is False
        assert user.hostel == h1
        assert user.room == r1


@pytest.mark.django_db
class TestWardenResidentVerification:
    def test_permissions_access(self, client, hostel_setup):
        manage_url = reverse("hostels:manage_residents")

        # Caretaker -> 403
        client.force_login(hostel_setup["caretaker"])
        resp = client.get(manage_url)
        assert resp.status_code == 403

        # Hosteler -> 403
        hosteler = UserFactory(role=Role.HOSTELER)
        client.force_login(hosteler)
        resp = client.get(manage_url)
        assert resp.status_code == 403

        # Warden -> 200
        client.force_login(hostel_setup["warden1"])
        resp = client.get(manage_url)
        assert resp.status_code == 200

        # Admin -> 200
        client.force_login(hostel_setup["admin"])
        resp = client.get(manage_url)
        assert resp.status_code == 200

    def test_warden_queryset_scoping(self, client, hostel_setup):
        w1 = hostel_setup["warden1"]
        h1 = hostel_setup["hostel1"]
        h2 = hostel_setup["hostel2"]
        r1 = hostel_setup["room1"]
        r2 = hostel_setup["room2"]

        u1 = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False, login_id="STU_H1")
        u2 = UserFactory(role=Role.HOSTELER, hostel=h2, room=r2, is_verified=False, login_id="STU_H2")

        client.force_login(w1)
        resp = client.get(reverse("hostels:manage_residents"))
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "STU_H1" in content
        assert "STU_H2" not in content

    def test_verify_resident_action(self, client, hostel_setup):
        w1 = hostel_setup["warden1"]
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        student = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False)

        client.force_login(w1)
        verify_url = reverse("hostels:verify_resident", kwargs={"resident_id": student.id})
        resp = client.post(verify_url)
        assert resp.status_code == 302

        student.refresh_from_db()
        assert student.is_verified is True
        assert student.verified_by == w1
        assert student.verified_at is not None

    def test_warden_cannot_verify_other_hostel(self, client, hostel_setup):
        w1 = hostel_setup["warden1"]
        h2 = hostel_setup["hostel2"]
        r2 = hostel_setup["room2"]
        student_h2 = UserFactory(role=Role.HOSTELER, hostel=h2, room=r2, is_verified=False)

        client.force_login(w1)
        verify_url = reverse("hostels:verify_resident", kwargs={"resident_id": student_h2.id})
        resp = client.post(verify_url)
        assert resp.status_code == 403

        student_h2.refresh_from_db()
        assert student_h2.is_verified is False

    def test_reject_resident_action(self, client, hostel_setup):
        w1 = hostel_setup["warden1"]
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        student = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False)

        client.force_login(w1)
        reject_url = reverse("hostels:reject_resident", kwargs={"resident_id": student.id})
        resp = client.post(reject_url, {"reason": "Invalid room allotment receipt."})
        assert resp.status_code == 302

        student.refresh_from_db()
        assert student.is_verified is False
        assert student.rejected_reason == "Invalid room allotment receipt."

    def test_reset_resident_password(self, client, hostel_setup):
        w1 = hostel_setup["warden1"]
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        student = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=True, login_id="RESETME")

        client.force_login(w1)
        reset_url = reverse("hostels:reset_resident_password", kwargs={"resident_id": student.id})
        resp = client.post(reset_url, follow=True)
        assert resp.status_code == 200

        student.refresh_from_db()
        assert student.must_change_password is True

    def test_bulk_verify_residents(self, client, hostel_setup):
        w1 = hostel_setup["warden1"]
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        h2 = hostel_setup["hostel2"]
        r2 = hostel_setup["room2"]

        u1 = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False)
        u2 = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False)
        u3 = UserFactory(role=Role.HOSTELER, hostel=h2, room=r2, is_verified=False)

        client.force_login(w1)
        bulk_url = reverse("hostels:bulk_verify_residents")
        resp = client.post(bulk_url, {"resident_ids": [str(u1.id), str(u2.id), str(u3.id)]})
        assert resp.status_code == 302

        u1.refresh_from_db()
        u2.refresh_from_db()
        u3.refresh_from_db()

        # Warden 1 can only verify residents in Hostel 1
        assert u1.is_verified is True
        assert u2.is_verified is True
        assert u3.is_verified is False


@pytest.mark.django_db
class TestUnverifiedResidentCommunityRestrictions:
    def test_unverified_cannot_repost(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        creator = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=True)
        ticket = TicketFactory(
            reporter=creator,
            hostel=h1,
            room=r1,
            visibility=TicketVisibility.HOSTEL,
        )

        unverified_user = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False)
        client.force_login(unverified_user)

        repost_url = reverse("tickets:repost", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(repost_url)
        assert resp.status_code == 403
        assert "pending warden verification" in resp.content.decode("utf-8")

    def test_unverified_cannot_comment_community(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        creator = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=True)
        ticket = TicketFactory(
            reporter=creator,
            hostel=h1,
            room=r1,
            visibility=TicketVisibility.HOSTEL,
        )

        unverified_user = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=False)
        client.force_login(unverified_user)

        comment_url = reverse("tickets:community_comments", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(comment_url, {"body": "I have this issue too!"})
        assert resp.status_code == 403
        assert "pending warden verification" in resp.content.decode("utf-8")

    def test_verified_user_can_repost_and_comment(self, client, hostel_setup):
        h1 = hostel_setup["hostel1"]
        r1 = hostel_setup["room1"]
        creator = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=True)
        ticket = TicketFactory(
            reporter=creator,
            hostel=h1,
            room=r1,
            visibility=TicketVisibility.HOSTEL,
        )

        verified_user = UserFactory(role=Role.HOSTELER, hostel=h1, room=r1, is_verified=True)
        client.force_login(verified_user)

        # Repost
        repost_url = reverse("tickets:repost", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(repost_url)
        assert resp.status_code == 200

        # Comment
        comment_url = reverse("tickets:community_comments", kwargs={"ticket_no": ticket.ticket_no})
        resp = client.post(comment_url, {"body": "Confirmed, very loud noise."})
        assert resp.status_code == 200
        assert "Confirmed, very loud noise." in resp.content.decode("utf-8")
