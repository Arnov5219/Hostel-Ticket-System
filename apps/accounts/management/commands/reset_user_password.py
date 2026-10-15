import secrets
import string
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Resets a user's password from CLI, generates a one-time temporary password, and forces password change on next login"

    def add_arguments(self, parser):
        parser.add_argument("login_id", type=str, help="Login ID / Roll number of the user")

    def handle(self, *args, **options):
        login_id = options["login_id"].strip()
        user = User.objects.filter(login_id__iexact=login_id).first()
        if not user:
            raise CommandError(f"User with login ID '{login_id}' not found.")

        # Generate a random 12-char password without look-alike characters
        alphabet = string.ascii_letters + string.digits
        temp_password = "".join(secrets.choice(alphabet) for _ in range(12))

        user.set_password(temp_password)
        user.must_change_password = True
        user.session_version = (user.session_version or 0) + 1
        user.last_password_reset_at = timezone.now()
        user.last_password_reset_by = None
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Password reset successfully for {user.login_id} ({user.full_name or user.role})."))
        self.stdout.write(self.style.WARNING(f"Temporary password (one-time display): {temp_password}"))
