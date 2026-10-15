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

    def community_for(self, user):
        """Filters tickets visible in community feed for user. Non-hostelers get none()."""
        if not user or not user.is_authenticated:
            return self.none()

        from apps.core.permissions import Capability, has_capability
        if not has_capability(user, Capability.COMMUNITY_ACCESS):
            return self.none()

        if not user.hostel:
            return self.none()

        from datetime import timedelta
        from django.utils import timezone
        from apps.tickets.models import TicketVisibility

        seven_days_ago = timezone.now() - timedelta(days=7)
        qs = self.filter(
            hostel=user.hostel,
            visibility=TicketVisibility.HOSTEL,
            community_hidden=False,
            category__allow_community=True,
        ).filter(
            models.Q(status__in=["OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD"])
            | models.Q(status="RESOLVED", resolved_at__gte=seven_days_ago)
        ).exclude(reporter=user)
        return qs


class ActiveTicketManager(models.Manager.from_queryset(TicketQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllTicketManager(models.Manager.from_queryset(TicketQuerySet)):
    pass


# Backwards compatibility alias
TicketManager = ActiveTicketManager
