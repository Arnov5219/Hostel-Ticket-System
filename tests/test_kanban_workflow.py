from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.tickets.factories import TicketFactory
from apps.tickets.models import Status
from apps.tickets.services.status import (
    auto_close_resolved_tickets,
    change_status,
)


@pytest.mark.django_db
def test_status_workflow_transitions():
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    ticket = TicketFactory(
        hostel=hostel, reporter=student, assigned_to=caretaker, status=Status.OPEN
    )

    # 1. Illegal move: OPEN -> CLOSED directly by caretaker
    with pytest.raises(ValidationError):
        change_status(ticket, Status.CLOSED, actor=caretaker)

    # 2. Legal move: OPEN -> ASSIGNED
    change_status(ticket, Status.ASSIGNED, actor=caretaker)
    ticket.refresh_from_db()
    assert ticket.status == Status.ASSIGNED

    # 3. ASSIGNED -> IN_PROGRESS
    change_status(ticket, Status.IN_PROGRESS, actor=caretaker)
    ticket.refresh_from_db()
    assert ticket.status == Status.IN_PROGRESS

    # 4. IN_PROGRESS -> RESOLVED
    change_status(ticket, Status.RESOLVED, actor=caretaker, note="Replaced switchboard")
    ticket.refresh_from_db()
    assert ticket.status == Status.RESOLVED
    assert ticket.resolved_at is not None

    # 5. Hosteler confirms and closes: RESOLVED -> CLOSED
    change_status(ticket, Status.CLOSED, actor=student)
    ticket.refresh_from_db()
    assert ticket.status == Status.CLOSED
    assert ticket.closed_at is not None


@pytest.mark.django_db
def test_kanban_move_endpoint(client):
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="password123")
    ticket = TicketFactory(hostel=hostel, assigned_to=caretaker, status=Status.ASSIGNED)

    client.login(username=caretaker.login_id, password="password123")

    # Legal move on Kanban: ASSIGNED -> IN_PROGRESS
    response = client.post(
        reverse("tickets:move", kwargs={"ticket_no": ticket.ticket_no}),
        {"status": "IN_PROGRESS"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    ticket.refresh_from_db()
    assert ticket.status == Status.IN_PROGRESS

    # Illegal move: IN_PROGRESS -> OPEN
    bad_response = client.post(
        reverse("tickets:move", kwargs={"ticket_no": ticket.ticket_no}),
        {"status": "OPEN"},
    )
    assert bad_response.status_code == 400
    assert "error" in bad_response.json()


@pytest.mark.django_db
def test_kanban_access_permissions(client):
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="staff_pwd")
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="student_pwd")

    # Caretaker can access Kanban board
    client.login(username=caretaker.login_id, password="staff_pwd")
    res1 = client.get(reverse("tickets:kanban"))
    assert res1.status_code == 200

    # Hosteler gets 403 on Kanban board
    client.logout()
    client.login(username=hosteler.login_id, password="student_pwd")
    res2 = client.get(reverse("tickets:kanban"))
    assert res2.status_code == 403


@pytest.mark.django_db
def test_auto_close_tickets():
    now = timezone.now()
    old_resolved = TicketFactory(
        status=Status.RESOLVED,
        resolved_at=now - timedelta(hours=75),
    )
    recent_resolved = TicketFactory(
        status=Status.RESOLVED,
        resolved_at=now - timedelta(hours=10),
    )

    closed_count = auto_close_resolved_tickets(hours_threshold=72)
    assert closed_count == 1

    old_resolved.refresh_from_db()
    assert old_resolved.status == Status.CLOSED
    assert old_resolved.closed_at is not None

    recent_resolved.refresh_from_db()
    assert recent_resolved.status == Status.RESOLVED
