from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render

from apps.accounts.forms import LoginForm, ProfileUpdateForm, ResidenceForm
from apps.accounts.services import set_residence
from apps.hostels.models import Hostel


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            messages.success(request, f"Welcome back, {user.full_name or user.login_id}!")
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("dashboard:index")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST" or request.method == "GET":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def profile_view(request):
    profile_form = ProfileUpdateForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_profile":
            profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("accounts:profile")
        elif action == "change_password":
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed.")
                return redirect("accounts:profile")

    residence_form = None
    if request.user.is_hosteler:
        initial_data = {}
        if request.user.hostel_id:
            initial_data["hostel"] = request.user.hostel_id
        if request.user.room_id and request.user.room:
            initial_data["block"] = request.user.room.block_id
            initial_data["room"] = request.user.room_id
        residence_form = ResidenceForm(initial=initial_data)

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "residence_form": residence_form,
            "current_section": "profile",
        },
    )


@login_required
def onboarding_view(request):
    """
    Mandatory onboarding gate for hostelers lacking a complete residence.
    """
    if not request.user.is_hosteler:
        return redirect("dashboard:index")

    if request.user.has_residence and request.method == "GET":
        return redirect("dashboard:index")

    form = ResidenceForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            try:
                set_residence(
                    user=request.user,
                    hostel=form.cleaned_data["hostel"],
                    block=form.cleaned_data["block"],
                    room=form.cleaned_data["room"],
                    changed_by=request.user,
                )
                messages.success(request, f"Welcome to {form.cleaned_data['hostel'].name}! Your residence has been saved.")
                return redirect("dashboard:index")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, "message") else e))
        else:
            messages.error(request, "Please select a valid Hostel, Block, and Room.")

    hostels = Hostel.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "accounts/onboarding.html",
        {
            "form": form,
            "hostels": hostels,
        },
    )


@login_required
def profile_residence_view(request):
    """
    Allows hostelers to update their residence from the profile page.
    """
    if not request.user.is_hosteler and not request.user.is_admin:
        messages.error(request, "Only hostelers have assigned residences.")
        return redirect("accounts:profile")

    if request.method == "POST":
        form = ResidenceForm(request.POST)
        if form.is_valid():
            try:
                set_residence(
                    user=request.user,
                    hostel=form.cleaned_data["hostel"],
                    block=form.cleaned_data["block"],
                    room=form.cleaned_data["room"],
                    changed_by=request.user,
                )
                messages.success(request, "Your residence was updated successfully.")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, "message") else e))
        else:
            messages.error(request, "Invalid residence selection. Please ensure Block and Room match the selected Hostel.")
        return redirect("accounts:profile")

    return redirect("accounts:profile")


def change_theme_view(request):
    """
    POST /accounts/theme/ saves theme choice (SYSTEM, LIGHT, DARK).
    """
    if request.method == "POST":
        theme = request.POST.get("theme", "").upper()
        if theme in ["LIGHT", "DARK", "SYSTEM"]:
            if request.user.is_authenticated:
                request.user.theme = theme
                request.user.save(update_fields=["theme"])
            return HttpResponse(status=204)
        return HttpResponseBadRequest("Invalid theme choice")
    return HttpResponseBadRequest("POST required")
