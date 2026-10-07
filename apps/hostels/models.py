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
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

