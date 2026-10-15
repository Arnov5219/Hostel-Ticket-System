from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


class RequireResidenceMiddleware:
    """
    Blocks authenticated hostelers who do not have a completed residence
    (Hostel, Block, Room) from accessing pages other than onboarding, logout,
    theme settings, cascading options, and static/media.
    """

    ALLOWED_PATH_PREFIXES = (
        "/accounts/onboarding/",
        "/accounts/logout/",
        "/accounts/theme/",
        "/hostels/options/",
        "/manage/options/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, "is_hosteler", False)
            and not getattr(request.user, "has_residence", False)
        ):
            path = request.path
            is_allowed = any(path.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES)
            if not is_allowed:
                onboarding_url = reverse("accounts:onboarding")
                if request.headers.get("HX-Request") == "true":
                    response = HttpResponse(status=200)
                    response["HX-Redirect"] = onboarding_url
                    return response
                return redirect(onboarding_url)

        return self.get_response(request)


class EnforcePasswordChangeAndSessionMiddleware:
    """
    Security enforcement for staff and hostelers:
    1. Immediate session termination on session_version mismatch or deactivation/archival.
    2. Enforces password change when must_change_password=True.
    """

    ALLOWED_PATH_PREFIXES = (
        "/accounts/password/change/",
        "/accounts/logout/",
        "/accounts/login/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 1. Deactivated or archived user check
            if not request.user.is_active or getattr(request.user, "archived_at", None):
                from django.contrib.auth import logout
                from django.contrib import messages
                logout(request)
                messages.error(request, "Your account is deactivated. Contact your administrator.")
                return redirect("accounts:login")

            # 2. Session version check
            sess_version = request.session.get("session_version")
            user_version = getattr(request.user, "session_version", 1) or 1
            if sess_version is not None and sess_version != user_version:
                from django.contrib.auth import logout
                from django.contrib import messages
                logout(request)
                messages.warning(request, "Your session has expired due to account changes. Please log in again.")
                return redirect("accounts:login")
            elif sess_version is None:
                request.session["session_version"] = user_version

            # 3. Must change password check
            if getattr(request.user, "must_change_password", False):
                path = request.path
                if not any(path.startswith(prefix) for prefix in self.ALLOWED_PATH_PREFIXES):
                    change_url = reverse("accounts:password_change")
                    if request.headers.get("HX-Request") == "true":
                        response = HttpResponse(status=200)
                        response["HX-Redirect"] = change_url
                        return response
                    return redirect(change_url)

        return self.get_response(request)
