from django.core.management.base import BaseCommand

from apps.hostels.models import GenderType, Hostel
from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Seeds real campus hostels (BH-1 to BH-12) without rooms"

    def add_arguments(self, parser):
        parser.add_argument("--hostels", type=int, default=12, help="Number of hostels to generate (default 12)")
        parser.add_argument("--prefix", type=str, default="BH", help="Hostel code prefix (default 'BH')")
        parser.add_argument(
            "--remove-demo",
            action="store_true",
            help="Remove legacy demo hostels (BH-A, GH-B, etc.) if they have no tickets",
        )

    def handle(self, *args, **options):
        num_hostels = options["hostels"]
        prefix = options["prefix"]
        remove_demo = options["remove_demo"]

        if remove_demo:
            demo_hostels = Hostel.objects.exclude(code__startswith=f"{prefix}-")
            for h in demo_hostels:
                ticket_count = Ticket.all_objects.filter(hostel=h).count()
                if ticket_count == 0:
                    self.stdout.write(f"Removing legacy demo hostel {h.code} (no tickets)...")
                    h.delete()
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Cannot delete demo hostel {h.code}: contains {ticket_count} tickets."
                        )
                    )

        total_hostels = 0

        for i in range(1, num_hostels + 1):
            code = f"{prefix}-{i}"
            name = f"Boys Hostel {i}"
            hostel, created = Hostel.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "gender_type": GenderType.BOYS,
                    "address": f"Campus Hall of Residence {i}",
                    "is_active": True,
                },
            )
            total_hostels += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded hostels: {total_hostels} hostels."
            )
        )
