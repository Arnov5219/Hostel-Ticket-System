from django.conf import settings


def test_django_setup():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert settings.TIME_ZONE == "Asia/Kolkata"
