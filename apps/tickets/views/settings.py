from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.permissions import Capability
from apps.tickets.forms import CategoryForm, CriticalityRuleForm, TagForm
from apps.tickets.models import Category, CriticalityRule, Priority, Tag


@login_required
def manage_settings(request):
    """
    Slim Ticket Settings page replacing Routing & SLA.
    Tabs:
      1. Categories (name, icon, default priority, allow in community, active)
      2. Tags
      3. Criticality rules
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

        elif action == "add_rule":
            form = CriticalityRuleForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Criticality threshold rule added.")
            else:
                messages.error(request, f"Error adding rule: {form.errors.as_text()}")
            return redirect(f"{request.path}?tab=criticality")

        elif action == "update_rule":
            rule_id = request.POST.get("rule_id")
            rule = get_object_or_404(CriticalityRule, id=rule_id)
            min_reposts = request.POST.get("min_reposts")
            bump_levels = request.POST.get("bump_levels")
            force_priority = request.POST.get("force_priority", "").strip() or None
            notify_level = request.POST.get("notify_level", "").strip() or None

            try:
                rule.min_reposts = int(min_reposts)
                rule.bump_levels = int(bump_levels)
                rule.force_priority = force_priority if force_priority in Priority.values else None
                rule.notify_level = int(notify_level) if notify_level else None
                rule.save()
                messages.success(request, f"Updated rule for {rule.min_reposts} reposts.")
            except Exception as e:
                messages.error(request, f"Error updating rule: {e}")
            return redirect(f"{request.path}?tab=criticality")

        elif action == "delete_rule":
            rule_id = request.POST.get("rule_id")
            rule = get_object_or_404(CriticalityRule, id=rule_id)
            rule.delete()
            messages.success(request, "Criticality rule deleted.")
            return redirect(f"{request.path}?tab=criticality")

        elif action == "reset_defaults":
            CriticalityRule.objects.all().delete()
            CriticalityRule.objects.create(min_reposts=3, bump_levels=1)
            CriticalityRule.objects.create(min_reposts=6, bump_levels=2)
            CriticalityRule.objects.create(min_reposts=10, force_priority=Priority.URGENT, notify_level=2)
            messages.success(request, "Default criticality rules restored.")
            return redirect(f"{request.path}?tab=criticality")

    context = {
        "current_section": "manage_settings",
        "tab": tab,
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "rules": CriticalityRule.objects.all().order_by("min_reposts"),
        "category_form": CategoryForm(),
        "tag_form": TagForm(),
        "rule_form": CriticalityRuleForm(),
        "priority_choices": Priority.choices,
    }
    return render(request, "tickets/manage_settings.html", context)
