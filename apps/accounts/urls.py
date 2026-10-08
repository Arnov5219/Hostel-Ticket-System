from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/residence/", views.profile_residence_view, name="profile_residence"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("theme/", views.change_theme_view, name="theme"),
]
