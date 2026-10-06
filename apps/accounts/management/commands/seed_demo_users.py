from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User
from apps.hostels.models import Block, GenderType, Hostel, Room


class Command(BaseCommand):
    help = "Seeds initial demo users for all system roles"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo hostels and rooms...")
        hostel_a, _ = Hostel.objects.get_or_create(
            code="HOSTEL_A",
            defaults={
                "name": "Boys Hostel A",
                "gender_type": GenderType.BOYS,
                "address": "North Campus, Sector 1",
            },
        )
        block_a, _ = Block.objects.get_or_create(hostel=hostel_a, name="Block 1")
        room_101, _ = Room.objects.get_or_create(
            block=block_a, room_number="101", defaults={"floor": 1, "capacity": 2}
        )

        users_data = [
            {
                "login_id": "admin",
                "full_name": "System Administrator",
                "role": Role.ADMIN,
                "escalation_level": 4,
                "is_staff": True,
                "is_superuser": True,
                "password": "admin123",
            },
            {
                "login_id": "chief_warden",
                "full_name": "Prof. S. K. Sharma",
                "role": Role.CHIEF_WARDEN,
                "escalation_level": 3,
                "is_staff": True,
                "password": "pass1234",
            },
            {
                "login_id": "warden_a",
                "full_name": "Dr. Ramesh Verma",
                "role": Role.WARDEN,
                "escalation_level": 2,
                "hostel": hostel_a,
                "is_staff": True,
                "password": "pass1234",
            },
            {
                "login_id": "caretaker_a1",
                "full_name": "Mukesh Kumar",
                "role": Role.CARETAKER,
                "escalation_level": 1,
                "hostel": hostel_a,
                "is_staff": True,
                "password": "pass1234",
            },
            {
                "login_id": "student1",
                "full_name": "Rahul Verma",
                "role": Role.HOSTELER,
                "escalation_level": None,
                "hostel": hostel_a,
                "room": room_101,
                "password": "pass1234",
            },
        ]

        for udata in users_data:
            password = udata.pop("password")
            user, created = User.objects.get_or_create(login_id=udata["login_id"], defaults=udata)
            user.set_password(password)
            user.save()
            action = "Created" if created else "Updated password for"
            self.stdout.write(f"{action} {user.login_id} ({user.get_role_display()})")

        self.stdout.write(self.style.SUCCESS("Demo users seeded successfully!"))
