from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ResidenceHistory


def set_residence(user, hostel, block, room, changed_by=None):
    """
    Validates and updates the residence (hostel, block, room) for a user.
    Records a ResidenceHistory log entry.
    """
    if not hostel or not block or not room:
        raise ValidationError("Hostel, Block, and Room are all required.")

    if not hostel.is_active:
        raise ValidationError(f"Hostel '{hostel.name}' is currently inactive.")

    if not block.is_active:
        raise ValidationError(f"Block '{block.name}' is currently inactive.")

    if not room.is_active:
        raise ValidationError(f"Room '{room.room_number}' is currently inactive.")

    # Validate hierarchy chain
    if block.hostel_id != hostel.id:
        raise ValidationError(f"Block '{block.name}' does not belong to hostel '{hostel.name}'.")

    if room.block_id != block.id:
        raise ValidationError(f"Room '{room.room_number}' does not belong to block '{block.name}'.")

    # Capacity enforcement check if configured
    enforce_capacity = getattr(settings, "ENFORCE_ROOM_CAPACITY", False)
    current_occupants = room.residents.exclude(id=user.id).count()
    if enforce_capacity and current_occupants >= room.capacity:
        raise ValidationError(f"Room {room.room_number} is at full capacity ({room.capacity} residents).")

    with transaction.atomic():
        user.hostel = hostel
        user.room = room
        user.residence_set_at = timezone.now()
        user.save(update_fields=["hostel", "room", "residence_set_at"])

        ResidenceHistory.objects.create(
            user=user,
            hostel=hostel,
            room=room,
            changed_by=changed_by or user,
        )

    return user
