from django.urls import path

from apps.tickets import community_views, views

app_name = "tickets"

from apps.tickets.views.settings import manage_settings

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("kanban/", views.ticket_kanban, name="kanban"),
    path("new/", views.ticket_create, name="create"),
    path("export/csv/", views.export_tickets_csv, name="export_csv"),
    path("search-quick/", views.search_quick, name="search_quick"),
    path("bulk-action/", views.bulk_action, name="bulk_action"),
    path("filter/save/", views.save_filter, name="save_filter"),
    path("filter/<int:filter_id>/delete/", views.delete_filter, name="delete_filter"),
    path("manage/settings/", manage_settings, name="manage_settings"),
    path("manage/criticality/", manage_settings, name="manage_criticality"),
    path("trash/", views.trash_list_view, name="trash"),
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
    path("<str:ticket_no>/delete/", views.ticket_delete_view, name="delete"),
    path("<str:ticket_no>/undo-delete/", views.ticket_undo_delete_view, name="undo_delete"),
    path("<str:ticket_no>/restore/", views.ticket_restore_view, name="restore"),
]
