from django.db import migrations


def seed_sla_and_categories(apps, schema_editor):
    SLAPolicy = apps.get_model("tickets", "SLAPolicy")
    Category = apps.get_model("tickets", "Category")
    Tag = apps.get_model("tickets", "Tag")

    sla_table = {
        "URGENT": [2, 2, 4, 4],
        "HIGH": [8, 8, 12, 12],
        "MEDIUM": [24, 24, 24, 24],
        "LOW": [48, 48, 48, 48],
    }

    for priority, hours_by_level in sla_table.items():
        for level_index, hours in enumerate(hours_by_level, start=1):
            SLAPolicy.objects.update_or_create(
                priority=priority,
                level=level_index,
                defaults={"hours": hours},
            )

    categories_data = [
        ("Electrical", "zap", "HIGH"),
        ("Plumbing / Water", "droplet", "HIGH"),
        ("Internet / Wi-Fi", "wifi", "HIGH"),
        ("Cleaning / Housekeeping", "sparkles", "MEDIUM"),
        ("Furniture", "armchair", "LOW"),
        ("Mess / Food", "utensils", "HIGH"),
        ("Security", "shield-alert", "URGENT"),
        ("Maintenance", "wrench", "MEDIUM"),
        ("Other", "help-circle", "MEDIUM"),
    ]

    for name, icon, default_prio in categories_data:
        Category.objects.get_or_create(
            name=name,
            defaults={"icon": icon, "default_priority": default_prio, "is_active": True},
        )

    tags_data = [
        ("Exam Period", "#F08C00"),
        ("Water Shortage", "#2490EF"),
        ("Recurring Issue", "#E03E3E"),
        ("Pending Vendor", "#6B3FA0"),
    ]

    for name, color in tags_data:
        Tag.objects.get_or_create(name=name, defaults={"color": color})


def remove_sla_and_categories(apps, schema_editor):
    SLAPolicy = apps.get_model("tickets", "SLAPolicy")
    Category = apps.get_model("tickets", "Category")
    Tag = apps.get_model("tickets", "Tag")

    SLAPolicy.objects.all().delete()
    Category.objects.all().delete()
    Tag.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_sla_and_categories, remove_sla_and_categories),
    ]
