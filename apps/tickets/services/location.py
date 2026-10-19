from django.core.exceptions import ValidationError

from apps.hostels.models import Hostel, Room


def validate_location(hostel_id, room_id=None, reporter=None, floor=None):
    """
    Validates that hostel (and optional room) exist and are active.
    Determines if the ticket is outside the reporter's own hostel.
    Returns: (hostel, room, outside_own_hostel)
    """
    if not hostel_id:
        raise ValidationError({"hostel": "Please select a hostel."})

    try:
        hostel = Hostel.objects.get(pk=hostel_id)
    except (Hostel.DoesNotExist, ValueError):
        raise ValidationError({"hostel": "Selected hostel does not exist."})

    if not hostel.is_active:
        raise ValidationError({"hostel": f"Hostel '{hostel.name}' is currently inactive."})

    room = None
    if room_id:
        try:
            room = Room.objects.get(pk=room_id)
        except (Room.DoesNotExist, ValueError):
            raise ValidationError({"room": "Selected room does not exist."})

        if not room.is_active:
            raise ValidationError({"room": f"Room '{room.room_number}' is currently inactive."})

        if room.hostel_id != hostel.id:
            raise ValidationError({"room": f"Room '{room.room_number}' does not belong to hostel '{hostel.code}'."})

        if floor is not None and str(room.floor) != str(floor):
            raise ValidationError({"room": f"Room '{room.room_number}' is not on floor {floor}."})

    outside_own_hostel = False
    if reporter and reporter.hostel_id:
        outside_own_hostel = bool(reporter.hostel_id != hostel.id)

    return hostel, room, outside_own_hostel
