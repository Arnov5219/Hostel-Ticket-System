from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.notifications.models import Notification
from apps.tickets.factories import TicketFactory
from apps.tickets.models import Status
from apps.tickets.services.escalation import check_overdue, escalate


@pytest.mark.django_db
def test_manual_escalate_hierarchy():
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, escalation_level=1)
    warden = UserFactory(role=Role.WARDEN, hostel=hostel, escalation_level=2)
    chief = UserFactory(role=Role.CHIEF_WARDEN, escalation_level=3)
    admin = UserFactory(role=Role.ADMIN, escalation_level=4)

    ticket = TicketFactory(
        hostel=hostel,
        assigned_to=caretaker,
        current_level=1,
        status=Status.IN_PROGRESS,
    )

    # 1. Escalate L1 -> L2
    escalate(ticket, actor=caretaker, reason="Needs warden approval for budget")
    ticket.refresh_from_db()
    assert ticket.current_level == 2
    assert ticket.assigned_to == warden
    assert Notification.objects.filter(recipient=warden, ticket=ticket).exists()

    # 2. Escalate L2 -> L3
    escalate(ticket, actor=warden, reason="Hostel-wide issue")
    ticket.refresh_from_db()
    assert ticket.current_level == 3
    assert ticket.assigned_to == chief
    assert Notification.objects.filter(recipient=chief, ticket=ticket).exists()

    # 3. Escalate L3 -> L4
    escalate(ticket, actor=chief, reason="Dean-level intervention")
    ticket.refresh_from_db()
    assert ticket.current_level == 4
    assert ticket.assigned_to == admin
    assert Notification.objects.filter(recipient=admin, ticket=ticket).exists()


@pytest.mark.django_db
def test_automated_sla_check_overdue():
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, escalation_level=1)
    warden = UserFactory(role=Role.WARDEN, hostel=hostel, escalation_level=2)
    admin = UserFactory(role=Role.ADMIN, escalation_level=4)

    now = timezone.now()

    # Ticket 1: L1 and overdue -> should escalate to L2
    t1 = TicketFactory(
        hostel=hostel,
        assigned_to=caretaker,
        current_level=1,
        status=Status.ASSIGNED,
        due_at=now - timedelta(hours=2),
    )

    # Ticket 2: L4 and overdue -> should be flagged is_overdue=True (Critical Overdue)
    t2 = TicketFactory(
        hostel=hostel,
        assigned_to=admin,
        current_level=4,
        status=Status.IN_PROGRESS,
        due_at=now - timedelta(hours=1),
        is_overdue=False,
    )

    # Ticket 3: Resolved ticket past deadline -> should NOT escalate
    t3 = TicketFactory(
        hostel=hostel,
        assigned_to=caretaker,
        current_level=1,
        status=Status.RESOLVED,
        due_at=now - timedelta(hours=5),
    )

    count = check_overdue()
    assert count == 2

    t1.refresh_from_db()
    assert t1.current_level == 2
    assert t1.assigned_to == warden

    t2.refresh_from_db()
    assert t2.current_level == 4
    assert t2.is_overdue is True

    t3.refresh_from_db()
    assert t3.current_level == 1
    assert t3.status == Status.RESOLVED


@pytest.mark.django_db
def test_manual_escalate_view(client):
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="staff_password")
    warden = UserFactory(role=Role.WARDEN, hostel=hostel)
    ticket = TicketFactory(hostel=hostel, assigned_to=caretaker, current_level=1)

    client.login(username=caretaker.login_id, password="staff_password")
    response = client.post(
        reverse("tickets:escalate", kwargs={"ticket_no": ticket.ticket_no}),
        {"reason": "Cannot be fixed locally by caretaker"},
    )
    assert response.status_code == 302
    ticket.refresh_from_db()
    assert ticket.current_level == 2
    assert ticket.assigned_to == warden
