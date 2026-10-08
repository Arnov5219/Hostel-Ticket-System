from django.core.management.base import BaseCommand

from apps.hostels.models import GenderType, Hostel, Room
from apps.hostels.services import generate_rooms
from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = "Seeds real campus hostels (BH-1 to BH-12) and generates rooms per floor"

    def add_arguments(self, parser):
        parser.add_argument("--hostels", type=int, default=12, help="Number of hostels to generate (default 12)")
        parser.add_argument("--prefix", type=str, default="BH", help="Hostel code prefix (default 'BH')")
        parser.add_argument("--floors", type=int, default=3, help="Number of floors per hostel (default 3)")
        parser.add_argument("--rooms-per-floor", type=int, default=40, help="Rooms per floor (default 40)")
        parser.add_argument("--capacity", type=int, default=2, help="Bed capacity per room (default 2)")
        parser.add_argument("--first-floor", type=int, default=1, help="Starting floor number (default 1)")
        parser.add_argument(
            "--remove-demo",
            action="store_true",
            help="Remove legacy demo hostels (BH-A, GH-B, etc.) if they have no tickets",
        )

    def handle(self, *args, **options):
        num_hostels = options["hostels"]
        prefix = options["prefix"]
        floors = options["floors"]
        rooms_per_floor = options["rooms_per_floor"]
        capacity = options["capacity"]
        first_floor = options["first_floor"]
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
        total_rooms = 0

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
            rooms_created = generate_rooms(
                hostel=hostel,
                floors=floors,
                rooms_per_floor=rooms_per_floor,
                capacity=capacity,
                first_floor=first_floor,
            )
            total_rooms += hostel.rooms.count()

        distinct_floors = num_hostels * floors
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded hostels: {total_hostels} hostels, {distinct_floors} floors, {total_rooms} rooms."
            )
        )
