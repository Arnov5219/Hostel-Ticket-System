import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel
from apps.tickets.models import ActivityAction, Category, Status, Ticket, TicketActivity


@pytest.fixture
def cleanup_data(db):
    h1, _ = Hostel.objects.get_or_create(code="BH-1", defaults={"name": "Bhabha Bhavan", "is_active": True})
    h2, _ = Hostel.objects.get_or_create(code="AB-1", defaults={"name": "Aryabhatta Bhavan", "is_active": True})

    hosteler = User.objects.create_user(
        login_id="HOSTELER1",
        email="hosteler1@campus.edu",
        password="pwd",
        role=Role.HOSTELER,
        hostel=h1,
        full_name="Alice Hosteler",
    )
    caretaker = User.objects.create_user(
        login_id="CARETAKER1",
        email="caretaker1@campus.edu",
        password="pwd",
        role=Role.CARETAKER,
        hostel=h1,
        full_name="Bob Caretaker",
    )
    h1.responsible_staff = caretaker
    h1.save()

    admin = User.objects.create_user(
        login_id="ADMIN1",
        email="admin1@campus.edu",
        password="pwd",
        role=Role.ADMIN,
        full_name="Admin User",
    )

    cat, _ = Category.objects.get_or_create(name="Plumbing", defaults={"icon": "droplet", "is_active": True})
    cat2, _ = Category.objects.get_or_create(name="Electrical", defaults={"icon": "zap", "is_active": True})

    return {
        "h1": h1,
        "h2": h2,
        "hosteler": hosteler,
        "caretaker": caretaker,
        "admin": admin,
        "cat": cat,
        "cat2": cat2,
    }


@pytest.mark.django_db
class TestNavbarSearchRemoval:
    """Acceptance: No global ticket-search appears in navbar, but ticket list search works."""

    def test_navbar_search_removed_from_base_template(self, client, cleanup_data):
        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        res = client.get(reverse("dashboard:index"))
        assert res.status_code == 200
        content = res.content.decode()

        assert "search-trigger" not in content
        assert "Search tickets..." not in content
        assert 'id="command-palette"' not in content

    def test_ticket_list_filters_and_search_still_work(self, client, cleanup_data):
        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        # Ticket list search filter
        res = client.get(reverse("tickets:list"), {"search": "geyser"})
        assert res.status_code == 200
        content = res.content.decode()
        assert "Search:" in content or 'name="search"' in content


@pytest.mark.django_db
class TestHostelerHostelChangePrevention:
    """Acceptance: Hosteler cannot change hostel via UI or direct request. Creation uses assigned hostel."""

    def test_profile_page_has_no_hostel_change_controls(self, client, cleanup_data):
        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        res = client.get(reverse("accounts:profile"))
        assert res.status_code == 200
        content = res.content.decode()

        assert "profile-hostel-select" not in content
        assert "editingResidence" not in content
        assert "Managed by Admin" in content

    def test_crafted_profile_residence_post_is_blocked_for_hosteler(self, client, cleanup_data):
        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        # Attempt to post a different hostel to profile_residence
        res = client.post(
            reverse("accounts:profile_residence"),
            {"hostel": cleanup_data["h2"].id},
            follow=True,
        )
        assert res.status_code == 200
        cleanup_data["hosteler"].refresh_from_db()
        assert cleanup_data["hosteler"].hostel == cleanup_data["h1"]
        assert "Hostel assignments are managed by administration" in res.content.decode()

    def test_ticket_create_forces_assigned_hostel_even_if_tampered(self, client, cleanup_data):
        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")

        # 1. UI renders read-only hostel
        res = client.get(reverse("tickets:create"))
        assert res.status_code == 200
        content = res.content.decode()
        assert "ASSIGNED HOSTEL" in content
        assert "Read-only" in content
        assert "differentHostel" not in content

        # 2. Tampered POST with different hostel ID (h2)
        create_res = client.post(
            reverse("tickets:create"),
            {
                "title": "Broken window latch",
                "room_number": "102",
                "description": "Room 102 window doesn't close properly",
                "category": cleanup_data["cat"].id,
                "priority": "MEDIUM",
                "hostel": cleanup_data["h2"].id,  # Tampered attempt!
            },
        )
        assert create_res.status_code == 302
        created_ticket = Ticket.objects.filter(reporter=cleanup_data["hosteler"]).first()
        assert created_ticket is not None
        # Must be strictly assigned to hosteler's own hostel (h1), NOT h2
        assert created_ticket.hostel == cleanup_data["h1"]


@pytest.mark.django_db
class TestCategorySelectorStyling:
    """Acceptance: Category options render completely as accessible cards with no clipping."""

    def test_category_selector_renders_grid_and_accessible_cards(self, client, cleanup_data):
        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        res = client.get(reverse("tickets:create"))
        assert res.status_code == 200
        content = res.content.decode()

        assert "category-selector-grid" in content
        assert "category-card" in content
        assert 'role="radio"' in content
        assert "Plumbing" in content
        assert "Electrical" in content


@pytest.mark.django_db
class TestTicketCommentsRemoval:
    """Acceptance: Comments UI and endpoints removed/disabled, timeline and audit preserved."""

    def test_ticket_detail_renders_timeline_not_comments(self, client, cleanup_data):
        ticket = Ticket.objects.create(
            ticket_no="BH1-2026-0001",
            title="Broken shower knob",
            description="Leaking water",
            reporter=cleanup_data["hosteler"],
            hostel=cleanup_data["h1"],
            category=cleanup_data["cat"],
            assigned_to=cleanup_data["caretaker"],
            status=Status.ASSIGNED,
        )
        TicketActivity.objects.create(
            ticket=ticket,
            actor=cleanup_data["hosteler"],
            action=ActivityAction.CREATED,
            note="Ticket raised by hosteler",
        )

        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        res = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
        assert res.status_code == 200
        content = res.content.decode()

        assert "Activity Timeline" in content
        assert "Timeline events (1)" in content
        assert "Ticket raised by hosteler" in content
        assert "Add a response" not in content
        assert "Send reply" not in content

    def test_comment_endpoint_is_forbidden(self, client, cleanup_data):
        ticket = Ticket.objects.create(
            ticket_no="BH1-2026-0002",
            title="Fan regulator faulty",
            description="Speed doesn't change",
            reporter=cleanup_data["hosteler"],
            hostel=cleanup_data["h1"],
            category=cleanup_data["cat"],
            assigned_to=cleanup_data["caretaker"],
            status=Status.ASSIGNED,
        )

        client.login(username=cleanup_data["hosteler"].login_id, password="pwd")
        res = client.post(
            reverse("tickets:comment", kwargs={"ticket_no": ticket.ticket_no}),
            {"body": "Hello is this fixed?"},
        )
        assert res.status_code == 403
        assert ticket.comments.count() == 0
