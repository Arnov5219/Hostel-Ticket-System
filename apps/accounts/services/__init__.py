import secrets

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ResidenceHistory, Role, User
from apps.hostels.models import Hostel, Room


def set_residence(user, hostel, room=None, changed_by=None, floor=None):
    """
    Validates and updates the residence for a user.
    Residence is Hostel-only (Section 5.3). Room is kept optional for historical data compatibility.
    """
    if not hostel:
        raise ValidationError("Hostel is required.")

    if not hostel.is_active:
        raise ValidationError(f"Hostel '{hostel.name}' is currently inactive.")

    with transaction.atomic():
        user.hostel = hostel
        if room:
            user.room = room
        user.residence_set_at = timezone.now()
        user.save(update_fields=["hostel", "room", "residence_set_at"] if room else ["hostel", "residence_set_at"])

        ResidenceHistory.objects.create(
            user=user,
            hostel=hostel,
            room=room,
            changed_by=changed_by or user,
        )

    return user


def generate_registration_token():
    """Generates a signed timestamp token for anti-bot protection."""
    signer = TimestampSigner(salt="accounts.registration")
    return signer.sign(str(int(timezone.now().timestamp())))


def validate_anti_bot(data, request_meta=None):
    """
    Validates anti-bot protections:
    1. Honeypot check: 'website' field must be empty.
    2. Timestamp check: must take >= 3 seconds and <= 1 hour (3600 seconds).
    3. IP rate limiting: max 5 registrations per IP per hour.
    """
    # 1. Honeypot check
    if data.get("website"):
        raise ValidationError("Registration rejected.")

    # 2. Timestamp check
    token = data.get("ts_token")
    if token:
        signer = TimestampSigner(salt="accounts.registration")
        try:
            val = signer.unsign(token, max_age=3600)
            submitted_time = int(val)
            now_sec = int(timezone.now().timestamp())
            if now_sec - submitted_time < 3:
                raise ValidationError("Form was submitted too quickly. Please take a moment and try again.")
        except SignatureExpired:
            raise ValidationError("Registration session timed out. Please refresh and try again.")
        except (BadSignature, ValueError):
            raise ValidationError("Invalid registration token.")

    # 3. IP rate limiting
    if request_meta:
        ip = request_meta.get("REMOTE_ADDR", "unknown")
        rate_key = f"reg_rate_limit_{ip}"
        attempts = cache.get(rate_key, 0)
        if attempts >= 5:
            raise ValidationError("Too many registration attempts from this network. Please try again later.")
        cache.set(rate_key, attempts + 1, timeout=3600)


def generate_student_login_id() -> str:
    """Generates a unique login ID for a hosteler if no roll number is provided."""
    while True:
        num = secrets.randbelow(900000) + 100000
        candidate = f"STU{num}"
        if not User.objects.filter(login_id=candidate).exists():
            return candidate


def register_hosteler(data, request_meta=None):
    """
    Self-registration service for student hostelers.
    Forces role to HOSTELER, sets is_verified=True.
    Roll number, email, and phone are optional.
    """
    validate_anti_bot(data, request_meta)

    raw_login_id = str(data.get("login_id", "") or "").strip().upper()
    if raw_login_id:
        if User.objects.filter(login_id__iexact=raw_login_id).exists():
            raise ValidationError(f"Roll number '{raw_login_id}' is already registered.")
        login_id = raw_login_id
    else:
        login_id = generate_student_login_id()

    email = str(data.get("email", "") or "").strip().lower()
    if email and User.objects.filter(email__iexact=email).exists():
        raise ValidationError(f"Email '{email}' is already in use.")

    full_name = str(data.get("full_name", "") or "").strip()
    if not full_name:
        raise ValidationError("Full Name is required.")

    phone = str(data.get("phone", "") or "").strip()
    password = data.get("password")
    if not password:
        raise ValidationError("Password is required.")

    hostel = data.get("hostel")
    if isinstance(hostel, (int, str)):
        hostel = Hostel.objects.filter(pk=hostel, is_active=True).first()
    if not hostel:
        raise ValidationError("A valid active hostel is required.")

    room = data.get("room")
    if room and isinstance(room, (int, str)):
        room = Room.objects.filter(pk=room, is_active=True).first()

    with transaction.atomic():
        user = User.objects.create_user(
            login_id=login_id,
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
            role=Role.HOSTELER,
            is_active=True,
            is_verified=True,
            registration_source="SELF_REGISTRATION",
            hostel=hostel,
            room=room,
            residence_set_at=timezone.now(),
        )

        from apps.accounts.models import AllowedRollNumber
        AllowedRollNumber.objects.filter(roll_no__iexact=login_id, used_by__isnull=True).update(
            used_by=user, used_at=timezone.now()
        )

        ResidenceHistory.objects.create(
            user=user,
            hostel=hostel,
            room=room,
            changed_by=user,
        )

    return user


def verify_resident(resident: User, verified_by: User):
    """Verifies a self-registered resident."""
    resident.is_verified = True
    resident.verified_by = verified_by
    resident.verified_at = timezone.now()
    resident.rejected_reason = ""
    resident.save(update_fields=["is_verified", "verified_by", "verified_at", "rejected_reason"])
    return resident


def reject_resident(resident: User, reason: str, rejected_by: User):
    """Rejects a resident registration with a mandatory reason."""
    reason = str(reason).strip()
    if not reason:
        raise ValidationError("A rejection reason is required.")
    resident.is_verified = False
    resident.rejected_reason = reason
    resident.save(update_fields=["is_verified", "rejected_reason"])
    return resident


def reset_resident_password(resident: User, reset_by: User) -> str:
    """Generates a secure temporary password and flags must_change_password."""
    temp_password = secrets.token_urlsafe(10)
    resident.set_password(temp_password)
    resident.must_change_password = True
    resident.save(update_fields=["password", "must_change_password"])
    return temp_password


def bulk_verify_residents(resident_ids, verified_by: User, allowed_hostel_id=None) -> int:
    """Bulk verifies resident accounts."""
    qs = User.objects.filter(id__in=resident_ids, role=Role.HOSTELER, is_verified=False)
    if allowed_hostel_id:
        qs = qs.filter(hostel_id=allowed_hostel_id)
    return qs.update(
        is_verified=True,
        verified_by=verified_by,
        verified_at=timezone.now(),
        rejected_reason="",
    )
