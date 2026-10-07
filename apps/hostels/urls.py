from django.urls import path

from apps.hostels import views

app_name = "hostels"

urlpatterns = [
    path("hostels/", views.manage_hostels, name="manage_hostels"),
    path("staff/", views.manage_staff, name="manage_staff"),
    path("responsibility/", views.manage_responsibility, name="manage_responsibility"),
    path("hostels/<int:hostel_id>/change-responsible/", views.change_responsible_staff_view, name="change_responsible_staff"),
    path("hostels/<int:hostel_id>/toggle-status/", views.toggle_hostel_status_view, name="toggle_hostel_status"),
    path("staff/<int:user_id>/assign-hostel/", views.assign_staff_hostel_view, name="assign_staff_hostel"),
    path("staff/<int:user_id>/toggle-status/", views.toggle_staff_status_view, name="toggle_staff_status"),
]
