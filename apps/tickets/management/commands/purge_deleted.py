from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Permanently removes tickets soft-deleted more than 90 days ago. Requires --confirm."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirmation flag required to actually purge records.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days a ticket must have been soft-deleted before purging (default: 90).",
        )

    def handle(self, *args, **options):
        confirm = options.get("confirm", False)
        days = options.get("days", 90)
        cutoff = timezone.now() - timedelta(days=days)

        candidates = Ticket.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff)
        count = candidates.count()

        if not confirm:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {count} ticket(s) soft-deleted more than {days} days ago found. "
                    "Run with --confirm to permanently purge."
                )
            )
            return

        candidates.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully purged {count} ticket(s) soft-deleted more than {days} days ago."
            )
        )
