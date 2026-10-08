from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.permissions import can_manage_config
from apps.tickets.forms import CategoryForm, CriticalityRuleForm, RoutingRuleForm, TagForm
from apps.tickets.models import (
    Category,
    CriticalityRule,
    Priority,
    RoutingRule,
    SLAPolicy,
    Tag,
)


@login_required
def manage_routing(request):
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage routing and SLA rules.")

    tab = request.GET.get("tab", "routing")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_rule":
            form = RoutingRuleForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Routing rule added.")
            else:
                messages.error(request, "Error adding routing rule.")
            return redirect(f"{request.path}?tab=routing")

        elif action == "delete_rule":
            rule_id = request.POST.get("rule_id")
            rule = get_object_or_404(RoutingRule, id=rule_id)
            rule.delete()
            messages.success(request, "Routing rule deleted.")
            return redirect(f"{request.path}?tab=routing")

        elif action == "update_sla":
            policy_id = request.POST.get("policy_id")
            policy = get_object_or_404(SLAPolicy, id=policy_id)
            hours = request.POST.get("hours")
            if hours and hours.isdigit():
                policy.hours = int(hours)
                policy.save()
                messages.success(request, f"Updated {policy} to {hours}h.")
            return redirect(f"{request.path}?tab=sla")

        elif action == "add_category":
            form = CategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Category added.")
            else:
                messages.error(request, "Error adding category.")
            return redirect(f"{request.path}?tab=categories")

        elif action == "add_tag":
            form = TagForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Tag added.")
            else:
                messages.error(request, "Error adding tag.")
            return redirect(f"{request.path}?tab=tags")

    context = {
        "current_section": "manage_config",
        "tab": tab,
        "routing_rules": RoutingRule.objects.select_related("hostel", "category", "assignee").all(),
        "sla_policies": SLAPolicy.objects.all(),
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "rule_form": RoutingRuleForm(),
        "category_form": CategoryForm(),
        "tag_form": TagForm(),
    }
    return render(request, "tickets/manage_routing.html", context)


@login_required
def manage_criticality(request):
    """Admin configuration for automatic priority escalation by repost thresholds."""
    if not can_manage_config(request.user):
        raise PermissionDenied("Only administrators can manage criticality escalation rules.")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_rule":
            form = CriticalityRuleForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Criticality threshold rule added.")
            else:
                messages.error(request, f"Error adding rule: {form.errors.as_text()}")
            return redirect("tickets:manage_criticality")

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
            return redirect("tickets:manage_criticality")

        elif action == "delete_rule":
            rule_id = request.POST.get("rule_id")
            rule = get_object_or_404(CriticalityRule, id=rule_id)
            rule.delete()
            messages.success(request, "Criticality rule deleted.")
            return redirect("tickets:manage_criticality")

        elif action == "reset_defaults":
            CriticalityRule.objects.all().delete()
            CriticalityRule.objects.create(min_reposts=3, bump_levels=1)
            CriticalityRule.objects.create(min_reposts=6, bump_levels=2)
            CriticalityRule.objects.create(min_reposts=10, force_priority=Priority.URGENT, notify_level=2)
            messages.success(request, "Default criticality rules restored (3 -> +1 level, 6 -> +2 levels, 10 -> Urgent & Notify L2).")
            return redirect("tickets:manage_criticality")

    rules = CriticalityRule.objects.all().order_by("min_reposts")
    form = CriticalityRuleForm()

    context = {
        "current_section": "manage_criticality",
        "rules": rules,
        "form": form,
        "priority_choices": Priority.choices,
    }
    return render(request, "tickets/manage_criticality.html", context)

