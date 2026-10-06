from datetime import datetime

from django.db import transaction

from apps.tickets.models import Ticket


def generate_ticket_number() -> str:
    """Generates unique race-safe ticket number: HTL-YYYY-00001."""
    year = datetime.now().year
    prefix = f"HTL-{year}-"

    with transaction.atomic():
        last_ticket = (
            Ticket.objects.select_for_update()
            .filter(ticket_no__startswith=prefix)
            .order_by("-ticket_no")
            .first()
        )
        if last_ticket:
            last_seq = int(last_ticket.ticket_no.split("-")[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1

        return f"{prefix}{new_seq:05d}"
