import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import (
    ActivityAction,
    Status,
    Ticket,
    TicketActivity,
)
from apps.tickets.services.numbering import generate_ticket_number
from apps.tickets.services.routing import assign_initial


@pytest.mark.django_db
def test_ticket_numbering_sequential():
    num1 = generate_ticket_number()
    TicketFactory(ticket_no=num1)
    num2 = generate_ticket_number()
    assert num1.startswith("HTL-")
    assert num2.startswith("HTL-")
    seq1 = int(num1.split("-")[-1])
    seq2 = int(num2.split("-")[-1])
    assert seq2 == seq1 + 1


@pytest.mark.django_db
def test_routing_assign_initial():
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel)
    category = CategoryFactory()

    ticket = Ticket.objects.create(
        ticket_no=generate_ticket_number(),
        title="Fan regulator broken",
        description="Fan running at top speed constantly",
        category=category,
        priority="HIGH",
        status=Status.OPEN,
        reporter=hosteler,
        hostel=hostel,
    )

    assign_initial(ticket)

    ticket.refresh_from_db()
    assert ticket.assigned_to == caretaker
    assert ticket.current_level == 1
    assert ticket.status == Status.ASSIGNED
    assert ticket.due_at is not None

    # Audit log check
    activity = TicketActivity.objects.filter(ticket=ticket, action=ActivityAction.ASSIGNED).first()
    assert activity is not None


@pytest.mark.django_db
def test_ticket_visible_to():
    hostel_a = HostelFactory()
    hostel_b = HostelFactory()

    hosteler_a = UserFactory(role=Role.HOSTELER, hostel=hostel_a)
    hosteler_b = UserFactory(role=Role.HOSTELER, hostel=hostel_b)
    warden_a = UserFactory(role=Role.WARDEN, hostel=hostel_a)
    admin = UserFactory(role=Role.ADMIN)

    t_a = TicketFactory(hostel=hostel_a, reporter=hosteler_a)
    t_b = TicketFactory(hostel=hostel_b, reporter=hosteler_b)

    # Hosteler only sees their own
    assert list(Ticket.objects.visible_to(hosteler_a)) == [t_a]

    # Warden of hostel A only sees hostel A tickets
    assert list(Ticket.objects.visible_to(warden_a)) == [t_a]

    # Admin sees all tickets
    admin_tickets = list(Ticket.objects.visible_to(admin))
    assert t_a in admin_tickets
    assert t_b in admin_tickets


@pytest.mark.django_db
def test_raise_ticket_and_comment_flow(client):
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="caretaker_pwd")
    hostel.responsible_staff = caretaker
    hostel.save()
    student = UserFactory(
        role=Role.HOSTELER,
        hostel=hostel,
        password="student_pwd",
    )
    category = CategoryFactory()

    # Student logs in
    client.login(username=student.login_id, password="student_pwd")

    # Raise ticket
    response = client.post(
        reverse("tickets:create"),
        {
            "category": category.id,
            "room_number": "201",
            "title": "Water heater not functioning",
            "description": "Geyser does not heat water in room 201",
            "priority": "MEDIUM",
            "hostel": hostel.id,
        },
    )
    assert response.status_code == 302
    ticket = Ticket.objects.filter(reporter=student).first()
    assert ticket is not None
    assert ticket.assigned_to == caretaker
    assert ticket.status == Status.ASSIGNED

    # Direct attempt to post comment is blocked with 403 Forbidden
    res = client.post(
        reverse("tickets:comment", kwargs={"ticket_no": ticket.ticket_no}),
        {"body": "Any update on when this will be checked?"},
    )
    assert res.status_code == 403
    assert ticket.comments.count() == 0

    # Caretaker attempt to post comment is also blocked
    client.logout()
    client.login(username=caretaker.login_id, password="caretaker_pwd")
    res = client.post(
        reverse("tickets:comment", kwargs={"ticket_no": ticket.ticket_no}),
        {"body": "Vendor called, heating element out of stock.", "is_internal": True},
    )
    assert res.status_code == 403
    assert ticket.comments.count() == 0

    # Student logs back in and checks detail page - comment form and comment tabs must be absent
    client.logout()
    client.login(username=student.login_id, password="student_pwd")
    detail_res = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
    assert detail_res.status_code == 200
    assert "Activity Timeline" in detail_res.content.decode()
    assert "Send reply" not in detail_res.content.decode()
    assert "Add a response" not in detail_res.content.decode()
