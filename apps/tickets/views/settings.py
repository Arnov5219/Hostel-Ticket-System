from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.permissions import Capability
from apps.tickets.forms import CategoryForm, TagForm
from apps.tickets.models import Category, Priority, Tag


@login_required
def manage_settings(request):
    """
    Slim Ticket Settings page replacing Routing & SLA.
    Tabs:
      1. Categories (name, icon, default priority, active)
      2. Tags
    """
    if not request.user.can(Capability.MANAGE_TICKET_SETTINGS):
        raise PermissionDenied("You do not have permission to manage ticket settings.")

    tab = request.GET.get("tab", "categories")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_category":
            form = CategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f"Category '{form.cleaned_data['name']}' added.")
            else:
                messages.error(request, "Error adding category.")
            return redirect(f"{request.path}?tab=categories")

        elif action == "update_category":
            cat_id = request.POST.get("category_id")
            cat = get_object_or_404(Category, id=cat_id)
            form = CategoryForm(request.POST, instance=cat)
            if form.is_valid():
                form.save()
                messages.success(request, f"Category '{cat.name}' updated.")
            else:
                messages.error(request, "Error updating category.")
            return redirect(f"{request.path}?tab=categories")

        elif action == "delete_category":
            cat_id = request.POST.get("category_id")
            cat = get_object_or_404(Category, id=cat_id)
            name = cat.name
            cat.delete()
            messages.success(request, f"Category '{name}' deleted.")
            return redirect(f"{request.path}?tab=categories")

        elif action == "add_tag":
            form = TagForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f"Tag '{form.cleaned_data['name']}' added.")
            else:
                messages.error(request, "Error adding tag.")
            return redirect(f"{request.path}?tab=tags")

        elif action == "delete_tag":
            tag_id = request.POST.get("tag_id")
            tag = get_object_or_404(Tag, id=tag_id)
            name = tag.name
            tag.delete()
            messages.success(request, f"Tag '{name}' deleted.")
            return redirect(f"{request.path}?tab=tags")

    context = {
        "current_section": "manage_settings",
        "tab": tab,
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "category_form": CategoryForm(),
        "tag_form": TagForm(),
        "priority_choices": Priority.choices,
    }
    return render(request, "tickets/manage_settings.html", context)
