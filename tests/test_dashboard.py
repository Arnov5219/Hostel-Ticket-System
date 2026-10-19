import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.dashboard.selectors import (
    get_escalation_breakdown,
    get_hosteler_kpis,
    get_kpis,
    get_resolution_time_data,
)
from apps.hostels.factories import HostelFactory
from apps.tickets.factories import CategoryFactory, TicketFactory
from apps.tickets.models import Status


@pytest.mark.django_db
def test_dashboard_access_for_hosteler(client):
    hostel = HostelFactory()
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    other_student = UserFactory(role=Role.HOSTELER, hostel=hostel)

    # Student's ticket
    my_ticket = TicketFactory(
        hostel=hostel, reporter=student, status=Status.OPEN, title="My leaky tap"
    )
    # Other student's ticket
    TicketFactory(
        hostel=hostel, reporter=other_student, status=Status.OPEN, title="Other room light"
    )

    client.force_login(student)
    response = client.get(reverse("dashboard:index"))

    assert response.status_code == 200
    assert "dashboard/hosteler.html" in [t.name for t in response.templates]
    assert response.context["kpis"]["my_open"] == 1
    assert my_ticket in response.context["recent_tickets"]
    assert len(response.context["recent_tickets"]) == 1

    content = response.content.decode("utf-8")
    assert "recent-filter-chips-row" in content
    assert "recent-filter-btn" in content
    assert "recent-filter-count" in content
    assert "All" in content
    assert "Open" in content
    assert "In progress" in content
    assert "Resolved" in content


@pytest.mark.django_db
def test_dashboard_access_for_staff(client):
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)

    TicketFactory(
        hostel=hostel,
        reporter=student,
        assigned_to=caretaker,
        status=Status.IN_PROGRESS,
    )
    TicketFactory(
        hostel=hostel,
        reporter=student,
        assigned_to=caretaker,
        status=Status.RESOLVED,
        resolved_at=timezone.now(),
    )

    client.force_login(caretaker)
    response = client.get(reverse("dashboard:index"))

    assert response.status_code == 200
    assert "dashboard/staff.html" in [t.name for t in response.templates]
    assert response.context["kpis"]["open_count"] == 1
    assert response.context["kpis"]["resolved_count"] == 1
    assert "escalations" in response.context


@pytest.mark.django_db
def test_dashboard_json_apis(client):
    hostel = HostelFactory()
    admin = UserFactory(role=Role.ADMIN)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    category = CategoryFactory(name="Plumbing")

    TicketFactory(
        hostel=hostel,
        reporter=student,
        category=category,
        status=Status.OPEN,
    )

    client.force_login(admin)

    # 1. Summary API
    res = client.get(reverse("dashboard:api_summary"))
    assert res.status_code == 200
    data = res.json()
    assert "total_month" in data
    assert "open_count" in data

    # 2. Category API
    res = client.get(reverse("dashboard:api_by_category"))
    assert res.status_code == 200
    data = res.json()
    assert "labels" in data
    assert "Plumbing" in data["labels"]

    # 3. Trend API
    res = client.get(reverse("dashboard:api_trend"))
    assert res.status_code == 200
    data = res.json()
    assert "labels" in data
    assert "created" in data
    assert len(data["labels"]) == 6

    # 4. Resolution Time API
    res = client.get(reverse("dashboard:api_resolution_time"))
    assert res.status_code == 200
    data = res.json()
    assert "labels" in data
    assert "data" in data


@pytest.mark.django_db
def test_dashboard_selectors():
    hostel = HostelFactory(name="Tagore Bhavan")
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)

    TicketFactory(
        hostel=hostel,
        reporter=student,
        assigned_to=caretaker,
        status=Status.RESOLVED,
        current_level=1,
        resolved_at=timezone.now(),
    )
    TicketFactory(
        hostel=hostel,
        reporter=student,
        assigned_to=caretaker,
        status=Status.OPEN,
        current_level=2,
    )

    kpis = get_kpis(caretaker)
    assert kpis["open_count"] == 1
    assert kpis["resolved_count"] == 1

    h_kpis = get_hosteler_kpis(student)
    assert h_kpis["my_open"] == 1
    assert h_kpis["my_resolved"] == 1
    assert h_kpis["my_closed"] == 0

    esc = get_escalation_breakdown(caretaker)
    assert esc["L2"] == 1
    assert esc["L1"] == 0  # resolved ticket is not in open/in_progress count

    res_time = get_resolution_time_data(caretaker)
    assert "Tagore Bhavan" in res_time["labels"]
