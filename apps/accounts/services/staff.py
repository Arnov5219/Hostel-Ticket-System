import re
import secrets

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, StaffAuditAction, StaffAuditLog, User
from apps.core.permissions import can_manage_user
from apps.hostels.models import Hostel
from apps.tickets.models import (
    ActivityAction,
    RoutingRule,
    Status,
    Ticket,
    TicketActivity,
)

LOGIN_ID_REGEX = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
ACTIVE_TICKET_STATUSES = [
    Status.OPEN,
    Status.ASSIGNED,
    Status.IN_PROGRESS,
    Status.ON_HOLD,
    Status.RESOLVED,
]


class ActiveTicketsError(ValidationError):
    def __init__(self, count: int, message: str = ""):
        self.count = count
        msg = message or f"Staff has {count} active tickets. A replacement staff member must be selected."
        super().__init__(msg)


def generate_temp_password(length: int = 12) -> str:
    """Generates a secure temporary password without look-alike characters."""
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_active_tickets_count(staff: User) -> int:
    return Ticket.objects.filter(assigned_to=staff, status__in=ACTIVE_TICKET_STATUSES).count()


def get_eligible_replacements(staff: User):
    """
    Returns eligible active staff candidates for ticket reassignment.
    Replacement eligibility is strictly by same role (Section 3.4).
    Prioritizes same hostel staff if applicable.
    """
    base_qs = User.objects.filter(
        is_active=True,
        archived_at__isnull=True,
        role=staff.role,
    ).exclude(id=staff.id)

    if staff.hostel:
        same_hostel = base_qs.filter(hostel=staff.hostel)
        others = base_qs.exclude(hostel=staff.hostel)
        return list(same_hostel) + list(others)

    return list(base_qs)


def create_staff(
    actor: User,
    full_name: str,
    login_id: str,
    role: str,
    hostel: Hostel | None = None,
    phone: str = "",
    email: str = "",
    password: str | None = None,
    is_l1_responsible: bool = False,
    ip: str | None = None,
) -> tuple[User, str]:
    """Creates a new staff account with full validation and audit logging."""
    dummy_target = User(role=role)
    if not can_manage_user(actor, dummy_target):
        raise PermissionDenied("You do not have permission to create this role.")

    login_id = (login_id or "").strip()
    if not LOGIN_ID_REGEX.match(login_id):
        raise ValidationError("Login ID must be 3-30 characters (letters, digits, ., _, -).")

    if User.objects.filter(login_id__iexact=login_id).exists():
        raise ValidationError(f"Login ID '{login_id}' is already taken.")

    if email:
        email = email.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(f"Email '{email}' is already in use.")

    full_name = (full_name or "").strip()
    if not full_name:
        raise ValidationError("Full name is required.")

    # Derive escalation level (Dean = 4, Admin = None)
    level_map = {
        Role.CARETAKER: 1,
        Role.WARDEN: 2,
        Role.CHIEF_WARDEN: 3,
        Role.DEAN: 4,
        Role.ADMIN: None,
    }
    escalation_level = level_map.get(role, None)

    # Campus-wide roles cannot have a specific hostel
    if role in [Role.CHIEF_WARDEN, Role.DEAN, Role.ADMIN]:
        hostel = None
    elif role in [Role.CARETAKER, Role.WARDEN] and not hostel:
        raise ValidationError(f"A hostel is required for {role.capitalize()}.")

    temp_password = ""
    if not password:
        temp_password = generate_temp_password(12)
        final_password = temp_password
    else:
        final_password = password

    with transaction.atomic():
        user = User.objects.create_user(
            login_id=login_id,
            email=email,
            password=final_password,
            full_name=full_name,
            phone=(phone or "").strip(),
            role=role,
            escalation_level=escalation_level,
            hostel=hostel,
            is_active=True,
            is_verified=True,
            must_change_password=True,
            registration_source="ADMIN",
            session_version=1,
        )

        if is_l1_responsible and hostel and role == Role.CARETAKER:
            hostel.responsible_staff = user
            hostel.save(update_fields=["responsible_staff"])

        StaffAuditLog.objects.create(
            actor=actor,
            target=user,
            action=StaffAuditAction.CREATED,
            details={
                "role": role,
                "hostel": hostel.code if hostel else "Campus-wide",
                "is_l1_responsible": bool(is_l1_responsible),
            },
            ip=ip,
        )

    return user, temp_password


