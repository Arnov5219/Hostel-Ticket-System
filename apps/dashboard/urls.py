from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_index, name="index"),
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/by-category/", views.api_by_category, name="api_by_category"),
    path("api/trend/", views.api_trend, name="api_trend"),
    path("api/resolution-time/", views.api_resolution_time, name="api_resolution_time"),
]
