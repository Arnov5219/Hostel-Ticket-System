from django.urls import path

from apps.tickets import community_views

app_name = "community"

urlpatterns = [
    path("", community_views.feed_page, name="feed"),
    path("feed/", community_views.feed_partial, name="feed_partial"),
    path("similar/", community_views.similar_issues, name="similar"),
    path("comments/<int:comment_id>/delete/", community_views.delete_comment_view, name="delete_comment"),
    path("comments/<int:comment_id>/reporter-hide/", community_views.reporter_hide_comment_view, name="reporter_hide_comment"),
    path("comments/<int:comment_id>/report/", community_views.report_comment_view, name="report_comment"),
]
