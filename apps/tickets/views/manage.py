from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.permissions import can_manage_config
from apps.tickets.forms import RoutingRuleForm
from apps.tickets.models import (
    Category,
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

    context = {
        "current_section": "manage_config",
        "tab": tab,
        "routing_rules": RoutingRule.objects.select_related("hostel", "category", "assignee").all(),
        "sla_policies": SLAPolicy.objects.all(),
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "rule_form": RoutingRuleForm(),
    }
    return render(request, "tickets/manage_routing.html", context)

