from django.core.management.base import BaseCommand, CommandError

from apps.tickets.models import TicketComment


class Command(BaseCommand):
    help = "Operator break-glass command to hide or unhide a community comment without UI access."

    def add_arguments(self, parser):
        parser.add_argument("comment_id", type=int, help="ID of the TicketComment to moderate")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--hide", action="store_true", help="Hide the comment")
        group.add_argument("--unhide", action="store_true", help="Unhide the comment")
        parser.add_argument("--reason", type=str, default="Moderated by system administrator", help="Reason for hiding")

    def handle(self, *args, **options):
        comment_id = options["comment_id"]
        try:
            comment = TicketComment.objects.get(id=comment_id)
        except TicketComment.DoesNotExist:
            raise CommandError(f"Comment with ID {comment_id} does not exist.")

        if options["hide"]:
            comment.is_hidden = True
            comment.hidden_reason = options["reason"]
            comment.save(update_fields=["is_hidden", "hidden_reason"])
            self.stdout.write(self.style.SUCCESS(f"Comment {comment_id} has been hidden: {options['reason']}"))
        elif options["unhide"]:
            comment.is_hidden = False
            comment.hidden_reason = ""
            comment.save(update_fields=["is_hidden", "hidden_reason"])
            self.stdout.write(self.style.SUCCESS(f"Comment {comment_id} has been unhidden."))
