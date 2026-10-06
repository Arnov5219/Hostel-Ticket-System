from django.core.management.base import BaseCommand

from apps.tickets.services.escalation import check_overdue


class Command(BaseCommand):
    help = "Checks SLA deadlines on all active tickets and automatically escalates or flags overdue"

    def handle(self, *args, **options):
        self.stdout.write("Checking active ticket SLA deadlines...")
        count = check_overdue()
        self.stdout.write(
            self.style.SUCCESS(f"Escalation check complete. Processed {count} ticket(s).")
        )
