import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role, User
from apps.hostels.factories import HostelFactory
from apps.hostels.models import GenderType, Hostel
from apps.hostels.services import (
    assign_staff_to_hostel,
    change_hostel_responsible_staff,
    create_hostel,
    deactivate_hostel,
    deactivate_staff,
    update_hostel,
)
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import Category, Priority, Status, Ticket
from apps.tickets.services.routing import assign_initial


@pytest.mark.django_db
def test_create_hostel_validation():
    caretaker = UserFactory(role=Role.CARETAKER, escalation_level=1)
    warden = UserFactory(role=Role.WARDEN, escalation_level=2)

    # Valid creation
    hostel = create_hostel(
        name="Boys Hostel A",
        code="BH-A",
        gender_type=GenderType.BOYS,
        address="North Campus",
        responsible_staff=caretaker,
    )
    assert hostel.pk is not None
    assert hostel.responsible_staff == caretaker
    assert caretaker.hostel == hostel

    # Duplicate code rejection
    with pytest.raises(ValidationError, match="already exists"):
        create_hostel(
            name="Boys Hostel Duplicate",
            code="bh-a",
            gender_type=GenderType.BOYS,
        )

    # Cannot assign Level 2 staff as Level 1 responsible staff
    with pytest.raises(ValidationError, match="Level 1"):
        create_hostel(
            name="Hostel with Warden as L1",
            code="HW-1",
            gender_type=GenderType.BOYS,
            responsible_staff=warden,
        )

    # Cannot assign inactive staff
    inactive_caretaker = UserFactory(role=Role.CARETAKER, is_active=False)
    with pytest.raises(ValidationError, match="inactive"):
        create_hostel(
            name="Hostel with Inactive Caretaker",
            code="HIC-1",
            gender_type=GenderType.BOYS,
            responsible_staff=inactive_caretaker,
        )


@pytest.mark.django_db
def test_update_hostel():
    caretaker1 = UserFactory(role=Role.CARETAKER)
    caretaker2 = UserFactory(role=Role.CARETAKER)
    hostel = HostelFactory(code="BH-B", responsible_staff=caretaker1)

    update_hostel(hostel, name="Boys Hostel B (Updated)", responsible_staff=caretaker2)
    hostel.refresh_from_db()
    assert hostel.name == "Boys Hostel B (Updated)"
    assert hostel.responsible_staff == caretaker2


@pytest.mark.django_db
def test_deactivate_hostel_safeguard():
    hostel = HostelFactory(is_active=True)
    ticket = TicketFactory(hostel=hostel, status=Status.IN_PROGRESS)

    _, active_count = deactivate_hostel(hostel)
    hostel.refresh_from_db()
    assert hostel.is_active is False
    assert active_count == 1
    # Historical ticket remains intact
    assert Ticket.objects.filter(hostel=hostel).exists()


@pytest.mark.django_db
def test_staff_assignment_and_responsibility():
    hostel_a = HostelFactory(name="Hostel Alpha", code="HA")
    hostel_b = HostelFactory(name="Hostel Beta", code="HB")
    caretaker1 = UserFactory(role=Role.CARETAKER, hostel=hostel_a)
    caretaker2 = UserFactory(role=Role.CARETAKER, hostel=hostel_b)

    # Assign staff to hostel
    assign_staff_to_hostel(caretaker1, hostel_b)
    caretaker1.refresh_from_db()
    assert caretaker1.hostel == hostel_b

    # Change responsible staff
    change_hostel_responsible_staff(hostel_a, caretaker2)
    hostel_a.refresh_from_db()
    assert hostel_a.responsible_staff == caretaker2


@pytest.mark.django_db
def test_deactivate_staff_safeguards():
    hostel = HostelFactory()
    caretaker_active = UserFactory(role=Role.CARETAKER)
    caretaker_replacement = UserFactory(role=Role.CARETAKER)

    hostel.responsible_staff = caretaker_active
    hostel.save()

    # Deactivating without replacement should raise ValidationError
    with pytest.raises(ValidationError, match="responsible Level 1 staff"):
        deactivate_staff(caretaker_active)

    # Deactivating with replacement succeeds
    deactivate_staff(caretaker_active, replacement_staff=caretaker_replacement)
    caretaker_active.refresh_from_db()
    hostel.refresh_from_db()

    assert caretaker_active.is_active is False
    assert hostel.responsible_staff == caretaker_replacement


