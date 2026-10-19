import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_is_internal_to_scope(apps, schema_editor):
    TicketComment = apps.get_model("tickets", "TicketComment")
    TicketComment.objects.filter(is_internal=True).update(scope="INTERNAL")
    TicketComment.objects.filter(is_internal=False).update(scope="PRIVATE")


def migrate_scope_to_is_internal(apps, schema_editor):
    TicketComment = apps.get_model("tickets", "TicketComment")
    TicketComment.objects.filter(scope="INTERNAL").update(is_internal=True)
    TicketComment.objects.exclude(scope="INTERNAL").update(is_internal=False)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tickets", "0006_ticketrepost"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticketcomment",
            name="scope",
            field=models.CharField(
                choices=[
                    ("INTERNAL", "Internal"),
                    ("PRIVATE", "Private"),
                    ("COMMUNITY", "Community"),
                ],
                default="PRIVATE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="ticketcomment",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ticketcomment",
            name="hidden_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="hidden_ticket_comments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="ticketcomment",
            name="hidden_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="ticketcomment",
            name="is_official",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            migrate_is_internal_to_scope,
            migrate_scope_to_is_internal,
        ),
        migrations.RemoveField(
            model_name="ticketcomment",
            name="is_internal",
        ),
    ]
