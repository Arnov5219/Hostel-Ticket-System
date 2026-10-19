from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds initial demo users for all system roles"

    def handle(self, *args, **options):
        call_command("seed_demo_accounts")
        self.stdout.write(self.style.SUCCESS("Demo users seeded successfully!"))
