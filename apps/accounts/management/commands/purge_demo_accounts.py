from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.hostels.models import Hostel
from apps.notifications.models import Notification
from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Purges all seeded demo accounts (is_demo=True) and safely disassociates their tickets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm deletion of demo accounts. Without this flag, only a dry run is executed.",
        )

    def handle(self, *args, **options):
        confirm = options.get("confirm", False)

        demo_users = User.objects.filter(is_demo=True)
        count = demo_users.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No demo accounts (is_demo=True) found in database."))
            return

        self.stdout.write(f"Found {count} demo account(s):")
        for u in demo_users:
            assigned_count = Ticket.objects.filter(assigned_to=u).count()
            reported_count = Ticket.objects.filter(reporter=u).count()
            self.stdout.write(
                f"  - [{u.login_id}] {u.full_name} ({u.get_role_display()}): {assigned_count} assigned, {reported_count} reported"
            )

        if not confirm:
            self.stdout.write(
                self.style.WARNING(
                    "\nDry run complete. To permanently delete these demo accounts, re-run with --confirm:\n"
                    "  python manage.py purge_demo_accounts --confirm"
                )
            )
            return

        self.stdout.write("\nPurging demo accounts with --confirm...")
        with transaction.atomic():
            demo_user_ids = list(demo_users.values_list("id", flat=True))

            # 1. Clear responsible_staff references on Hostels
            Hostel.objects.filter(responsible_staff_id__in=demo_user_ids).update(responsible_staff=None)

            # 2. Reassign tickets assigned to demo users to None
            reassigned = Ticket.objects.filter(assigned_to_id__in=demo_user_ids).update(assigned_to=None)
            if reassigned:
                self.stdout.write(f"  Unassigned {reassigned} ticket(s) previously assigned to demo staff.")

            # 3. Clean up notifications for demo users
            Notification.objects.filter(recipient_id__in=demo_user_ids).delete()

            # 4. Delete demo tickets where reporter is demo user
            deleted_tickets = Ticket.all_objects.filter(reporter_id__in=demo_user_ids).delete()
            self.stdout.write(f"  Cleaned up demo tickets reported by demo users: {deleted_tickets[0]} records.")

            # 5. Delete demo users
            deleted_count, _ = demo_users.delete()
            self.stdout.write(
                self.style.SUCCESS(f"Successfully purged {count} demo account(s) from database.")
            )