def edit_staff(
    actor: User,
    target: User,
    full_name: str,
    phone: str = "",
    email: str = "",
    role: str | None = None,
    hostel: Hostel | None = None,
    ip: str | None = None,
) -> User:
    """Updates staff details with scope guards."""
    if not can_manage_user(actor, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    full_name = (full_name or "").strip()
    if not full_name:
        raise ValidationError("Full name is required.")

    if email:
        email = email.strip().lower()
        if User.objects.filter(email__iexact=email).exclude(id=target.id).exists():
            raise ValidationError(f"Email '{email}' is already in use.")

    role_changed = role and role != target.role
    hostel_changed = hostel != target.hostel

    if role_changed or hostel_changed:
        active_count = get_active_tickets_count(target)
        if active_count > 0:
            raise ValidationError(
                f"Cannot change role or hostel while staff has {active_count} active tickets. Reassign tickets first."
            )

    changes = {}
    if target.full_name != full_name:
        changes["full_name"] = {"from": target.full_name, "to": full_name}
        target.full_name = full_name

    phone = (phone or "").strip()
    if target.phone != phone:
        changes["phone"] = {"from": target.phone, "to": phone}
        target.phone = phone

    if target.email != email:
        changes["email"] = {"from": target.email, "to": email}
        target.email = email

    if role_changed:
        if not can_manage_user(actor, User(role=role)):
            raise PermissionDenied(f"You cannot assign role {role}.")
        changes["role"] = {"from": target.role, "to": role}
        target.role = role
        level_map = {Role.CARETAKER: 1, Role.WARDEN: 2, Role.CHIEF_WARDEN: 3, Role.DEAN: 4, Role.ADMIN: None}
        target.escalation_level = level_map.get(role, None)
        if role in [Role.CHIEF_WARDEN, Role.DEAN, Role.ADMIN]:
            target.hostel = None

    if hostel_changed:
        old_h = target.hostel.code if target.hostel else "None"
        new_h = hostel.code if hostel else "None"
        changes["hostel"] = {"from": old_h, "to": new_h}
        target.hostel = hostel

    with transaction.atomic():
        target.save()
        if changes:
            StaffAuditLog.objects.create(
                actor=actor,
                target=target,
                action=StaffAuditAction.UPDATED,
                details=changes,
                ip=ip,
            )

    return target


def change_staff_role(
    actor: User,
    target: User,
    new_role: str,
    actor_password: str,
    new_hostel: Hostel | None = None,
    allow_admin_fallback: bool = False,
    ip: str | None = None,
) -> User:
    """
    Role change (Admin only) is a separate audited action with the actor's password re-entered.
    Changing a person to Dean sets escalation_level=4 and clears their hostel;
    to Admin sets escalation_level=None and clears hostel.
    A role change is blocked while the person has active tickets in the old role's scope until they are reassigned.
    """
    if not can_manage_user(actor, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    if not actor.check_password(actor_password):
        raise ValidationError("Invalid administrator password. Re-authentication failed.")

    if target.role == new_role:
        return target

    # Guard: Cannot demote the last active Admin
    if target.role == Role.ADMIN and new_role != Role.ADMIN:
        active_admins = User.objects.filter(role=Role.ADMIN, is_active=True).exclude(id=target.id).count()
        if active_admins == 0:
            raise ValidationError("Cannot change the role of the last active Admin.")

    # Guard: Cannot demote the last active Dean unless another Dean exists or fallback accepted
    if target.role == Role.DEAN and new_role != Role.DEAN:
        active_deans = User.objects.filter(role=Role.DEAN, is_active=True).exclude(id=target.id).count()
        if active_deans == 0 and not allow_admin_fallback:
            raise ValidationError("Cannot change the role of the last active Dean without admin fallback confirmation.")

    # Guard: Cannot change role of the last active Chief Warden
    if target.role == Role.CHIEF_WARDEN and new_role != Role.CHIEF_WARDEN:
        active_cws = User.objects.filter(role=Role.CHIEF_WARDEN, is_active=True).exclude(id=target.id).count()
        if active_cws == 0:
            raise ValidationError("Cannot change the role of the last active Chief Warden.")

    # Blocked while the person has active tickets in old role's scope
    active_count = get_active_tickets_count(target)
    if active_count > 0:
        raise ValidationError(
            f"Cannot change role while staff has {active_count} active tickets. Reassign tickets first."
        )

    old_role = target.role
    target.role = new_role

    if new_role == Role.DEAN:
        target.escalation_level = 4
        target.hostel = None
    elif new_role == Role.ADMIN:
        target.escalation_level = None
        target.hostel = None
    elif new_role == Role.CHIEF_WARDEN:
        target.escalation_level = 3
        target.hostel = None
    elif new_role == Role.WARDEN:
        target.escalation_level = 2
        target.hostel = new_hostel or target.hostel
        if not target.hostel:
            raise ValidationError("A hostel is required for Warden.")
    elif new_role == Role.CARETAKER:
        target.escalation_level = 1
        target.hostel = new_hostel or target.hostel
        if not target.hostel:
            raise ValidationError("A hostel is required for Caretaker.")

    with transaction.atomic():
        target.save()
        StaffAuditLog.objects.create(
            actor=actor,
            target=target,
            action=StaffAuditAction.ROLE_CHANGED,
            details={"from": old_role, "to": new_role},
            ip=ip,
        )

    return target


def change_login_id(actor: User, target: User, new_login_id: str, ip: str | None = None) -> User:
    """Changes a staff member's login ID with audit logging and session invalidation."""
    if not can_manage_user(actor, target):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    new_login_id = (new_login_id or "").strip()
    if not LOGIN_ID_REGEX.match(new_login_id):
        raise ValidationError("Login ID must be 3-30 characters (letters, digits, ., _, -).")

    if User.objects.filter(login_id__iexact=new_login_id).exclude(id=target.id).exists():
        raise ValidationError(f"Login ID '{new_login_id}' is already taken.")

    old_login_id = target.login_id
    if old_login_id == new_login_id:
        return target

    with transaction.atomic():
        target.login_id = new_login_id
        target.session_version = (target.session_version or 0) + 1
        target.save(update_fields=["login_id", "session_version"])

        StaffAuditLog.objects.create(
            actor=actor,
            target=target,
            action=StaffAuditAction.LOGIN_ID_CHANGED,
            details={"from": old_login_id, "to": new_login_id},
            ip=ip,
        )

    return target


def reset_staff_password(
    actor: User,
    target: User,
    actor_password: str,
    ip: str | None = None,
) -> str:
    """Resets staff password, requiring actor password verification. Never logs password."""
    if not can_manage_user(actor, target):
        raise PermissionDenied("You do not have permission to reset this user's password.")

    if not actor.check_password(actor_password):
        raise ValidationError("Invalid administrator password. Re-authentication failed.")

    temp_password = generate_temp_password(12)

    with transaction.atomic():
        target.set_password(temp_password)
        target.must_change_password = True
        target.session_version = (target.session_version or 0) + 1
        target.last_password_reset_at = timezone.now()
        target.last_password_reset_by = actor
        target.save(
            update_fields=[
                "password",
                "must_change_password",
                "session_version",
                "last_password_reset_at",
                "last_password_reset_by",
            ]
        )

        StaffAuditLog.objects.create(
            actor=actor,
            target=target,
            action=StaffAuditAction.PASSWORD_RESET,
            details={"forced_change": True},
            ip=ip,
        )

    return temp_password


def assign_hostel(
    actor: User,
    staff: User,
    hostel: Hostel | None,
    make_l1_default: bool = False,
    ip: str | None = None,
) -> User:
    """Assigns staff to a hostel and optionally sets them as Level 1 responsible."""
    if not can_manage_user(actor, staff):
        raise PermissionDenied("You do not have permission to manage this staff member.")

    with transaction.atomic():
        old_hostel = staff.hostel
        staff.hostel = hostel
        staff.save(update_fields=["hostel"])

        if make_l1_default and hostel:
            hostel.responsible_staff = staff
            hostel.save(update_fields=["responsible_staff"])

        StaffAuditLog.objects.create(
            actor=actor,
            target=staff,
            action=StaffAuditAction.HOSTEL_CHANGED,
            details={
                "from": old_hostel.code if old_hostel else "None",
                "to": hostel.code if hostel else "None",
                "make_l1_default": make_l1_default,
            },
            ip=ip,
        )

    return staff


def deactivate_staff(
    actor: User,
    target: User,
    replacement: User | None = None,
    reason: str = "",
    allow_admin_fallback: bool = False,
    archive: bool = False,
    ip: str | None = None,
) -> User:
    """
    Safely deactivates or archives a staff member.
    Enforces active tickets guard, last-admin guard, and atomic reassignment.
    """
    if actor.id == target.id:
        raise ValidationError("You cannot deactivate your own account.")

    if not can_manage_user(actor, target):
        raise PermissionDenied("You do not have permission to deactivate this staff member.")

    if target.role == Role.ADMIN:
        active_admins = User.objects.filter(role=Role.ADMIN, is_active=True).exclude(id=target.id).count()
        if active_admins == 0:
            raise ValidationError("Cannot deactivate the last active Admin.")

    if target.role == Role.DEAN:
        other_deans = User.objects.filter(role=Role.DEAN, is_active=True).exclude(id=target.id).count()
        if other_deans == 0 and not allow_admin_fallback:
            raise ValidationError(
                "Cannot deactivate the last active Dean without admin fallback confirmation."
            )

    if target.role == Role.CHIEF_WARDEN:
        other_cw = User.objects.filter(role=Role.CHIEF_WARDEN, is_active=True).exclude(id=target.id).count()
        if other_cw == 0:
            raise ValidationError(
                "Cannot deactivate the last active Chief Warden."
            )

    active_tickets = Ticket.objects.filter(assigned_to=target, status__in=ACTIVE_TICKET_STATUSES)
    active_count = active_tickets.count()

    if active_count > 0:
        if not replacement:
            raise ActiveTicketsError(active_count)

        if replacement.id == target.id or not replacement.is_active or replacement.archived_at:
            raise ValidationError("A valid active replacement staff member is required.")

        if replacement.role != target.role:
            raise ValidationError(f"Replacement must have the same role ({target.get_role_display()}).")

    reason = (reason or "").strip()

    with transaction.atomic():
        # Select for update to guard concurrency
        locked_target = User.objects.select_for_update().get(id=target.id)
        locked_tickets = list(
            Ticket.objects.select_for_update().filter(
                assigned_to=locked_target, status__in=ACTIVE_TICKET_STATUSES
            )
        )

        if locked_tickets and replacement:
            reassign_note = (
                f"Staff deactivated. Reassigned: {reason}"
                if reason
                else f"Staff deactivated. Reassigned to {replacement.login_id}."
            )
            for t in locked_tickets:
                t.assigned_to = replacement
                t.save(update_fields=["assigned_to"])
                TicketActivity.objects.create(
                    ticket=t,
                    actor=actor,
                    action=ActivityAction.REASSIGNED,
                    from_value=locked_target.login_id,
                    to_value=replacement.login_id,
                    note=reassign_note,
                )

            RoutingRule.objects.filter(assignee=locked_target).update(assignee=replacement)
            Hostel.objects.filter(responsible_staff=locked_target).update(responsible_staff=replacement)

            StaffAuditLog.objects.create(
                actor=actor,
                target=locked_target,
                action=StaffAuditAction.TICKETS_REASSIGNED,
                details={
                    "count": len(locked_tickets),
                    "reassigned_to": replacement.login_id,
                    "reason": reason or "Staff deactivated/archived",
                },
                ip=ip,
            )
        else:
            Hostel.objects.filter(responsible_staff=locked_target).update(responsible_staff=None)

        locked_target.is_active = False
        locked_target.session_version = (locked_target.session_version or 0) + 1
        fields_to_update = ["is_active", "session_version"]

        action = StaffAuditAction.DEACTIVATED
        if archive:
            locked_target.archived_at = timezone.now()
            fields_to_update.append("archived_at")
            action = StaffAuditAction.ARCHIVED

        locked_target.save(update_fields=fields_to_update)

        StaffAuditLog.objects.create(
            actor=actor,
            target=locked_target,
            action=action,
            details={"reason": reason or ("Archived by admin" if archive else "Deactivated by admin")},
            ip=ip,
        )

    return locked_target


def archive_staff(
    actor: User,
    target: User,
    replacement: User | None = None,
    reason: str = "",
    allow_admin_fallback: bool = False,
    ip: str | None = None,
) -> User:
    """Soft-deletes (archives) a staff member."""
    return deactivate_staff(
        actor,
        target,
        replacement=replacement,
        reason=reason,
        allow_admin_fallback=allow_admin_fallback,
        archive=True,
        ip=ip,
    )


def reactivate_staff(actor: User, target: User, ip: str | None = None) -> User:
    """Reactivates a deactivated or archived staff member."""
    if not can_manage_user(actor, target):
        raise PermissionDenied("You do not have permission to reactivate this staff member.")

    with transaction.atomic():
        target.is_active = True
        target.archived_at = None
        target.must_change_password = True
        target.session_version = (target.session_version or 0) + 1
        target.save(update_fields=["is_active", "archived_at", "must_change_password", "session_version"])

        StaffAuditLog.objects.create(
            actor=actor,
            target=target,
            action=StaffAuditAction.REACTIVATED,
            details={},
            ip=ip,
        )

    return target
