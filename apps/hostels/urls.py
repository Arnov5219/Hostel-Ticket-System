from django.urls import path

from apps.hostels import views

app_name = "hostels"

urlpatterns = [
    path("hostels/", views.manage_hostels, name="manage_hostels"),
    path("rooms/", views.manage_rooms, name="manage_rooms"),
    path("staff/", views.manage_staff, name="manage_staff"),
    path("responsibility/", views.manage_responsibility, name="manage_responsibility"),
    path("hostels/<int:hostel_id>/generate-rooms/", views.generate_rooms_view, name="generate_rooms"),
    path("hostels/<int:hostel_id>/change-responsible/", views.change_responsible_staff_view, name="change_responsible_staff"),
    path("hostels/<int:hostel_id>/toggle-status/", views.toggle_hostel_status_view, name="toggle_hostel_status"),
    path("staff/<int:user_id>/assign-hostel/", views.assign_staff_hostel_view, name="assign_staff_hostel"),
    path("staff/<int:user_id>/toggle-status/", views.toggle_staff_status_view, name="toggle_staff_status"),
    path("rooms/<int:room_id>/toggle-status/", views.toggle_room_status_view, name="toggle_room_status"),
    path("rooms/<int:room_id>/edit/", views.edit_room_view, name="edit_room"),
    path("residents/", views.manage_residents, name="manage_residents"),
    path("residents/<int:resident_id>/verify/", views.verify_resident_view, name="verify_resident"),
    path("residents/<int:resident_id>/reject/", views.reject_resident_view, name="reject_resident"),
    path("residents/<int:resident_id>/reset-password/", views.reset_resident_password_view, name="reset_resident_password"),
    path("residents/bulk-verify/", views.bulk_verify_residents_view, name="bulk_verify_residents"),
    path("options/floors/", views.options_floors_view, name="options_floors"),
    path("options/rooms/", views.options_rooms_view, name="options_rooms"),
]
