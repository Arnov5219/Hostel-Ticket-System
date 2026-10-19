import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import AnnouncementSeverity, AnnouncementStatus
from apps.hostels.models import GenderType, Hostel, Room
from apps.tickets.factories import TicketFactory


@pytest.mark.django_db
def test_launch_screen_rendered_in_base_templates(client):
    """Verify app launch screen is present in base HTML markup."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert 'id="app-launch-screen"' in content
    assert "HostelFlow" in content
    assert "launch-logo-badge" in content
    assert 'id="launch-progress-bar"' in content
    assert 'id="launch-status-text"' in content
    assert 'id="launch-fallback-box"' in content
    assert "launch-retry-btn" in content
    assert "hf_app_launched" in content


@pytest.mark.django_db
def test_dashboard_does_not_show_mobile_back_button(client):
    """Root / Dashboard page must display brand title and NOT show a back button."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-brand-title" in content
    # In page-header, mobile-back-nav should not be rendered
    assert '<div class="mobile-back-nav">' not in content


@pytest.mark.django_db
def test_mobile_back_button_renders_on_ticket_list(client):
    """Ticket list page must include mobile back button with fallback."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("tickets:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-back-nav" in content
    assert "mobile-back-btn" in content
    assert "handleMobileBack(this)" in content
    assert 'data-fallback="' in content


@pytest.mark.django_db
def test_mobile_back_button_renders_on_ticket_detail(client):
    """Ticket detail page must include mobile back button."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    ticket = TicketFactory(hostel=hostel, reporter=hosteler, title="Broken switch")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-back-nav" in content
    assert "mobile-back-btn" in content
    assert "handleMobileBack(this)" in content


@pytest.mark.django_db
def test_mobile_back_button_renders_on_ticket_create(client):
    """Ticket create page must include mobile back button."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    room = Room.objects.create(hostel=hostel, room_number="101", floor=1)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, room=room, password="password123")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("tickets:create"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-back-nav" in content
    assert "mobile-back-btn" in content
    assert "handleMobileBack(this)" in content


@pytest.mark.django_db
def test_mobile_back_button_renders_on_notifications(client):
    """Notifications page must include mobile back button."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-back-nav" in content
    assert "mobile-back-btn" in content
    assert "handleMobileBack(this)" in content


@pytest.mark.django_db
def test_mobile_back_button_renders_on_profile(client):
    """Profile page must include mobile back button."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-back-nav" in content
    assert "mobile-back-btn" in content
    assert "handleMobileBack(this)" in content


@pytest.mark.django_db
def test_mobile_back_button_on_custom_admin_headers(client):
    """Custom mobile headers on hostel management pages have mobile back button."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    admin = UserFactory(role=Role.ADMIN, hostel=hostel, password="password123")
    client.login(username=admin.login_id, password="password123")

    # 1. Manage Hostels
    res = client.get(reverse("hostels:manage_hostels"))
    assert res.status_code == 200
    assert "mobile-back-btn" in res.content.decode("utf-8")

    # 2. Manage Staff
    res = client.get(reverse("hostels:manage_staff"))
    assert res.status_code == 200
    assert "mobile-back-btn" in res.content.decode("utf-8")

    # 3. Manage Responsibility
    res = client.get(reverse("hostels:manage_responsibility"))
    assert res.status_code == 200
    assert "mobile-back-btn" in res.content.decode("utf-8")

    # 4. Trash Log
    res = client.get(reverse("manage_trash"))
    assert res.status_code == 200
    assert "mobile-back-btn" in res.content.decode("utf-8")


