import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("announcements", "0001_initial"),
        ("notifications", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="announcement",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="announcements.announcement",
            ),
        ),
    ]
