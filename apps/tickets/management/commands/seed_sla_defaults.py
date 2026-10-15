from django.core.management.base import BaseCommand

from apps.tickets.models import SLAPolicy
from apps.tickets.services.sla import DEFAULT_SLA_HOURS


class Command(BaseCommand):
    help = "Idempotently restores default SLA policy rows for all priorities and escalation levels"

    def handle(self, *args, **options):
        self.stdout.write("Restoring default SLA policies...")
        count = 0
        for priority, levels in DEFAULT_SLA_HOURS.items():
            for level, hours in levels.items():
                policy, created = SLAPolicy.objects.update_or_create(
                    priority=priority,
                    level=level,
                    defaults={"hours": hours},
                )
                action = "Created" if created else "Updated"
                self.stdout.write(f"  {action} {priority} L{level} -> {hours}h")
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully ensured {count} SLA policy rows."))
