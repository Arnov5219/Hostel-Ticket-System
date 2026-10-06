from django.urls import path

from apps.tickets import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("kanban/", views.ticket_kanban, name="kanban"),
    path("new/", views.ticket_create, name="create"),
    path("manage/routing/", views.manage_routing, name="manage_routing"),
    path("<str:ticket_no>/", views.ticket_detail, name="detail"),
    path("<str:ticket_no>/status/", views.change_status, name="change_status"),
    path("<str:ticket_no>/move/", views.move_ticket, name="move"),
    path("<str:ticket_no>/assign/", views.reassign, name="reassign"),
    path("<str:ticket_no>/escalate/", views.manual_escalate, name="escalate"),
    path("<str:ticket_no>/comment/", views.add_comment, name="comment"),
    path("<str:ticket_no>/follow/", views.toggle_follow, name="follow"),
    path("<str:ticket_no>/rate/", views.rate_ticket, name="rate"),
]
