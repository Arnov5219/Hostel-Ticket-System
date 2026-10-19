import os

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, Tags, register


def check_demo_accounts_in_production(app_configs, **kwargs):
    """Deploy check: error if demo accounts with default passwords exist in production."""
    errors = []
    if not settings.DEBUG and os.environ.get("ALLOW_DEMO_ACCOUNTS") != "1":
        from apps.accounts.models import User
        try:
            demo_count = User.objects.filter(is_demo=True).count()
            if demo_count > 0:
                errors.append(
                    Error(
                        f"Found {demo_count} demo account(s) with known default passwords in production database.",
                        hint="Run 'python manage.py purge_demo_accounts --confirm' or set ALLOW_DEMO_ACCOUNTS=1 for demo environments.",
                        id="accounts.E001",
                    )
                )
        except Exception:
            pass
    return errors


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        register(Tags.security, deploy=True)(check_demo_accounts_in_production)
