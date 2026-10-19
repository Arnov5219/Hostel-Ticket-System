from django.db import migrations, models


def seed_criticality_rules(apps, schema_editor):
    CriticalityRule = apps.get_model("tickets", "CriticalityRule")
    CriticalityRule.objects.update_or_create(
        min_reposts=3,
        defaults={"bump_levels": 1, "force_priority": None, "notify_level": None},
    )
    CriticalityRule.objects.update_or_create(
        min_reposts=6,
        defaults={"bump_levels": 2, "force_priority": None, "notify_level": None},
    )
    CriticalityRule.objects.update_or_create(
        min_reposts=10,
        defaults={"bump_levels": 0, "force_priority": "URGENT", "notify_level": 2},
    )


def unseed_criticality_rules(apps, schema_editor):
    CriticalityRule = apps.get_model("tickets", "CriticalityRule")
    CriticalityRule.objects.filter(min_reposts__in=[3, 6, 10]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0007_ticketcomment_scope"),
    ]

    operations = [
        migrations.CreateModel(
            name="CriticalityRule",
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
                ("min_reposts", models.PositiveIntegerField(unique=True)),
                ("bump_levels", models.PositiveSmallIntegerField(default=1)),
                (
                    "force_priority",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("URGENT", "Urgent"),
                            ("HIGH", "High"),
                            ("MEDIUM", "Medium"),
                            ("LOW", "Low"),
                        ],
                        max_length=10,
                        null=True,
                    ),
                ),
                ("notify_level", models.PositiveSmallIntegerField(blank=True, null=True)),
            ],
            options={
                "ordering": ["min_reposts"],
            },
        ),
        migrations.RunPython(
            seed_criticality_rules,
            unseed_criticality_rules,
        ),
    ]
