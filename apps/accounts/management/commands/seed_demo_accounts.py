import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role, Theme, User
from apps.hostels.models import GenderType, Hostel, Room


class Command(BaseCommand):
    help = "Seeds or updates L0..L5 standardized demo accounts with default credentials"

    DEMO_PASSWORD = "me1234"

    def handle(self, *args, **options):
        # 1. Environment Guard (Section 4.2)
        if not settings.DEBUG and os.environ.get("ENABLE_DEMO_ACCOUNTS") != "1":
            raise CommandError(
                "Refusing to seed demo accounts in non-DEBUG environment without ENABLE_DEMO_ACCOUNTS=1."
            )

        self.stdout.write("Seeding standardized L0..L5 demo accounts...")

        # 2. Ensure base hostel and room exist for demo assignment
        hostel, _ = Hostel.objects.get_or_create(
            code="MH",
            defaults={
                "name": "Mandakini Hostel",
                "gender_type": GenderType.BOYS,
                "address": "Campus Hall of Residence, North Wing",
                "is_active": True,
            },
        )
        if not hostel.is_active:
            hostel.is_active = True
            hostel.save(update_fields=["is_active"])

        room_101, _ = Room.objects.get_or_create(
            hostel=hostel,
            room_number="101",
            defaults={
                "floor": 1,
                "capacity": 2,
                "is_active": True,
            },
        )
        if not room_101.is_active:
            room_101.is_active = True
            room_101.save(update_fields=["is_active"])

        # 3. L0..L5 Specification Matrix (Section 4.1)
        demo_accounts = [
            {
                "login_id": "L0",
                "full_name": "Aarav Sharma (Demo)",
                "email": "l0.hosteler@demo.local",
                "role": Role.HOSTELER,
                "escalation_level": None,
                "hostel": hostel,
                "room": room_101,
                "is_staff": False,
                "is_superuser": False,
                "theme": Theme.LIGHT,
            },
            {
                "login_id": "L1",
                "full_name": "Mukesh Caretaker (Demo)",
                "email": "l1.caretaker@demo.local",
                "role": Role.CARETAKER,
                "escalation_level": 1,
                "hostel": hostel,
                "room": None,
                "is_staff": True,
                "is_superuser": False,
                "theme": Theme.LIGHT,
            },
            {
                "login_id": "L2",
                "full_name": "Dr. Ramesh Warden (Demo)",
                "email": "l2.warden@demo.local",
                "role": Role.WARDEN,
                "escalation_level": 2,
                "hostel": hostel,
                "room": None,
                "is_staff": True,
                "is_superuser": False,
                "theme": Theme.SYSTEM,
            },
            {
                "login_id": "L3",
                "full_name": "Prof. Sunita Chief Warden (Demo)",
                "email": "l3.chiefwarden@demo.local",
                "role": Role.CHIEF_WARDEN,
                "escalation_level": 3,
                "hostel": None,
                "room": None,
                "is_staff": True,
                "is_superuser": False,
                "theme": Theme.SYSTEM,
            },
            {
                "login_id": "L4",
                "full_name": "Dr. K. V. Dean (Demo)",
                "email": "l4.dean@demo.local",
                "role": Role.DEAN,
                "escalation_level": 4,
                "hostel": None,
                "room": None,
                "is_staff": True,
                "is_superuser": False,
                "theme": Theme.SYSTEM,
            },
            {
                "login_id": "L5",
                "full_name": "System Administrator (Demo)",
                "email": "l5.admin@demo.local",
                "role": Role.ADMIN,
                "escalation_level": None,
                "hostel": None,
                "room": None,
                "is_staff": True,
                "is_superuser": True,
                "theme": Theme.DARK,
            },
        ]

        seeded_users = []
        for account in demo_accounts:
            login_id = account["login_id"]
            user, created = User.objects.get_or_create(
                login_id=login_id,
                defaults={
                    "full_name": account["full_name"],
                    "email": account["email"],
                    "role": account["role"],
                    "escalation_level": account["escalation_level"],
                    "hostel": account["hostel"],
                    "room": account["room"],
                    "is_staff": account["is_staff"],
                    "is_superuser": account["is_superuser"],
                    "is_active": True,
                    "is_verified": True,
                    "is_demo": True,
                    "must_change_password": False,
                    "theme": account["theme"],
                },
            )

            if not created:
                user.full_name = account["full_name"]
                user.email = account["email"]
                user.role = account["role"]
                user.escalation_level = account["escalation_level"]
                user.hostel = account["hostel"]
                user.room = account["room"]
                user.is_staff = account["is_staff"]
                user.is_superuser = account["is_superuser"]
                user.is_active = True
                user.is_verified = True
                user.is_demo = True
                user.must_change_password = False
                user.archived_at = None

            user.set_password(self.DEMO_PASSWORD)
            user.save()
            seeded_users.append(user)

            action_label = "Created" if created else "Updated"
            self.stdout.write(
                f"  [{user.login_id}] {action_label}: {user.full_name} ({user.get_role_display()})"
            )

        # 4. Set L1 as responsible staff for Mandakini Hostel
        l1_user = next((u for u in seeded_users if u.login_id == "L1"), None)
        if l1_user and hostel.responsible_staff != l1_user:
            hostel.responsible_staff = l1_user
            hostel.save(update_fields=["responsible_staff"])
            self.stdout.write(f"  Assigned L1 ({l1_user.full_name}) as responsible staff for {hostel.name}.")

        # 5. Legacy demo accounts: flag as is_demo and set password
        legacy_logins = [
            "student1",
            "caretaker1",
            "caretaker_a1",
            "warden1",
            "warden_bha",
            "warden_ghb",
            "chief_warden",
            "admin",
        ]
        legacy_updated = 0
        for leg_id in legacy_logins:
            leg_user = User.objects.filter(login_id=leg_id).first()
            if leg_user:
                leg_user.is_demo = True
                leg_user.set_password(self.DEMO_PASSWORD)
                leg_user.is_active = True
                leg_user.is_verified = True
                leg_user.must_change_password = False
                if leg_user.role == Role.ADMIN:
                    leg_user.escalation_level = None
                leg_user.save()
                legacy_updated += 1

        if legacy_updated:
            self.stdout.write(f"  Tagged {legacy_updated} legacy demo account(s) with is_demo=True and default password.")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded/refreshed {len(seeded_users)} demo accounts (L0..L5) with password '{self.DEMO_PASSWORD}'."
            )
        )
