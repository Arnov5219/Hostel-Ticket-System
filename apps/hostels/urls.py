from django.urls import path

from apps.hostels import views

app_name = "hostels"

urlpatterns = [
    path("hostels/", views.manage_hostels, name="manage_hostels"),
    path("blocks/", views.manage_blocks, name="manage_blocks"),
    path("rooms/", views.manage_rooms, name="manage_rooms"),
]
