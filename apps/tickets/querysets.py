from django.db import models


class TicketQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Filters tickets by user's role and assigned scope."""
        if not user or not user.is_authenticated:
            return self.none()

        if user.is_superuser or user.is_admin or user.is_chief_warden:
            return self.all()

        if user.is_warden or user.is_caretaker:
            if user.hostel:
                return self.filter(models.Q(hostel=user.hostel) | models.Q(assigned_to=user))
            return self.filter(assigned_to=user)

        if user.is_hosteler:
            return self.filter(reporter=user)

        return self.none()


class TicketManager(models.Manager.from_queryset(TicketQuerySet)):
    pass
