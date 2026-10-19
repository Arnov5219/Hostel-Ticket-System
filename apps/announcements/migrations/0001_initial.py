import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hostels", "0002_remove_room_block_alter_room_unique_together_and_more"),
        ("tickets", "0008_criticalityrule_and_seeds"),
    ]

    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=150)),
                ("body", models.TextField()),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("NOTICE", "Notice"),
                            ("MAINTENANCE", "Maintenance"),
                            ("EMERGENCY", "Emergency"),
                            ("EVENT", "Event"),
                            ("POLICY", "Policy"),
                        ],
                        default="NOTICE",
                        max_length=20,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("INFO", "Info"),
                            ("IMPORTANT", "Important"),
                            ("URGENT", "Urgent"),
                        ],
                        default="INFO",
                        max_length=20,
                    ),
                ),
                ("all_hostels", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("SCHEDULED", "Scheduled"),
                            ("PUBLISHED", "Published"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("is_pinned", models.BooleanField(default=False)),
                ("publish_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "attachment",
                    models.FileField(blank=True, null=True, upload_to="announcements/"),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "hostels",
                    models.ManyToManyField(
                        blank=True, related_name="announcements", to="hostels.hostel"
                    ),
                ),
                (
                    "related_ticket",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="announcements",
                        to="tickets.ticket",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_pinned", "-published_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AnnouncementRead",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("read_at", models.DateTimeField(auto_now_add=True)),
                (
                    "announcement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reads",
                        to="announcements.announcement",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcement_reads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="announcement",
            index=models.Index(
                fields=["status", "published_at"], name="announcemen_status_5cfd59_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="announcement",
            index=models.Index(
                fields=["is_pinned", "published_at"], name="announcemen_is_pinn_aee056_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="announcementread",
            constraint=models.UniqueConstraint(
                fields=("announcement", "user"), name="unique_announcement_user_read"
            ),
        ),
    ]
