import csv
import os
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import AllowedRollNumber
from apps.hostels.models import Hostel


class Command(BaseCommand):
    help = "Imports allowed roll numbers from a CSV file (columns: roll_no, name [optional], hostel_code [optional])"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file containing roll numbers")

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        if not os.path.exists(csv_path):
            raise CommandError(f"File not found: {csv_path}")

        created_count = 0
        updated_count = 0

        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # If CSV has no header, fall back to plain reading
            if "roll_no" not in (reader.fieldnames or []):
                f.seek(0)
                raw_reader = csv.reader(f)
                for row in raw_reader:
                    if not row:
                        continue
                    roll_no = row[0].strip().upper()
                    if not roll_no:
                        continue
                    obj, created = AllowedRollNumber.objects.update_or_create(
                        roll_no=roll_no,
                        defaults={},
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            else:
                for row in reader:
                    roll_no = (row.get("roll_no") or "").strip().upper()
                    if not roll_no:
                        continue
                    name = (row.get("name") or "").strip()
                    hostel_code = (row.get("hostel_code") or "").strip().upper()
                    hostel = None
                    if hostel_code:
                        hostel = Hostel.objects.filter(code__iexact=hostel_code).first()

                    defaults = {}
                    if name:
                        defaults["name"] = name
                    if hostel:
                        defaults["hostel"] = hostel

                    obj, created = AllowedRollNumber.objects.update_or_create(
                        roll_no=roll_no,
                        defaults=defaults,
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported roll numbers: {created_count} created, {updated_count} existing."
            )
        )
