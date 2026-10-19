from django.urls import path

from apps.accounts import staff_views
from apps.hostels import views

app_name = "hostels"

urlpatterns = [
    path("hostels/", views.manage_hostels, name="manage_hostels"),
    path("hostels/<int:hostel_id>/change-responsible/", views.change_responsible_staff_view, name="change_responsible_staff"),
    path("hostels/<int:hostel_id>/toggle-status/", views.toggle_hostel_status_view, name="toggle_hostel_status"),
    path("responsibility/", views.manage_responsibility, name="manage_responsibility"),
    path("staff/", staff_views.staff_list_view, name="manage_staff"),
    path("staff/new/", staff_views.create_staff_view, name="create_staff"),
    path("staff/<int:user_id>/edit/", staff_views.edit_staff_view, name="edit_staff"),
    path("staff/<int:user_id>/login-id/", staff_views.change_login_id_view, name="change_login_id"),
    path("staff/<int:user_id>/reset-password/", staff_views.reset_password_view, name="reset_password"),
    path("staff/<int:user_id>/deactivate/", staff_views.deactivate_staff_view, name="deactivate_staff"),
    path("staff/<int:user_id>/reactivate/", staff_views.reactivate_staff_view, name="reactivate_staff"),
    path("staff/<int:user_id>/delete/", staff_views.archive_staff_view, name="archive_staff"),
    path("staff/<int:user_id>/reassign-preview/", staff_views.reassign_preview_view, name="reassign_preview"),
    path("staff/<int:user_id>/assign-hostel/", views.assign_staff_hostel_view, name="assign_staff_hostel"),
    path("staff/<int:user_id>/toggle-status/", views.toggle_staff_status_view, name="toggle_staff_status"),
]
