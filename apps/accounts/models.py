from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    HOSTELER = "HOSTELER", "Hosteler"
    CARETAKER = "CARETAKER", "Caretaker (L1)"
    WARDEN = "WARDEN", "Hostel Warden (L2)"
    CHIEF_WARDEN = "CHIEF_WARDEN", "Chief Warden (L3)"
    ADMIN = "ADMIN", "Admin / Dean (L4)"


ROLE_TO_LEVEL = {
    Role.CARETAKER: 1,
    Role.WARDEN: 2,
    Role.CHIEF_WARDEN: 3,
    Role.ADMIN: 4,
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
        extra_fields.setdefault("escalation_level", 4)

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
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    USERNAME_FIELD = "login_id"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    class Meta:
        ordering = ["login_id"]

    def __str__(self):
        name = self.full_name or self.login_id
        return f"{name} ({self.login_id})"

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.login_id
        # Automatically sync escalation_level if not explicitly set
        if not self.escalation_level and self.role in ROLE_TO_LEVEL:
            self.escalation_level = ROLE_TO_LEVEL[self.role]
        super().save(*args, **kwargs)

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
    def is_admin(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_staff_member(self):
        return self.role in [Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]
