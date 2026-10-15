from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.notifications.models import Notification
from apps.tickets.models import ActivityAction, Ticket, TicketActivity


def can_delete(user, ticket):
    """
    Checks if a user is permitted to delete a ticket per D7 and D8 rules.
    Returns: (can_delete: bool, reason_message: str)
    """
    if not user or not user.is_authenticated:
        return False, "Authentication required."

    if getattr(ticket, "is_deleted", False):
        return False, "Ticket is already deleted."

    # Admin and Chief Warden can delete any ticket in scope
    if user.is_admin or user.is_chief_warden:
        return True, ""

    # Warden can delete tickets in their assigned hostel
    if user.is_warden:
        if user.hostel_id == ticket.hostel_id:
            return True, ""
        return False, "Wardens can only delete tickets within their own hostel."

    # Hosteler rules (D7)
    if user.is_hosteler:
        if ticket.reporter_id != user.id:
            return False, "You can only delete tickets that you reported."

        if ticket.status not in ["OPEN", "ASSIGNED"]:
            return False, f"Ticket cannot be deleted because it is already {ticket.get_status_display().lower()}."

        # Check for staff comments
        has_staff_comment = ticket.comments.filter(
            author__role__in=[Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]
        ).exists()
        if has_staff_comment:
            return (
                False,
                "A staff member has already commented on or investigated this issue. Ask your Warden to close it.",
            )

        return True, ""

    # Caretakers and others
    return False, "You do not have permission to delete tickets."


def soft_delete(ticket, actor, reason=""):
    """
    Performs safe soft-delete of a ticket, logging activity, clearing pending notifications,
    and alerting assignees if applicable.
    """
    allowed, block_reason = can_delete(actor, ticket)
    if not allowed:
        raise ValidationError(block_reason or "You do not have permission to delete this ticket.")

    # Staff reason is mandatory (min 5 characters)
    if not actor.is_hosteler:
        clean_reason = (reason or "").strip()
        if len(clean_reason) < 5:
            raise ValidationError("A deletion reason of at least 5 characters is required for staff.")
    else:
        clean_reason = (reason or "").strip()

    with transaction.atomic():
        ticket.is_deleted = True
        ticket.deleted_at = timezone.now()
        ticket.deleted_by = actor
        ticket.delete_reason = clean_reason
        ticket.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "delete_reason"])

        # Write activity log
        actor_title = actor.full_name or actor.login_id
        action_note = f"Deleted by {actor_title}"
        if clean_reason:
            action_note += f": {clean_reason}"

        TicketActivity.objects.create(
            ticket=ticket,
            actor=actor,
            action=ActivityAction.DELETED,
            note=action_note,
        )

        # Notify assignee if staff was assigned
        if ticket.assigned_to and ticket.assigned_to != actor:
            Notification.objects.create(
                recipient=ticket.assigned_to,
                ticket=ticket,
                verb="TICKET_DELETED",
                message=f"Ticket {ticket.ticket_no} was deleted by {actor_title}." + (f" Reason: {clean_reason}" if clean_reason else ""),
            )

        # Mark all pending unread notifications for this ticket as read
        Notification.objects.filter(ticket=ticket, is_read=False).update(is_read=True)

    return ticket


def restore(ticket, actor):
    """
    Restores a soft-deleted ticket (Admin only).
    """
    if not (actor.is_admin or actor.is_superuser):
        raise ValidationError("Only administrators can restore deleted tickets.")

    if not ticket.is_deleted:
        raise ValidationError("Ticket is not deleted.")

    with transaction.atomic():
        ticket.is_deleted = False
        ticket.deleted_at = None
        ticket.deleted_by = None
        ticket.delete_reason = ""
        ticket.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "delete_reason"])

        TicketActivity.objects.create(
            ticket=ticket,
            actor=actor,
            action=ActivityAction.RESTORED,
            note=f"Ticket restored by {actor.full_name or actor.login_id}.",
        )

    return ticket


def generate_undo_token(ticket_no, user_id):
    """Generates a cryptographic timestamped token for 8-second undo."""
    signer = TimestampSigner()
    return signer.sign(f"{ticket_no}:{user_id}")


def undo_delete(ticket_no, actor, token):
    """
    Allows a hosteler to undo their own ticket deletion within the 8-second window.
    """
    signer = TimestampSigner()
    try:
        # Max age 12s to comfortably support 8s UI toast + network roundtrip
        val = signer.unsign(token, max_age=12)
        signed_ticket_no, signed_user_id = val.split(":")
        if signed_ticket_no != ticket_no or int(signed_user_id) != actor.id:
            raise ValidationError("Invalid undo token for this ticket and user.")
    except (SignatureExpired, BadSignature, ValueError):
        raise ValidationError("Undo window has expired (available for 8 seconds after deletion).")

    ticket = Ticket.all_objects.filter(ticket_no=ticket_no).first()
    if not ticket:
        raise ValidationError("Ticket not found.")

    if not ticket.is_deleted:
        return ticket

    if ticket.reporter_id != actor.id:
        raise ValidationError("Only the ticket reporter can undo deletion.")

    with transaction.atomic():
        ticket.is_deleted = False
        ticket.deleted_at = None
        ticket.deleted_by = None
        ticket.delete_reason = ""
        ticket.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "delete_reason"])

        TicketActivity.objects.create(
            ticket=ticket,
            actor=actor,
            action=ActivityAction.RESTORED,
            note="Deletion undone by reporter via toast undo.",
        )

    return ticket
