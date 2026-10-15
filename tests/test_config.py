import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.hostels.models import Hostel
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
def test_manage_staff_and_responsibility_views(client):
    admin = UserFactory(role=Role.ADMIN, password="admin_password")
    client.login(username=admin.login_id, password="admin_password")

    staff_res = client.get(reverse("hostels:manage_staff"))
    assert staff_res.status_code == 200

    resp_res = client.get(reverse("hostels:manage_responsibility"))
    assert resp_res.status_code == 200


@pytest.mark.django_db
def test_manage_settings_view(client):
    admin = UserFactory(role=Role.ADMIN, password="admin_password")
    client.login(username=admin.login_id, password="admin_password")

    response = client.get(reverse("tickets:manage_settings"))
    assert response.status_code == 200

    # Ensure /manage/routing/ is 404
    routing_res = client.get("/manage/routing/")
    assert routing_res.status_code == 404


@pytest.mark.django_db
def test_unauthorized_hosteler_access_denied(client):
    hosteler = UserFactory(role=Role.HOSTELER, password="student_password")
    client.login(username=hosteler.login_id, password="student_password")

    res1 = client.get(reverse("hostels:manage_hostels"))
    assert res1.status_code == 403

    res2 = client.get(reverse("tickets:manage_settings"))
    assert res2.status_code == 403

