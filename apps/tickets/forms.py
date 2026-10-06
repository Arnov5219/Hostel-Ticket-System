from django import forms

from apps.accounts.models import Role, User
from apps.tickets.models import Category, RoutingRule, SLAPolicy, Tag


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "icon", "default_priority", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "icon": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. zap, droplet"}
            ),
            "default_priority": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(),
        }


class SLAPolicyForm(forms.ModelForm):
    class Meta:
        model = SLAPolicy
        fields = ["priority", "level", "hours"]
        widgets = {
            "priority": forms.Select(attrs={"class": "form-select"}),
            "level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 4}),
            "hours": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }


class RoutingRuleForm(forms.ModelForm):
    class Meta:
        model = RoutingRule
        fields = ["hostel", "category", "level", "assignee"]
        widgets = {
            "hostel": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 4}),
            "assignee": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit assignee choices to staff members
        self.fields["assignee"].queryset = User.objects.filter(
            role__in=[Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.ADMIN]
        )


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
        }
