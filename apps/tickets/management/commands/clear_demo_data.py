import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import ResidenceHistory, Role, User
from apps.announcements.models import Announcement, AnnouncementRead
from apps.notifications.models import Notification
from apps.tickets.models import (
    Ticket,
    TicketActivity,
    TicketAttachment,
    TicketComment,
)


class Command(BaseCommand):
    help = (
        "Removes all demo/fake tickets, comments, announcements, notifications, "
        "and student accounts while preserving hostel structure and staff/admin."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-students",
            action="store_true",
            help="Keep student accounts and only remove tickets, announcements, and notifications.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Cleaning demo/fake data...")

        with transaction.atomic():
            # 1. Delete all attachments & tickets (cascades comments, activities)
            attachment_count = TicketAttachment.objects.count()
            TicketAttachment.objects.all().delete()

            comment_count = TicketComment.objects.count()
            TicketComment.objects.all().delete()

            activity_count = TicketActivity.objects.count()
            TicketActivity.objects.all().delete()

            ticket_count = Ticket.all_objects.count()
            Ticket.all_objects.all().delete()

            # 2. Delete announcements & reads
            ann_read_count = AnnouncementRead.objects.count()
            AnnouncementRead.objects.all().delete()

            ann_count = Announcement.objects.count()
            Announcement.objects.all().delete()

            # 3. Delete notifications
            notif_count = Notification.objects.count()
            Notification.objects.all().delete()

            # 4. Delete student accounts if not kept
            student_count = 0
            if not options["keep_students"]:
                ResidenceHistory.objects.all().delete()
                students = User.objects.filter(role=Role.HOSTELER)
                student_count = students.count()
                students.delete()

        # Clean media attachments directory
        media_attachments = Path(settings.MEDIA_ROOT) / "attachments"
        if media_attachments.exists():
            shutil.rmtree(media_attachments, ignore_errors=True)
            media_attachments.mkdir(parents=True, exist_ok=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully removed:\n"
                f"  - {ticket_count} tickets\n"
                f"  - {comment_count} ticket comments\n"
                f"  - {activity_count} ticket activities\n"
                f"  - {attachment_count} attachments\n"
                f"  - {ann_count} announcements ({ann_read_count} read markers)\n"
                f"  - {notif_count} notifications\n"
                f"  - {student_count} student accounts\n\n"
                f"Preserved:\n"
                f"  - All 12 Hostels & 1,440 Rooms\n"
                f"  - All Staff & Admin accounts\n"
                f"  - Categories, Tags, Routing Rules, SLAs"
            )
        )
