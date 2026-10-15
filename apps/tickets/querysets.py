from django.db import models


class TicketQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Filters tickets by user's capability and assigned scope."""
        if not user or not user.is_authenticated:
            return self.none()

        from apps.core.permissions import Capability, has_capability

        if has_capability(user, Capability.VIEW_ALL_TICKETS):
            return self.all()

        if has_capability(user, Capability.VIEW_HOSTEL_TICKETS):
            if user.hostel:
                return self.filter(models.Q(hostel=user.hostel) | models.Q(assigned_to=user))
            return self.filter(assigned_to=user)

        if has_capability(user, Capability.VIEW_ASSIGNED_TICKETS):
            if user.hostel:
                return self.filter(models.Q(hostel=user.hostel) | models.Q(assigned_to=user))
            return self.filter(assigned_to=user)

        if getattr(user, "role", None) == "HOSTELER":
            return self.filter(reporter=user)

        return self.none()



class ActiveTicketManager(models.Manager.from_queryset(TicketQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllTicketManager(models.Manager.from_queryset(TicketQuerySet)):
    pass


# Backwards compatibility alias
TicketManager = ActiveTicketManager
