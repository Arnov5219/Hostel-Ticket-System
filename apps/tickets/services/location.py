from django.core.exceptions import ValidationError

from apps.hostels.models import Block, Hostel, Room


def validate_location(hostel_id, block_id, room_id, reporter=None):
    """
    Validates that hostel, block, and room exist, are active, and form a valid hierarchy chain:
    hostel -> block -> room.

    Determines if the ticket is outside the reporter's own hostel.
    Returns: (hostel, block, room, outside_own_hostel)
    """
    if not hostel_id:
        raise ValidationError({"hostel": "Please select a hostel."})
    if not block_id:
        raise ValidationError({"block": "Please select a block."})
    if not room_id:
        raise ValidationError({"room": "Please select a room."})

    try:
        hostel = Hostel.objects.get(pk=hostel_id)
    except (Hostel.DoesNotExist, ValueError):
        raise ValidationError({"hostel": "Selected hostel does not exist."})

    if not hostel.is_active:
        raise ValidationError({"hostel": f"Hostel '{hostel.name}' is currently inactive."})

    try:
        block = Block.objects.get(pk=block_id)
    except (Block.DoesNotExist, ValueError):
        raise ValidationError({"block": "Selected block does not exist."})

    if not block.is_active:
        raise ValidationError({"block": f"Block '{block.name}' is currently inactive."})

    if block.hostel_id != hostel.id:
        raise ValidationError({"block": f"Block '{block.name}' does not belong to '{hostel.name}'."})

    try:
        room = Room.objects.get(pk=room_id)
    except (Room.DoesNotExist, ValueError):
        raise ValidationError({"room": "Selected room does not exist."})

    if not room.is_active:
        raise ValidationError({"room": f"Room '{room.room_number}' is currently inactive."})

    if room.block_id != block.id:
        raise ValidationError({"room": f"Room '{room.room_number}' does not belong to block '{block.name}'."})

    outside_own_hostel = False
    if reporter and reporter.hostel_id:
        outside_own_hostel = bool(reporter.hostel_id != hostel.id)

    return hostel, block, room, outside_own_hostel
