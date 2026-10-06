from django.shortcuts import redirect, render


def home(request):
    """Redirect to dashboard if logged in, otherwise login."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return redirect("dashboard:index")


def ui_kit(request):
    """UI Kit showcase page to test all design tokens and components."""
    context = {
        "current_section": "ui-kit",
        "demo_statuses": [
            "OPEN",
            "ASSIGNED",
            "IN_PROGRESS",
            "ON_HOLD",
            "RESOLVED",
            "CLOSED",
            "ESCALATED",
            "REJECTED",
        ],
        "demo_priorities": ["URGENT", "HIGH", "MEDIUM", "LOW"],
    }
    return render(request, "core/ui_kit.html", context)
