from django.urls import path

from apps.tickets import community_views, views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("kanban/", views.ticket_kanban, name="kanban"),
    path("new/", views.ticket_create, name="create"),
    path("export/csv/", views.export_tickets_csv, name="export_csv"),
    path("search-quick/", views.search_quick, name="search_quick"),
    path("bulk-action/", views.bulk_action, name="bulk_action"),
    path("filter/save/", views.save_filter, name="save_filter"),
    path("filter/<int:filter_id>/delete/", views.delete_filter, name="delete_filter"),
    path("manage/routing/", views.manage_routing, name="manage_routing"),
    path("manage/criticality/", views.manage_criticality, name="manage_criticality"),
    path("<str:ticket_no>/", views.ticket_detail, name="detail"),
    path("<str:ticket_no>/status/", views.change_status, name="change_status"),
    path("<str:ticket_no>/move/", views.move_ticket, name="move"),
    path("<str:ticket_no>/assign/", views.reassign, name="reassign"),
    path("<str:ticket_no>/escalate/", views.manual_escalate, name="escalate"),
    path("<str:ticket_no>/comment/", views.add_comment, name="comment"),
    path("<str:ticket_no>/repost/", community_views.toggle_repost_view, name="repost"),
    path("<str:ticket_no>/community-comments/", community_views.community_comments_view, name="community_comments"),
    path("<str:ticket_no>/follow/", views.toggle_follow, name="follow"),
    path("<str:ticket_no>/rate/", views.rate_ticket, name="rate"),
]
