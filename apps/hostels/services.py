from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel
from apps.tickets.models import Status, Ticket


def create_hostel(
    name: str,
    code: str,
    gender_type: str,
    responsible_staff: User | None = None,
    responsible_warden: User | None = None,
    is_active: bool = True,
    **kwargs,
) -> Hostel:
    """Creates a new hostel with validation rules."""
    code = code.strip().upper()
    if Hostel.objects.filter(code__iexact=code).exists():
        raise ValidationError(f"Hostel with code '{code}' already exists.")

    if responsible_staff:
        if not responsible_staff.is_active:
            raise ValidationError("Cannot assign an inactive staff member as responsible staff.")
        if responsible_staff.role != Role.CARETAKER and responsible_staff.escalation_level != 1:
            raise ValidationError("Responsible staff must be a Level 1 staff member (Caretaker).")

    if responsible_warden:
        if not responsible_warden.is_active:
            raise ValidationError("Cannot assign an inactive staff member as responsible warden.")
        if responsible_warden.role != Role.WARDEN and responsible_warden.escalation_level != 2:
            raise ValidationError("Responsible warden must be a Level 2 staff member (Warden).")

    with transaction.atomic():
        hostel = Hostel.objects.create(
            name=name.strip(),
            code=code,
            gender_type=gender_type,
            responsible_staff=responsible_staff,
            responsible_warden=responsible_warden,
            is_active=is_active,
        )
        if responsible_staff and not responsible_staff.hostel:
            responsible_staff.hostel = hostel
            responsible_staff.save(update_fields=["hostel"])
        if responsible_warden and not responsible_warden.hostel:
            responsible_warden.hostel = hostel
            responsible_warden.save(update_fields=["hostel"])

    return hostel


def update_hostel(hostel: Hostel, **fields) -> Hostel:
    """Updates hostel details with validation."""
    code = fields.get("code")
    if code:
        code = code.strip().upper()
        if Hostel.objects.filter(code__iexact=code).exclude(pk=hostel.pk).exists():
            raise ValidationError(f"Hostel with code '{code}' already exists.")
        hostel.code = code

    if "name" in fields:
        hostel.name = fields["name"].strip()
    if "gender_type" in fields:
        hostel.gender_type = fields["gender_type"]
    if "is_active" in fields:
        hostel.is_active = fields["is_active"]

    if "responsible_staff" in fields:
        staff = fields["responsible_staff"]
        if staff:
            if not staff.is_active:
                raise ValidationError("Cannot assign an inactive staff member as responsible staff.")
            if staff.role != Role.CARETAKER and staff.escalation_level != 1:
                raise ValidationError("Responsible staff must be a Level 1 staff member (Caretaker).")
        hostel.responsible_staff = staff

    if "responsible_warden" in fields:
        warden = fields["responsible_warden"]
        if warden:
            if not warden.is_active:
                raise ValidationError("Cannot assign an inactive staff member as responsible warden.")
            if warden.role != Role.WARDEN and warden.escalation_level != 2:
                raise ValidationError("Responsible warden must be a Level 2 staff member (Warden).")
        hostel.responsible_warden = warden

    hostel.save()
    return hostel


def change_hostel_assignments(
    hostel: Hostel,
    caretaker: User | None = None,
    warden: User | None = None,
    update_caretaker: bool = True,
    update_warden: bool = True,
    actor: User | None = None,
) -> Hostel:
    """
    Assigns or updates the Level 1 Caretaker and/or Level 2 Warden for a hostel.
    Allows changing caretaker without changing warden, and vice versa, or both together.
    """
    with transaction.atomic():
        if update_caretaker:
            if caretaker:
                if not caretaker.is_active:
                    raise ValidationError("Cannot assign an inactive staff member as Caretaker.")
                if caretaker.role != Role.CARETAKER and caretaker.escalation_level != 1:
                    raise ValidationError("Responsible staff must be a Level 1 staff member (Caretaker).")
                if caretaker.hostel != hostel:
                    caretaker.hostel = hostel
                    caretaker.save(update_fields=["hostel"])
            hostel.responsible_staff = caretaker

        if update_warden:
            if warden:
                if not warden.is_active:
                    raise ValidationError("Cannot assign an inactive staff member as Warden.")
                if warden.role != Role.WARDEN and warden.escalation_level != 2:
                    raise ValidationError("Responsible warden must be a Level 2 staff member (Warden).")
                if warden.hostel != hostel:
                    warden.hostel = hostel
                    warden.save(update_fields=["hostel"])
            hostel.responsible_warden = warden

        hostel.save(update_fields=["responsible_staff", "responsible_warden", "updated_at"])

    return hostel


