from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.tickets.views import trash_list_view
from apps.tickets.views.settings import manage_settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls", namespace="core")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("tickets/", include("apps.tickets.urls", namespace="tickets")),
    path("community/", include("apps.tickets.community_urls", namespace="community")),
    path("announcements/", include("apps.announcements.urls", namespace="announcements")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("manage/settings/", manage_settings, name="manage_settings"),
    path("manage/trash/", trash_list_view, name="manage_trash"),
    path("manage/", include("apps.hostels.urls", namespace="hostels")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
