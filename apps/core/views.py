from django.http import JsonResponse
from django.shortcuts import redirect, render


def health_check(request):
    """Lightweight health check endpoint for Android app and load balancers."""
    return JsonResponse({"status": "ok", "app": "Hostel Ticket System"})


def home(request):
    """Redirect to dashboard if logged in, otherwise login."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return redirect("dashboard:index")


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
