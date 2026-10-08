from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.announcements.models import Announcement, AnnouncementStatus
from apps.announcements.services import publish


class Command(BaseCommand):
    help = "Publishes scheduled announcements that have reached their publish_at time."

    def handle(self, *args, **options):
        now = timezone.now()
        scheduled_announcements = Announcement.objects.filter(
            status=AnnouncementStatus.SCHEDULED,
            publish_at__lte=now,
        )

        count = 0
        for ann in scheduled_announcements:
            publish(ann, actor=ann.author)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully published {count} scheduled announcement(s).")
        )
