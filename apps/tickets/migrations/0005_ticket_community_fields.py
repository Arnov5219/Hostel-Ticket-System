from django.db import migrations, models
from django.db.models import F


def populate_ticket_community_defaults(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    Ticket.objects.update(
        base_priority=F("priority"),
        level_started_at=F("created_at"),
        last_activity_at=F("updated_at"),
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0004_category_allow_community"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="visibility",
            field=models.CharField(
                choices=[("PRIVATE", "Private"), ("HOSTEL", "Share with my hostel")],
                default="PRIVATE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="ticket",
            name="show_reporter_name",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ticket",
            name="base_priority",
            field=models.CharField(
                choices=[
                    ("URGENT", "Urgent"),
                    ("HIGH", "High"),
                    ("MEDIUM", "Medium"),
                    ("LOW", "Low"),
                ],
                default="MEDIUM",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="ticket",
            name="repost_count",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="ticket",
            name="level_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="last_activity_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="ticket",
            name="community_hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ticket",
            name="last_notified_threshold",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=["hostel", "visibility", "status", "last_activity_at"],
                name="tickets_tic_hostel__e6d3bf_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=["hostel", "repost_count"],
                name="tickets_tic_hostel__459b79_idx",
            ),
        ),
        migrations.RunPython(
            populate_ticket_community_defaults,
            noop,
        ),
    ]
