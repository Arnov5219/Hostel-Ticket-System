from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("read-all/", views.mark_all_read, name="read_all"),
    path("read/<int:notification_id>/", views.mark_read_and_redirect, name="mark_read"),
    path("poll/", views.bell_poll, name="poll"),
    path("api/list/", views.notification_api_list, name="api_list"),
]
