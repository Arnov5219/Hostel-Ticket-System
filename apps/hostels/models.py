from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class GenderType(models.TextChoices):
    BOYS = "BOYS", "Boys"
    GIRLS = "GIRLS", "Girls"
    COED = "COED", "Co-ed"


class Hostel(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    gender_type = models.CharField(
        max_length=10,
        choices=GenderType.choices,
        default=GenderType.BOYS,
    )
    address = models.TextField(blank=True, default="")
    responsible_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_hostels",
        help_text="Primary Level 1 staff member responsible for all tickets in this hostel",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def floors(self):
        return list(self.rooms.values_list("floor", flat=True).distinct().order_by("floor"))

    @property
    def room_count(self):
        return self.rooms.filter(is_active=True).count()

    @property
    def total_room_count(self):
        return self.rooms.count()

    @property
    def resident_count(self):
        if hasattr(self, "_resident_count"):
            return self._resident_count
        from apps.accounts.models import Role, User
        return User.objects.filter(hostel=self, role=Role.HOSTELER, is_active=True).count()

    @resident_count.setter
    def resident_count(self, value):
        self._resident_count = value


class Room(TimeStampedModel):
    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    floor = models.PositiveSmallIntegerField(default=1)
    room_number = models.CharField(max_length=10)
    capacity = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["floor", "room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "room_number"],
                name="unique_hostel_room_number",
            )
        ]
        indexes = [
            models.Index(fields=["hostel", "floor"]),
        ]

    def __str__(self):
        return f"{self.hostel.code} - {self.room_number}"

    @property
    def resident_count(self):
        if hasattr(self, "_resident_count"):
            return self._resident_count
        return self.residents.filter(is_active=True).count()

    @resident_count.setter
    def resident_count(self, value):
        self._resident_count = value
