import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory
from apps.tickets.factories import TicketFactory
from apps.tickets.models import SavedFilter, Status


@pytest.mark.django_db
def test_export_tickets_csv(client):
    hostel = HostelFactory(name="CV Raman Bhavan")
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)

    t1 = TicketFactory(
        hostel=hostel, reporter=student, assigned_to=caretaker, title="Fan regulator broken"
    )

    client.force_login(caretaker)
    response = client.get(reverse("tickets:export_csv"))

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert "attachment; filename=" in response["Content-Disposition"]

    content = response.content.decode("utf-8")
    assert "Ticket No" in content
    assert "Title" in content
    assert t1.ticket_no in content
    assert "Fan regulator broken" in content


@pytest.mark.django_db
def test_search_quick_api(client):
    hostel = HostelFactory()
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)
    ticket = TicketFactory(
        hostel=hostel,
        reporter=student,
        title="Water heater leakage in 304",
    )

    client.force_login(student)

    # 1. Short query returns empty
    res = client.get(reverse("tickets:search_quick"), {"q": "w"})
    assert res.status_code == 200
    assert res.json()["results"] == []

    # 2. Matching query
    res = client.get(reverse("tickets:search_quick"), {"q": "leakage"})
    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) == 1
    assert results[0]["ticket_no"] == ticket.ticket_no
    assert results[0]["title"] == "Water heater leakage in 304"


@pytest.mark.django_db
def test_saved_filter_crud(client):
    hostel = HostelFactory()
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)

    client.force_login(student)

    # 1. Save filter
    res = client.post(
        reverse("tickets:save_filter"),
        {"name": "Urgent Issues", "querystring": "priority=URGENT", "view": "list"},
    )
    assert res.status_code == 302
    assert SavedFilter.objects.filter(user=student, name="Urgent Issues").exists()

    sf = SavedFilter.objects.get(user=student, name="Urgent Issues")

    # 2. Delete filter
    res = client.post(reverse("tickets:delete_filter", kwargs={"filter_id": sf.id}))
    assert res.status_code == 302
    assert not SavedFilter.objects.filter(id=sf.id).exists()


@pytest.mark.django_db
def test_bulk_actions(client):
    hostel = HostelFactory()
    caretaker1 = UserFactory(role=Role.CARETAKER, hostel=hostel)
    caretaker2 = UserFactory(role=Role.CARETAKER, hostel=hostel)
    student = UserFactory(role=Role.HOSTELER, hostel=hostel)

    t1 = TicketFactory(
        hostel=hostel,
        reporter=student,
        assigned_to=caretaker1,
        status=Status.ASSIGNED,
    )
    t2 = TicketFactory(
        hostel=hostel,
        reporter=student,
        assigned_to=caretaker1,
        status=Status.ASSIGNED,
    )

    # 1. Hosteler cannot bulk act
    client.force_login(student)
    res = client.post(
        reverse("tickets:bulk_action"),
        {
            "action": "status",
            "target_value": Status.IN_PROGRESS,
            "selected_tickets": [t1.id, t2.id],
        },
    )
    assert res.status_code == 302
    t1.refresh_from_db()
    assert t1.status == Status.ASSIGNED  # Unchanged

    # 2. Staff bulk update status
    client.force_login(caretaker1)
    res = client.post(
        reverse("tickets:bulk_action"),
        {
            "action": "status",
            "target_value": Status.IN_PROGRESS,
            "selected_tickets": [t1.id, t2.id],
        },
    )
    assert res.status_code == 302
    t1.refresh_from_db()
    t2.refresh_from_db()
    assert t1.status == Status.IN_PROGRESS
    assert t2.status == Status.IN_PROGRESS

    # 3. Staff bulk assign
    res = client.post(
        reverse("tickets:bulk_action"),
        {
            "action": "assign",
            "target_value": str(caretaker2.id),
            "selected_tickets": [t1.id, t2.id],
        },
    )
    assert res.status_code == 302
    t1.refresh_from_db()
    t2.refresh_from_db()
    assert t1.assigned_to == caretaker2
    assert t2.assigned_to == caretaker2


def test_custom_error_pages(client):
    from django.contrib.auth.models import AnonymousUser
    from django.test import RequestFactory

    from apps.core.views import error_403, error_404, error_500

    rf = RequestFactory()
    req = rf.get("/")
    req.user = AnonymousUser()

    res_403 = error_403(req)
    assert res_403.status_code == 403
    assert "Access Denied" in res_403.content.decode("utf-8")

    res_404 = error_404(req)
    assert res_404.status_code == 404
    assert "Page Not Found" in res_404.content.decode("utf-8")

    res_500 = error_500(req)
    assert res_500.status_code == 500
    assert "Server Error" in res_500.content.decode("utf-8")
