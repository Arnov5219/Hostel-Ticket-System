from django.db import migrations


def set_all_hostelers_verified(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="HOSTELER").update(is_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_user_archived_at_user_last_password_reset_at_and_more"),
    ]

    operations = [
        migrations.RunPython(set_all_hostelers_verified, migrations.RunPython.noop),
    ]