@pytest.mark.django_db
def test_ticket_routing_by_hostel_regardless_of_category():
    """
    Core principle:
    The hostel determines who receives a Level 1 ticket.
    The category only describes what the problem is.
    """
    caretaker_a = UserFactory(role=Role.CARETAKER, full_name="Mukesh Kumar")
    caretaker_b = UserFactory(role=Role.CARETAKER, full_name="Anita Devi")

    hostel_a = HostelFactory(name="Boys Hostel A", code="BHA", responsible_staff=caretaker_a)
    hostel_b = HostelFactory(name="Girls Hostel B", code="GHB", responsible_staff=caretaker_b)

    student_a = UserFactory(role=Role.HOSTELER, hostel=hostel_a)
    student_b = UserFactory(role=Role.HOSTELER, hostel=hostel_b)

    cat_electrical = CategoryFactory(name="Electrical")
    cat_plumbing = CategoryFactory(name="Plumbing")
    cat_wifi = CategoryFactory(name="Wi-Fi & LAN")

    # Ticket 1: Electrical issue in Hostel A -> routes to Mukesh Kumar
    t1 = Ticket.objects.create(
        ticket_no="HTL-2026-90001",
        title="Fan regulator broken",
        description="Fan stuck on speed 5",
        category=cat_electrical,
        hostel=hostel_a,
        reporter=student_a,
    )
    assign_initial(t1)
    assert t1.assigned_to == caretaker_a
    assert t1.current_level == 1
    assert t1.status == Status.ASSIGNED

    # Ticket 2: Plumbing issue in Hostel A -> also routes to Mukesh Kumar (not category based!)
    t2 = Ticket.objects.create(
        ticket_no="HTL-2026-90002",
        title="Tap leaking",
        description="Washbasin tap dripping",
        category=cat_plumbing,
        hostel=hostel_a,
        reporter=student_a,
    )
    assign_initial(t2)
    assert t2.assigned_to == caretaker_a

    # Ticket 3: Wi-Fi issue in Hostel B -> routes to Anita Devi
    t3 = Ticket.objects.create(
        ticket_no="HTL-2026-90003",
        title="No signal",
        description="Wi-Fi disconnected",
        category=cat_wifi,
        hostel=hostel_b,
        reporter=student_b,
    )
    assign_initial(t3)
    assert t3.assigned_to == caretaker_b


@pytest.mark.django_db
def test_assignment_change_behavior_on_tickets():
    """
    Section 16:
    Existing tickets remain with current assignee unless explicitly reassigned.
    New tickets created after the assignment change route to the new responsible staff member.
    """
    caretaker_old = UserFactory(role=Role.CARETAKER, full_name="Mukesh Kumar")
    caretaker_new = UserFactory(role=Role.CARETAKER, full_name="Suresh Kumar")

    hostel = HostelFactory(name="Boys Hostel A", responsible_staff=caretaker_old)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    cat = CategoryFactory()

    # Create ticket before assignment change
    t_old = Ticket.objects.create(
        ticket_no="HTL-2026-91001",
        title="Old issue",
        description="Details",
        category=cat,
        hostel=hostel,
        reporter=student,
    )
    assign_initial(t_old)
    assert t_old.assigned_to == caretaker_old

    # Admin changes responsible staff
    change_hostel_responsible_staff(hostel, caretaker_new)

    # Old ticket still belongs to old caretaker
    t_old.refresh_from_db()
    assert t_old.assigned_to == caretaker_old

    # New ticket routes to new caretaker
    t_new = Ticket.objects.create(
        ticket_no="HTL-2026-91002",
        title="New issue",
        description="Details",
        category=cat,
        hostel=hostel,
        reporter=student,
    )
    assign_initial(t_new)
    assert t_new.assigned_to == caretaker_new


@pytest.mark.django_db
def test_inactive_hostel_cannot_receive_tickets():
    caretaker = UserFactory(role=Role.CARETAKER)
    hostel = HostelFactory(is_active=False, responsible_staff=caretaker)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    cat = CategoryFactory()

    t = Ticket(
        ticket_no="HTL-2026-92001",
        title="Inactive hostel issue",
        description="Details",
        category=cat,
        hostel=hostel,
        reporter=student,
    )
    with pytest.raises(ValidationError, match="inactive hostel"):
        assign_initial(t)


@pytest.mark.django_db
def test_admin_staff_management_endpoints(client):
    admin = UserFactory(role=Role.ADMIN, password="admin_password")
    caretaker = UserFactory(role=Role.CARETAKER)
    hostel = HostelFactory()

    client.login(username=admin.login_id, password="admin_password")

    # Assign staff to hostel POST
    res = client.post(
        reverse("hostels:assign_staff_hostel", kwargs={"user_id": caretaker.id}),
        {"hostel_id": hostel.id},
    )
    assert res.status_code == 302
    caretaker.refresh_from_db()
    assert caretaker.hostel == hostel

    # Change responsible staff POST
    res2 = client.post(
        reverse("hostels:change_responsible_staff", kwargs={"hostel_id": hostel.id}),
        {"responsible_staff": caretaker.id},
    )
    assert res2.status_code == 302
    hostel.refresh_from_db()
    assert hostel.responsible_staff == caretaker
