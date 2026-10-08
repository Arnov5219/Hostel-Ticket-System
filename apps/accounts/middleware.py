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
