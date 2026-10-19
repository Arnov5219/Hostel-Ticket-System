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


@pytest.mark.django_db
def test_kanban_collapsed_by_default(client):
    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, password="staff_pwd")
    client.login(username=caretaker.login_id, password="staff_pwd")

    # Create tickets across multiple statuses
    for st in [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD, Status.RESOLVED]:
        TicketFactory(hostel=hostel, status=st)

    response = client.get(reverse("tickets:kanban"))
    assert response.status_code == 200
    content = response.content.decode()

    # Board initializes with allOpen = false
    assert "allOpen: false" in content

    # All stage columns initialize with isOpen: false (collapsed)
    assert 'x-data="{ isOpen: false, sortPrio: false }"' in content
    assert 'x-data="{ isOpen: true, sortPrio: false }"' not in content

    # Stage header supports click-to-expand
    assert '@click="isOpen = !isOpen"' in content

    # Cards containers are bound to x-show="isOpen" with x-cloak
    assert 'x-show="isOpen" x-cloak' in content

    # Verify all 5 stages exist in the rendered board
    for st in ["open", "assigned", "in_progress", "on_hold", "resolved"]:
        assert f'class="kanban-column {st}"' in content

    # No persistent storage logic for expansion state in kanban.js
    from pathlib import Path
    kanban_js = (Path(__file__).parent.parent / "static" / "js" / "kanban.js").read_text(encoding="utf-8")
    assert "localStorage" not in kanban_js
    assert "sessionStorage" not in kanban_js


@pytest.mark.django_db
def test_kanban_light_theme_and_non_sticky_tabs(client):
    from pathlib import Path
    from apps.accounts.models import Theme

    hostel = HostelFactory()
    caretaker = UserFactory(role=Role.CARETAKER, hostel=hostel, theme=Theme.LIGHT, password="staff_pwd")
    client.login(username=caretaker.login_id, password="staff_pwd")

    # Create tickets across statuses to populate cards
    for st in [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD, Status.RESOLVED]:
        TicketFactory(hostel=hostel, status=st, title=f"Test Ticket for {st}")

    response = client.get(reverse("tickets:kanban"))
    assert response.status_code == 200
    content = response.content.decode()

    # Renders with light theme
    assert 'data-user-theme="LIGHT"' in content
    assert 'data-theme-pref="light"' in content

    # Toolbar and card surfaces use theme tokens, not hardcoded dark colors
    assert "kanban-toolbar" in content
    assert "#0d1527" not in content
    assert "#070c17" not in content
    assert "rgba(13, 21, 39" not in content

    # Status tabs are completely removed from Kanban layout
    assert "kanban-tab-strip" not in content
    assert "kanban-tab-btn" not in content

    # Check kanban.css properties
    kanban_css = (Path(__file__).parent.parent / "static" / "css" / "kanban.css").read_text(encoding="utf-8")
    # Verify no sticky positioning in kanban.css
    assert "position: sticky" not in kanban_css
    assert "position: fixed" not in kanban_css
    assert "kanban-tab-strip" not in kanban_css

    # Verify CSS uses design system variables for surfaces and text
    assert "var(--bg-surface)" in kanban_css
    assert "var(--text-primary)" in kanban_css
    assert "var(--border)" in kanban_css
    assert "var(--primary)" in kanban_css


@pytest.mark.django_db
def test_kanban_status_tabs_removed_preserves_stages(client):
    """Horizontal status tabs are removed while stage sections, headers, and filters remain."""
    hostel = HostelFactory(name="Hostel Alpha", code="HA")
    staff = UserFactory(role=Role.CARETAKER, hostel=hostel, password="password123")
    client.login(username=staff.login_id, password="password123")

    # Seed tickets across all statuses
    for st in [Status.OPEN, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD, Status.RESOLVED]:
        TicketFactory(hostel=hostel, status=st, title=f"Sample {st}")

    response = client.get(reverse("tickets:kanban"))
    assert response.status_code == 200
    content = response.content.decode()

    # Redundant horizontal status tabs must NOT exist
    assert "kanban-tab-strip" not in content
    assert "kanban-tab-btn" not in content
    assert "tab-btn-" not in content

    # Search filter and toolbar controls must be present
    assert "Filter cards on board..." in content
    assert "Expand all stages" in content
    assert "Collapse all stages" in content

    # All stage headers and counts must be preserved
    assert "kanban-stage-header" in content
    assert "Open" in content
    assert "Assigned" in content
    assert "In Progress" in content
    assert "On Hold" in content
    assert "Resolved" in content
    assert "kanban-cards-container" in content
    assert "Sample OPEN" in content
    assert "Sample RESOLVED" in content
