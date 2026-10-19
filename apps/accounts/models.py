from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.core.models import TimeStampedModel


class Role(models.TextChoices):
    HOSTELER = "HOSTELER", "Hosteler"
    CARETAKER = "CARETAKER", "Caretaker (L1)"
    WARDEN = "WARDEN", "Hostel Warden (L2)"
    CHIEF_WARDEN = "CHIEF_WARDEN", "Chief Warden (L3)"
    DEAN = "DEAN", "Dean (L4)"
    ADMIN = "ADMIN", "Admin"


class Theme(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    LIGHT = "LIGHT", "Light"
    DARK = "DARK", "Dark"


ROLE_TO_LEVEL = {
    Role.CARETAKER: 1,
    Role.WARDEN: 2,
    Role.CHIEF_WARDEN: 3,
    Role.DEAN: 4,
}


class CustomUserManager(BaseUserManager):
    def create_user(self, login_id, password=None, **extra_fields):
        if not login_id:
            raise ValueError("The login_id must be set")
        login_id = login_id.strip()
        user = self.model(login_id=login_id, username=login_id, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, login_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("escalation_level", None)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(login_id, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    login_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Roll number for students or Employee ID for staff",
    )
    full_name = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.HOSTELER,
    )
    escalation_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="1 to 4 for staff members, null for hostelers",
    )
    hostel = models.ForeignKey(
        "hostels.Hostel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    room = models.ForeignKey(
        "hostels.Room",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="residents",
    )
    residence_set_at = models.DateTimeField(null=True, blank=True)
    theme = models.CharField(
        max_length=10,
        choices=Theme.choices,
        default=Theme.SYSTEM,
    )
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # Verification and Registration (Feature Section 3.3)
    is_verified = models.BooleanField(default=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    registration_source = models.CharField(
        max_length=20,
        choices=[("SELF", "Self-registered"), ("ADMIN", "Admin-created"), ("IMPORT", "Imported")],
        default="ADMIN",
    )
    rejected_reason = models.CharField(max_length=200, blank=True, default="")
    must_change_password = models.BooleanField(default=False)

    # Staff Lifecycle & Session Security (Addendum Section 7.1)
    session_version = models.PositiveIntegerField(default=1)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False, db_index=True, help_text="Flag for demo/seeded accounts")
    last_password_reset_at = models.DateTimeField(null=True, blank=True)
    last_password_reset_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resets_performed",
    )

    USERNAME_FIELD = "login_id"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    class Meta:
        ordering = ["login_id"]

    def __str__(self):
        name = self.full_name or self.login_id
        return f"{name} ({self.login_id})"

    def save(self, *args, **kwargs):
        if self.login_id:
            self.login_id = self.login_id.strip().upper()
        if not self.username:
            self.username = self.login_id
        # Automatically sync escalation_level if not explicitly set
        if self.role in ROLE_TO_LEVEL:
            if not self.escalation_level:
                self.escalation_level = ROLE_TO_LEVEL[self.role]
        elif self.role == Role.ADMIN:
            self.escalation_level = None
        super().save(*args, **kwargs)

    def can(self, capability):
        """Capability-based permission check."""
        from apps.core.permissions import has_capability
        return has_capability(self, capability)

    @property
    def is_hosteler(self):
        return self.role == Role.HOSTELER

    @property
    def is_caretaker(self):
        return self.role == Role.CARETAKER

    @property
    def is_warden(self):
        return self.role == Role.WARDEN

    @property
    def is_chief_warden(self):
        return self.role == Role.CHIEF_WARDEN

    @property
    def is_dean(self):
        return self.role == Role.DEAN

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_staff_member(self):
        return self.role in [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.DEAN, Role.ADMIN]

    @property
    def has_residence(self):
        """Residence is defined solely by hostel allocation."""
        if not self.is_hosteler:
            return True
        return bool(self.hostel_id)


class StaffAuditAction(models.TextChoices):
    CREATED = "CREATED", "Created"
    UPDATED = "UPDATED", "Updated"
    LOGIN_ID_CHANGED = "LOGIN_ID_CHANGED", "Login ID Changed"
    PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
    ROLE_CHANGED = "ROLE_CHANGED", "Role Changed"
    HOSTEL_CHANGED = "HOSTEL_CHANGED", "Hostel Changed"
    DEACTIVATED = "DEACTIVATED", "Deactivated"
    REACTIVATED = "REACTIVATED", "Reactivated"
    ARCHIVED = "ARCHIVED", "Archived"
    TICKETS_REASSIGNED = "TICKETS_REASSIGNED", "Tickets Reassigned"


class StaffAuditLog(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="staff_audits_performed",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_audit_logs",
    )
    action = models.CharField(max_length=30, choices=StaffAuditAction.choices)
    details = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.target.login_id} by {self.actor.login_id if self.actor else 'System'}"


class ResidenceHistory(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="residence_histories",
    )
    hostel = models.ForeignKey(
        "hostels.Hostel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residence_history_records",
    )
    room = models.ForeignKey(
        "hostels.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residence_history_records",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "Residence histories"

    def __str__(self):
        return f"{self.user} -> {self.hostel} {self.room}"


class AllowedRollNumber(TimeStampedModel):
    roll_no = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150, blank=True, default="")
    hostel = models.ForeignKey(
        "hostels.Hostel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allowed_roll_numbers",
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["roll_no"]

    def __str__(self):
        return self.roll_no
