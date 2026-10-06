from django.core.management.base import BaseCommand

from apps.tickets.services.status import auto_close_resolved_tickets


class Command(BaseCommand):
    help = "Automatically closes tickets resolved more than 72 hours ago"

    def handle(self, *args, **options):
        count = auto_close_resolved_tickets(hours_threshold=72)
        self.stdout.write(
            self.style.SUCCESS(f"Successfully auto-closed {count} resolved ticket(s).")
        )
