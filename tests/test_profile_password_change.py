import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.accounts.models import Role


@pytest.mark.django_db
def test_profile_view_initial_state(client):
    user = UserFactory(login_id="TESTUSER01", password="InitialPassword123!", role=Role.HOSTELER)
    client.login(username="TESTUSER01", password="InitialPassword123!")

    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 200
    content = response.content.decode()

    # Profile Information is rendered
    assert "Profile information" in content
    assert "Save profile" in content

    # Change Password toggle button is present
    assert "btn-toggle-password" in content
    assert "Change Password" in content

    # Change password card is hidden by default via Alpine state
    assert 'passwordOpen: false' in content
    assert 'id="change-password-card"' in content
    assert 'x-show="passwordOpen"' in content

    # All three password fields are rendered
    assert 'name="old_password"' in content
    assert 'name="new_password1"' in content
    assert 'name="new_password2"' in content

    # Requirement message and eye icons are rendered
    assert "Password requirements:" in content
    assert "Must be at least 8 characters long" in content
    assert "data-lucide=\"eye\"" in content
    assert "data-lucide=\"eye-off\"" in content

    # Cancel and Update buttons exist
    assert "Update password" in content
    assert "Cancel" in content


@pytest.mark.django_db
def test_change_password_mismatch(client):
    user = UserFactory(login_id="TESTUSER02", password="CurrentPassword123!", role=Role.HOSTELER)
    client.login(username="TESTUSER02", password="CurrentPassword123!")

    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "change_password",
            "old_password": "CurrentPassword123!",
            "new_password1": "NewValidPassword456!",
            "new_password2": "MismatchedPassword789!",
        },
    )
    assert response.status_code == 200
    content = response.content.decode()

    assert "The new passwords do not match." in content
    # When errors are present, form is automatically kept open
    assert "passwordOpen: true" in content

    user.refresh_from_db()
    assert user.check_password("CurrentPassword123!") is True
    assert user.check_password("NewValidPassword456!") is False


@pytest.mark.django_db
def test_change_password_length_validation(client):
    user = UserFactory(login_id="TESTUSER03", password="CurrentPassword123!", role=Role.HOSTELER)
    client.login(username="TESTUSER03", password="CurrentPassword123!")

    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "change_password",
            "old_password": "CurrentPassword123!",
            "new_password1": "short",
            "new_password2": "short",
        },
    )
    assert response.status_code == 200
    content = response.content.decode()

    assert "Password must be at least 8 characters long." in content
    assert "passwordOpen: true" in content

    user.refresh_from_db()
    assert user.check_password("CurrentPassword123!") is True


@pytest.mark.django_db
def test_change_password_invalid_current_password(client):
    user = UserFactory(login_id="TESTUSER04", password="CurrentPassword123!", role=Role.HOSTELER)
    client.login(username="TESTUSER04", password="CurrentPassword123!")

    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "change_password",
            "old_password": "WrongCurrentPassword!",
            "new_password1": "BrandNewPassword123!",
            "new_password2": "BrandNewPassword123!",
        },
    )
    assert response.status_code == 200
    content = response.content.decode()

    assert "Invalid current password. Please enter it again." in content
    assert "passwordOpen: true" in content

    user.refresh_from_db()
    assert user.check_password("CurrentPassword123!") is True
    assert user.check_password("BrandNewPassword123!") is False


@pytest.mark.django_db
def test_change_password_success(client):
    user = UserFactory(login_id="TESTUSER05", password="OldPassword123!", role=Role.HOSTELER)
    client.login(username="TESTUSER05", password="OldPassword123!")

    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "change_password",
            "old_password": "OldPassword123!",
            "new_password1": "SuperSecureNewPassword999!",
            "new_password2": "SuperSecureNewPassword999!",
        },
        follow=True,
    )
    assert response.status_code == 200
    content = response.content.decode()

    # Success message displayed
    assert "Your password has been changed successfully." in content

    # Password form is closed after successful redirect
    assert "passwordOpen: false" in content

    # User's password is now securely updated
    user.refresh_from_db()
    assert user.check_password("SuperSecureNewPassword999!") is True
    assert user.check_password("OldPassword123!") is False

    # User is still authenticated in session
    assert int(client.session["_auth_user_id"]) == user.pk


@pytest.mark.django_db
def test_profile_update_still_works(client):
    user = UserFactory(
        login_id="TESTUSER06",
        password="Password123!",
        full_name="Original Name",
        email="orig@example.com",
        phone="1111111111",
        role=Role.HOSTELER,
    )
    client.login(username="TESTUSER06", password="Password123!")

    response = client.post(
        reverse("accounts:profile"),
        {
            "action": "update_profile",
            "full_name": "Updated Full Name",
            "email": "updated@example.com",
            "phone": "9999888877",
        },
        follow=True,
    )
    assert response.status_code == 200
    content = response.content.decode()

    assert "Profile updated successfully." in content
    user.refresh_from_db()
    assert user.full_name == "Updated Full Name"
    assert user.email == "updated@example.com"
    assert user.phone == "9999888877"
