from django.db import migrations, models


def seed_category_allow_community(apps, schema_editor):
    Category = apps.get_model("tickets", "Category")
    Category.objects.filter(name__in=["Security", "Other"]).update(allow_community=False)


def unseed_category_allow_community(apps, schema_editor):
    Category = apps.get_model("tickets", "Category")
    Category.objects.filter(name__in=["Security", "Other"]).update(allow_community=True)


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0003_remove_ticket_room"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="allow_community",
            field=models.BooleanField(
                default=True,
                help_text="Allow sharing tickets in this category to community feed",
            ),
        ),
        migrations.RunPython(
            seed_category_allow_community,
            unseed_category_allow_community,
        ),
    ]
