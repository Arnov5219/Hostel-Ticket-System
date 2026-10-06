from django.core.management.base import BaseCommand

from apps.tickets.models import Category, Priority, SLAPolicy, Tag


class Command(BaseCommand):
    help = "Seeds standard categories, default SLA policies, and tags"

    def handle(self, *args, **options):
        # 1. Default SLA Table (Section 3.3)
        # Priority -> [L1, L2, L3, L4 hours]
        sla_table = {
            Priority.URGENT: [2, 2, 4, 4],
            Priority.HIGH: [8, 8, 12, 12],
            Priority.MEDIUM: [24, 24, 24, 24],
            Priority.LOW: [48, 48, 48, 48],
        }

        self.stdout.write("Seeding SLA Policies...")
        for priority, hours_by_level in sla_table.items():
            for level_index, hours in enumerate(hours_by_level, start=1):
                policy, _ = SLAPolicy.objects.update_or_create(
                    priority=priority,
                    level=level_index,
                    defaults={"hours": hours},
                )
                self.stdout.write(f"  {policy}")

        # 2. Standard Categories
        categories_data = [
            ("Electrical", "zap", Priority.HIGH),
            ("Plumbing / Water", "droplet", Priority.HIGH),
            ("Internet / Wi-Fi", "wifi", Priority.HIGH),
            ("Cleaning / Housekeeping", "sparkles", Priority.MEDIUM),
            ("Furniture", "armchair", Priority.LOW),
            ("Mess / Food", "utensils", Priority.HIGH),
            ("Security", "shield-alert", Priority.URGENT),
            ("Maintenance", "wrench", Priority.MEDIUM),
            ("Other", "help-circle", Priority.MEDIUM),
        ]

        self.stdout.write("Seeding Categories...")
        for name, icon, default_prio in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={"icon": icon, "default_priority": default_prio},
            )
            self.stdout.write(f"  Category: {cat.name}")

        # 3. Standard Tags
        tags_data = [
            ("Exam Period", "#F08C00"),
            ("Water Shortage", "#2490EF"),
            ("Recurring Issue", "#E03E3E"),
            ("Pending Vendor", "#6B3FA0"),
        ]

        self.stdout.write("Seeding Tags...")
        for name, color in tags_data:
            t, _ = Tag.objects.get_or_create(name=name, defaults={"color": color})
            self.stdout.write(f"  Tag: {t.name}")

        self.stdout.write(self.style.SUCCESS("SLA policies and categories seeded successfully!"))
