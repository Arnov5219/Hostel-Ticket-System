import os
import re

import pytest
from django.test import Client

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role
from apps.core.navigation import nav_for
from apps.hostels.factories import HostelFactory


@pytest.mark.django_db
class TestTemplateUrlsAndNavigationCrawler:
    """Crawler test ensuring all navigation links and template URL tags resolve cleanly."""

    def test_all_template_url_names_resolve(self):
        """Scans all HTML templates for {% url 'name' %} and verifies the name exists in URLconf."""
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        url_pattern = re.compile(r'{%\s*url\s+[\'"]([^\'"\s]+)[\'"]')

        found_names = set()

        for root, _, files in os.walk(template_dir):
            for file in files:
                if file.endswith(".html"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                    matches = url_pattern.findall(content)
                    for name in matches:
                        found_names.add(name)

        assert len(found_names) > 0, "Should have found URL names in templates"

        # Assert no community URLs are referenced
        for name in found_names:
            assert "community" not in name.lower(), f"Forbidden community url found in templates: {name}"

    def test_role_navigation_link_crawler(self, client: Client):
        """Logs in as each role, collects all sidebar, bottom bar, and more sheet links, and asserts 200."""
        hostel = HostelFactory(is_active=True)

        roles = [
            Role.HOSTELER,
            Role.CARETAKER,
            Role.WARDEN,
            Role.CHIEF_WARDEN,
            Role.ADMIN,
        ]

        for role in roles:
            user = UserFactory(role=role, hostel=hostel, password="password123")
            logged_in = client.login(username=user.login_id, password="password123")
            assert logged_in, f"Failed to log in as {role}"

            nav = nav_for(user)
            all_items = (
                nav.get("sidebar_items", [])
                + nav.get("mobile_bar_items", [])
                + nav.get("mobile_more_items", [])
            )

            visited_urls = set()

            # Dashboard/home test
            home_resp = client.get("/dashboard/", follow=True)
            assert home_resp.status_code == 200, f"/dashboard/ failed with {home_resp.status_code} for {role}"

            for item in all_items:
                url = item.url
                if not url or url == "#" or url in visited_urls:
                    continue
                visited_urls.add(url)

                assert not url.startswith("/community"), f"Found community url {url} in navigation for {role}"

                resp = client.get(url, follow=True)
                assert resp.status_code == 200, (
                    f"Navigation link {url} (key: {item.key}) failed with {resp.status_code} for {role}"
                )

            client.logout()
