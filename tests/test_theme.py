import pytest
from django.urls import reverse

from apps.accounts.models import Role, Theme, User


@pytest.fixture
def theme_user(db):
    return User.objects.create_user(
        login_id="theme_test_user",
        full_name="Theme Tester",
        role=Role.HOSTELER,
        password="password123",
    )


@pytest.mark.django_db
class TestThemeFeatures:
    def test_default_theme_is_system(self, theme_user):
        assert theme_user.theme == Theme.SYSTEM

    def test_authenticated_theme_update(self, client, theme_user):
        client.force_login(theme_user)
        url = reverse("accounts:theme")

        # Set to DARK
        res_dark = client.post(url, {"theme": "DARK"})
        assert res_dark.status_code == 204
        theme_user.refresh_from_db()
        assert theme_user.theme == Theme.DARK

        # Set to LIGHT
        res_light = client.post(url, {"theme": "LIGHT"})
        assert res_light.status_code == 204
        theme_user.refresh_from_db()
        assert theme_user.theme == Theme.LIGHT

        # Set to SYSTEM
        res_sys = client.post(url, {"theme": "SYSTEM"})
        assert res_sys.status_code == 204
        theme_user.refresh_from_db()
        assert theme_user.theme == Theme.SYSTEM

    def test_invalid_theme_rejected(self, client, theme_user):
        client.force_login(theme_user)
        url = reverse("accounts:theme")
        res = client.post(url, {"theme": "BLUE"})
        assert res.status_code == 400

    def test_anonymous_theme_post_succeeds(self, client):
        url = reverse("accounts:theme")
        res = client.post(url, {"theme": "DARK"})
        assert res.status_code == 204

    def test_base_template_renders_user_theme(self, client, theme_user):
        theme_user.theme = Theme.DARK
        theme_user.save()
        client.force_login(theme_user)

        res = client.get(reverse("accounts:onboarding"))
        content = res.content.decode()
        assert 'data-user-theme="DARK"' in content
        assert "meta-theme-color" in content
        assert "data-theme" in content
