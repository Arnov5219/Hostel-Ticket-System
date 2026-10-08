from django.urls import path

from apps.tickets import community_views

app_name = "community"

urlpatterns = [
    path("", community_views.feed_page, name="feed"),
    path("feed/", community_views.feed_partial, name="feed_partial"),
    path("similar/", community_views.similar_issues, name="similar"),
    path("comments/<int:comment_id>/hide/", community_views.hide_comment_view, name="hide_comment"),
    path("<str:ticket_no>/hide/", community_views.hide_ticket_view, name="hide_ticket"),
]
