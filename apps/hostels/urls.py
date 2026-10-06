from django.urls import path

from apps.hostels import views

app_name = "hostels"

urlpatterns = [
    path("manage/hostels/", views.manage_hostels, name="manage_hostels"),
]
