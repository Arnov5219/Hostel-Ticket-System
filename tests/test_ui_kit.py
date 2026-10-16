import os
import re

import pytest
from django.urls import NoReverseMatch, reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.hostels.factories import HostelFactory


@pytest.mark.django_db
class TestUIKitRemoved:
    """Verifies that all UI kit, review samples, and showcase pages are completely removed."""

    def test_ui_kit_route_returns_404(self, client):
        """Accessing /ui-kit/ must return a 404 response."""
        response = client.get("/ui-kit/")
        assert response.status_code == 404

    def test_core_ui_kit_reverse_does_not_exist(self):
        """core:ui_kit must raise NoReverseMatch."""
        with pytest.raises(NoReverseMatch):
            reverse("core:ui_kit")

    def test_no_templates_contain_ui_kit_references(self):
        """Scans all templates to ensure no references to ui_kit exist."""
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        url_pattern = re.compile(r'{%\s*url\s+[\'"]([^\'"\s]+)[\'"]')

        for root, _, files in os.walk(template_dir):
            for file in files:
                if file.endswith(".html"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                    matches = url_pattern.findall(content)
                    for name in matches:
                        assert "ui_kit" not in name, f"Found ui_kit url tag '{name}' in {filepath}"
                    assert 'title="UI Kit"' not in content, f"Found UI Kit title attribute in {filepath}"
                    assert ">UI Kit<" not in content, f"Found UI Kit label in {filepath}"

    def test_sidebar_does_not_render_ui_kit_for_any_role(self, client):
        """Every authenticated user role must see only real application navigation."""
        hostel = HostelFactory(is_active=True)
        roles = [
            Role.HOSTELER,
            Role.CARETAKER,
            Role.WARDEN,
            Role.CHIEF_WARDEN,
            Role.DEAN,
            Role.ADMIN,
        ]

        for role in roles:
            user = UserFactory(role=role, hostel=hostel, password="password123")
            client.login(username=user.login_id, password="password123")

            response = client.get("/dashboard/", follow=True)
            assert response.status_code == 200
            content = response.content.decode("utf-8")

            # UI Kit must not appear in sidebar or anywhere in page
            assert "UI Kit" not in content, f"UI Kit found in rendered dashboard for {role}"
            assert "/ui-kit/" not in content, f"/ui-kit/ link found in rendered dashboard for {role}"

            client.logout()
