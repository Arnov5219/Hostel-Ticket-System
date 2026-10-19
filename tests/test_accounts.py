import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import (
    can_add_internal_note,
    can_manage_config,
    can_raise_ticket,
    can_view_kanban,
)


@pytest.mark.django_db
def test_login_success(client):
    UserFactory(login_id="STU1001", password="secure_password")
    response = client.post(
        reverse("accounts:login"),
        {"login_id": "STU1001", "password": "secure_password"},
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:index")


@pytest.mark.django_db
def test_login_case_insensitive(client):
    UserFactory(login_id="CARETAKER_BH1", password="secure_password")
    response = client.post(
        reverse("accounts:login"),
        {"login_id": "caretaker_bh1", "password": "secure_password"},
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:index")


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    UserFactory(login_id="STU1002", password="secure_password")
    response = client.post(
        reverse("accounts:login"),
        {"login_id": "STU1002", "password": "wrong_password"},
    )
    assert response.status_code == 200
    assert "Invalid Roll No / Employee ID or password." in response.content.decode()


@pytest.mark.django_db
def test_logout(client):
    UserFactory(login_id="STU1003", password="secure_password")
    client.login(username="STU1003", password="secure_password")
    response = client.get(reverse("accounts:logout"))
    assert response.status_code == 302
    assert response.url == reverse("accounts:login")


@pytest.mark.django_db
def test_permissions_by_role():
    hosteler = UserFactory(role=Role.HOSTELER)
    caretaker = UserFactory(role=Role.CARETAKER)
    warden = UserFactory(role=Role.WARDEN)
    dean = UserFactory(role=Role.DEAN)
    admin = UserFactory(role=Role.ADMIN)

    # can_raise_ticket
    assert can_raise_ticket(hosteler) is True
    assert can_raise_ticket(caretaker) is False
    assert can_raise_ticket(admin) is True

    # can_view_kanban (operational staff only, not admin)
    assert can_view_kanban(hosteler) is False
    assert can_view_kanban(caretaker) is True
    assert can_view_kanban(warden) is True
    assert can_view_kanban(dean) is True
    assert can_view_kanban(admin) is False

    # can_manage_config (strictly admin)
    assert can_manage_config(hosteler) is False
    assert can_manage_config(caretaker) is False
    assert can_manage_config(warden) is False
    assert can_manage_config(dean) is False
    assert can_manage_config(admin) is True

    # can_add_internal_note
    assert can_add_internal_note(hosteler) is False
    assert can_add_internal_note(caretaker) is True
    assert can_add_internal_note(warden) is True
    assert can_add_internal_note(dean) is True


@pytest.mark.django_db
def test_role_required_mixin():
    from django.views import View

    class ProtectedView(RoleRequiredMixin, View):
        allowed_roles = [Role.ADMIN]

        def get(self, request):
            return "OK"

    view = ProtectedView()
    factory = RequestFactory()

    # Hosteler accessing admin view raises 403
    request = factory.get("/fake-url/")
    request.user = UserFactory(role=Role.HOSTELER)
    with pytest.raises(PermissionDenied):
        view.dispatch(request)

    # Admin accessing admin view succeeds
    request.user = UserFactory(role=Role.ADMIN)
    response = view.dispatch(request)
    assert response == "OK"