@pytest.mark.django_db
def test_mobile_back_button_renders_on_announcement_detail(client):
    """Notice detail page must include mobile back button pointing to notices list."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, password="password123")
    warden = UserFactory(role=Role.WARDEN, hostel=hostel)
    ann = AnnouncementFactory(
        author=warden,
        all_hostels=True,
        severity=AnnouncementSeverity.INFO,
        status=AnnouncementStatus.PUBLISHED,
        title="Notice for Residents",
    )
    client.login(username=hosteler.login_id, password="password123")

    response = client.get(reverse("announcements:detail", kwargs={"announcement_id": ann.id}))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "mobile-back-nav" in content
    assert "mobile-back-btn" in content
    assert "handleMobileBack(this)" in content
    assert f'data-fallback="{reverse("announcements:list")}"' in content


@pytest.mark.django_db
def test_mobile_back_fallbacks_on_key_screens(client):
    """Verify context-specific parent fallback URLs on key screens."""
    hostel = Hostel.objects.create(name="Hostel One", code="H1", gender_type=GenderType.BOYS)
    room = Room.objects.create(hostel=hostel, room_number="102", floor=1)
    hosteler = UserFactory(role=Role.HOSTELER, hostel=hostel, room=room, password="password123")
    ticket = TicketFactory(hostel=hostel, reporter=hosteler, title="Leaking tap")
    client.login(username=hosteler.login_id, password="password123")

    # 1. Ticket Detail -> tickets:list
    res_ticket = client.get(reverse("tickets:detail", kwargs={"ticket_no": ticket.ticket_no}))
    assert res_ticket.status_code == 200
    assert f'data-fallback="{reverse("tickets:list")}"' in res_ticket.content.decode("utf-8")

    # 2. Ticket Create -> tickets:list
    res_create = client.get(reverse("tickets:create"))
    assert res_create.status_code == 200
    assert f'data-fallback="{reverse("tickets:list")}"' in res_create.content.decode("utf-8")

    # 3. User Profile -> dashboard:index
    res_profile = client.get(reverse("accounts:profile"))
    assert res_profile.status_code == 200
    assert f'data-fallback="{reverse("dashboard:index")}"' in res_profile.content.decode("utf-8")

    # 4. Notifications List -> dashboard:index
    res_notif = client.get(reverse("notifications:list"))
    assert res_notif.status_code == 200
    assert f'data-fallback="{reverse("dashboard:index")}"' in res_notif.content.decode("utf-8")

    # 5. Kanban Board -> tickets:list
    staff = UserFactory(role=Role.CARETAKER, hostel=hostel, password="password123")
    client.login(username=staff.login_id, password="password123")
    res_kanban = client.get(reverse("tickets:kanban"))
    assert res_kanban.status_code == 200
    assert f'data-fallback="{reverse("tickets:list")}"' in res_kanban.content.decode("utf-8")


@pytest.mark.django_db
def test_auth_pages_back_navigation_security(client):
    """Auth pages (login & register) purge stale session stacks and guard against bfcache re-exposure."""
    # 1. Login page
    res_login = client.get(reverse("accounts:login"))
    assert res_login.status_code == 200
    login_html = res_login.content.decode("utf-8")
    assert "sessionStorage.removeItem('hf_nav_stack')" in login_html
    assert "hf_scroll_" in login_html
    assert "pageshow" in login_html

    # 2. Register page
    res_reg = client.get(reverse("accounts:register"))
    assert res_reg.status_code == 200
    reg_html = res_reg.content.decode("utf-8")
    assert "sessionStorage.removeItem('hf_nav_stack')" in reg_html
    assert "hf_scroll_" in reg_html
    assert "pageshow" in reg_html


def test_mobile_js_navigation_contracts():
    """Verify app.js provides required navigation utilities, overlay dismissals, and Capacitor listeners."""
    with open("static/js/app.js", "r", encoding="utf-8") as f:
        js_code = f.read()

    # Core utilities
    assert "window.dismissOpenOverlays" in js_code
    assert "window.hasUnsavedChanges" in js_code
    assert "window.confirmDiscardChanges" in js_code
    assert "window.handleMobileBack" in js_code

    # Overlay classes handled
    assert ".bottom-sheet-backdrop" in js_code
    assert ".app-modal-backdrop" in js_code
    assert "command-palette-backdrop" in js_code

    # History & scroll state preservation
    assert "hf_nav_stack" in js_code
    assert "hf_scroll_" in js_code
    assert "restoreScrollPosition" in js_code

    # Bottom navigation deduplication
    assert ".mobile-bottom-nav" in js_code
    assert "['/dashboard/']" in js_code

    # Capacitor App backButton integration
    assert "App.addListener('backButton'" in js_code
    assert "dismissOpenOverlays" in js_code
    assert "confirmDiscardChanges" in js_code
    assert "exitApp" in js_code

