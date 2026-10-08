from django.urls import path

from apps.announcements import views

app_name = "announcements"

urlpatterns = [
    path("", views.announcement_list, name="list"),
    path("<int:announcement_id>/", views.announcement_detail, name="detail"),
    path("<int:announcement_id>/read/", views.mark_read_endpoint, name="read"),
    path("manage/", views.manage_list, name="manage_list"),
    path("manage/new/", views.manage_create, name="manage_create"),
    path("manage/<int:announcement_id>/edit/", views.manage_edit, name="manage_edit"),
    path(
        "manage/<int:announcement_id>/<str:action>/",
        views.manage_state_action,
        name="manage_action",
    ),
]
