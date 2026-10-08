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

    def community_for(self, user):
        """Filters tickets visible in community feed for user."""
        if not user or not user.is_authenticated:
            return self.none()

        from datetime import timedelta
        from django.utils import timezone
        from apps.tickets.models import TicketVisibility

        if user.is_superuser or user.is_admin or user.is_chief_warden:
            return self.filter(visibility=TicketVisibility.HOSTEL, community_hidden=False)

        if not user.hostel:
            return self.none()

        seven_days_ago = timezone.now() - timedelta(days=7)
        qs = self.filter(
            hostel=user.hostel,
            visibility=TicketVisibility.HOSTEL,
            community_hidden=False,
            category__allow_community=True,
        ).filter(
            models.Q(status__in=["OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD"])
            | models.Q(status="RESOLVED", resolved_at__gte=seven_days_ago)
        )
        if user.is_hosteler:
            qs = qs.exclude(reporter=user)
        return qs


class TicketManager(models.Manager.from_queryset(TicketQuerySet)):
    pass
