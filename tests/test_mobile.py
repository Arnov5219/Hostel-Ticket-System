import json
from pathlib import Path
import pytest
from django.urls import reverse
from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.models import Block, GenderType, Hostel, Room
from apps.tickets.factories import TicketFactory


BASE_DIR = Path(__file__).resolve().parent.parent


def test_manifest_file_exists_and_valid():
    """Verify web manifest is present, valid JSON, and meets standalone PWA specs."""
    manifest_path = BASE_DIR / "static" / "manifest.webmanifest"
    assert manifest_path.exists(), "static/manifest.webmanifest should exist"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data.get("display") == "standalone"
    assert "name" in data
    assert "icons" in data
    assert len(data["icons"]) >= 2


@pytest.mark.django_db
def test_mobile_bottom_nav_renders_for_hosteler(client):
    """Hosteler bottom nav must contain Home, Community, Raise, News, and More."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    block = Block.objects.create(hostel=hostel, name="Block A")
    room = Room.objects.create(block=block, room_number="101", floor=1)
    hosteler = UserFactory(
        role=Role.HOSTELER,
        hostel=hostel,
        room=room,
        password="password123",
    )
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("tickets:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-bottom-nav" in content
    assert "raise-center-btn" in content
    assert "Community" in content
    assert "News" in content
    assert "moreOpen" in content


@pytest.mark.django_db
def test_mobile_bottom_nav_renders_for_staff(client):
    """Staff bottom nav must contain Dashboard, Tickets, Kanban, Alerts, and More."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="password123")
    client.login(username=caretaker.login_id, password="password123")

    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-bottom-nav" in content
    assert "Dashboard" in content
    assert "Kanban" in content
    assert "Alerts" in content
    assert "moreOpen" in content


@pytest.mark.django_db
def test_ticket_list_renders_both_desktop_and_mobile_views(client):
    """Ticket list table includes responsive desktop table view and mobile card list."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    user = UserFactory(role=Role.CARETAKER, hostel=hostel, password="password123")
    ticket = TicketFactory(hostel=hostel, title="Water heater broken")
    client.login(username=user.login_id, password="password123")

    response = client.get(reverse("tickets:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "desktop-table-view" in content
    assert "mobile-card-list" in content
    assert "Water heater broken" in content
    assert "mobileFilterOpen" in content  # Mobile filter bottom sheet


@pytest.mark.django_db
def test_kanban_renders_mobile_tab_strip_and_move_fallback(client):
    """Kanban board includes status tab strip and card action fallback for mobile."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="password123")
    ticket = TicketFactory(hostel=hostel, assigned_to=caretaker, status="ASSIGNED", title="Leaking tap")
    client.login(username=caretaker.login_id, password="password123")

    response = client.get(reverse("tickets:kanban"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "kanban-tab-strip" in content
    assert "MOVE TO" in content


@pytest.mark.django_db
def test_ticket_create_has_camera_capture_options(client):
    """Ticket create template includes camera capture and gallery options."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    block = Block.objects.create(hostel=hostel, name="Block A")
    room = Room.objects.create(block=block, room_number="101", floor=1)
    hosteler = UserFactory(
        role=Role.HOSTELER,
        hostel=hostel,
        room=room,
        password="password123",
    )
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("tickets:create"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert 'capture="environment"' in content
    assert 'raise-submit-bar' in content
