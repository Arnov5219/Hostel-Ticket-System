from django.urls import path

from apps.tickets import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("kanban/", views.ticket_kanban, name="kanban"),
    path("new/", views.ticket_create, name="create"),
    path("manage/routing/", views.manage_routing, name="manage_routing"),
]