def change_hostel_responsible_staff(hostel: Hostel, staff: User, actor: User | None = None) -> Hostel:
    """Assigns or changes the Level 1 responsible staff member for a hostel."""
    return change_hostel_assignments(
        hostel,
        caretaker=staff,
        update_caretaker=True,
        update_warden=False,
        actor=actor,
    )


def assign_staff_to_hostel(staff: User, hostel: Hostel | None, actor: User | None = None) -> User:
    """Changes hostel assignment for a staff member."""
    staff.hostel = hostel
    staff.save(update_fields=["hostel"])
    return staff


def get_active_tickets_count_for_hostel(hostel: Hostel) -> int:
    """Returns the count of unresolved tickets for a hostel."""
    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    return Ticket.objects.filter(hostel=hostel, status__in=active_statuses).count()


def get_active_tickets_count_for_staff(staff: User) -> int:
    """Returns the count of unresolved tickets assigned to a staff member."""
    active_statuses = [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD]
    return Ticket.objects.filter(assigned_to=staff, status__in=active_statuses).count()


def deactivate_hostel(hostel: Hostel) -> tuple[Hostel, int]:
    """
    Marks a hostel as inactive rather than deleting it.
    Returns (hostel, active_tickets_count).
    """
    active_count = get_active_tickets_count_for_hostel(hostel)
    hostel.is_active = False
    hostel.save(update_fields=["is_active", "updated_at"])
    return hostel, active_count


def deactivate_staff(staff: User, replacement_staff: User | None = None) -> tuple[User, int]:
    """
    Deactivates a staff member with safeguards:
    - If the staff is responsible for active hostels, requires replacement active L1 staff.
    - Warns about unresolved tickets.
    """
    responsible_active_hostels = Hostel.objects.filter(responsible_staff=staff, is_active=True)
    if responsible_active_hostels.exists():
        if not replacement_staff:
            hostel_names = ", ".join([h.name for h in responsible_active_hostels])
            raise ValidationError(
                f"Cannot deactivate {staff.full_name or staff.login_id} because they are the responsible Level 1 staff "
                f"for active hostel(s): {hostel_names}. Please assign a replacement Level 1 staff member first."
            )
        if not replacement_staff.is_active:
            raise ValidationError("Replacement staff must be active.")
        if replacement_staff.role != Role.CARETAKER and replacement_staff.escalation_level != 1:
            raise ValidationError("Replacement staff must be a Level 1 staff member (Caretaker).")

        # Reassign responsible staff for those hostels
        for h in responsible_active_hostels:
            h.responsible_staff = replacement_staff
            h.save(update_fields=["responsible_staff", "updated_at"])

    active_tickets_count = get_active_tickets_count_for_staff(staff)
    staff.is_active = False
    staff.save(update_fields=["is_active"])

    return staff, active_tickets_count


def generate_rooms(
    hostel: Hostel,
    floors: int = 3,
    rooms_per_floor: int = 40,
    capacity: int = 2,
    first_floor: int = 1,
) -> int:
    """
    Generates missing rooms for a hostel across floors.
    Idempotent: skips existing rooms.
    Returns: count of newly created rooms.
    """
    from apps.hostels.models import Room

    created_count = 0
    with transaction.atomic():
        for floor_idx in range(floors):
            floor = first_floor + floor_idx
            for n in range(1, rooms_per_floor + 1):
                room_number = f"{floor * 100 + n}"
                _, created = Room.objects.get_or_create(
                    hostel=hostel,
                    room_number=room_number,
                    defaults={
                        "floor": floor,
                        "capacity": capacity,
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
    return created_count


def room_options(hostel: Hostel, floor: int | None = None):
    """
    Returns active rooms for a hostel (optionally filtered by floor)
    annotated with their current resident count.
    """
    from django.db.models import Count

    from apps.hostels.models import Room

    qs = Room.objects.filter(hostel=hostel, is_active=True)
    if floor is not None:
        qs = qs.filter(floor=floor)
    return qs.annotate(resident_count=Count("residents", filter=models.Q(residents__is_active=True))).order_by("floor", "room_number")


def natural_sort_key(item):
    """
    Helper for natural sorting strings like 'BH-2' before 'BH-10'.
    Accepts Hostel object, code, or string.
    """
    import re

    s = item
    if hasattr(item, "code"):
        s = item.code
    elif hasattr(item, "name"):
        s = item.name
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]
