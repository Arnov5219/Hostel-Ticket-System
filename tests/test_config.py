import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import BlockFactory, HostelFactory
from apps.hostels.models import Hostel, Room
from apps.tickets.models import Category, Priority, RoutingRule, SLAPolicy


@pytest.mark.django_db
def test_sla_policy_seeded():
    # Verify default SLA values from Section 3.3
    urgent_l1 = SLAPolicy.objects.get(priority=Priority.URGENT, level=1)
    assert urgent_l1.hours == 2

    high_l3 = SLAPolicy.objects.get(priority=Priority.HIGH, level=3)
    assert high_l3.hours == 12

    medium_l4 = SLAPolicy.objects.get(priority=Priority.MEDIUM, level=4)
    assert medium_l4.hours == 24


@pytest.mark.django_db
def test_manage_hostels_view(client):
    admin = UserFactory(role=Role.ADMIN, password="admin_password")
    client.login(username=admin.login_id, password="admin_password")

    # Access page
    response = client.get(reverse("hostels:manage_hostels"))
    assert response.status_code == 200

    # Create new hostel
    post_res = client.post(
        reverse("hostels:manage_hostels"),
        {
            "action": "create",
            "name": "Girls Hostel C",
            "code": "GIRLS_C",
            "gender_type": "GIRLS",
            "address": "Sector 4",
            "is_active": True,
        },
    )
    assert post_res.status_code == 302
    assert Hostel.objects.filter(code="GIRLS_C").exists()


@pytest.mark.django_db
def test_manage_rooms_view(client):
    admin = UserFactory(role=Role.ADMIN, password="admin_password")
    client.login(username=admin.login_id, password="admin_password")

    block = BlockFactory()
    response = client.post(
        reverse("hostels:manage_rooms"),
        {
            "block": block.id,
            "room_number": "305",
            "floor": 3,
            "capacity": 3,
        },
    )
    assert response.status_code == 302
    assert Room.objects.filter(block=block, room_number="305").exists()


@pytest.mark.django_db
def test_manage_routing_rules(client):
    admin = UserFactory(role=Role.ADMIN, password="admin_password")
    caretaker = UserFactory(role=Role.CARETAKER)
    client.login(username=admin.login_id, password="admin_password")

    hostel = HostelFactory()
    category = Category.objects.first()

    # Add routing rule
    response = client.post(
        reverse("tickets:manage_routing"),
        {
            "action": "add_rule",
            "hostel": hostel.id,
            "category": category.id if category else "",
            "level": 1,
            "assignee": caretaker.id,
        },
    )
    assert response.status_code == 302
    assert RoutingRule.objects.filter(hostel=hostel, assignee=caretaker).exists()


@pytest.mark.django_db
def test_unauthorized_hosteler_access_denied(client):
    hosteler = UserFactory(role=Role.HOSTELER, password="student_password")
    client.login(username=hosteler.login_id, password="student_password")

    res1 = client.get(reverse("hostels:manage_hostels"))
    assert res1.status_code == 403

    res2 = client.get(reverse("tickets:manage_routing"))
    assert res2.status_code == 403
