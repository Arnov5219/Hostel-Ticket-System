from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel
from apps.tickets.models import (
    Category,
    CommentScope,
    Priority,
    RoutingRule,
    SLAPolicy,
    Tag,
    Ticket,
    TicketComment,
    TicketVisibility,
)


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


class TicketCreateForm(forms.ModelForm):
    different_hostel = forms.BooleanField(
        required=False,
        initial=False,
        label="This issue is in a different hostel",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_different_hostel"}),
    )

    class Meta:
        model = Ticket
        fields = [
            "title",
            "category",
            "priority",
            "description",
            "hostel",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief summary of the issue...",
                    "autofocus": True,
                }
            ),
            "category": forms.Select(attrs={"class": "form-select", "id": "id_category"}),
            "priority": forms.HiddenInput(),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Say exactly where the problem is (for example washroom or corridor)...",
                }
            ),
            "hostel": forms.Select(attrs={"class": "form-select", "id": "id_hostel"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["hostel"].queryset = Hostel.objects.filter(is_active=True)
        self.fields["hostel"].required = True

        if user and user.is_authenticated and user.hostel:
            self.fields["hostel"].initial = user.hostel

        if not self.initial.get("priority"):
            self.initial["priority"] = Priority.MEDIUM

    def clean_hostel(self):
        hostel = self.cleaned_data.get("hostel")
        if hostel and not hostel.is_active:
            raise ValidationError("Cannot create tickets for an inactive hostel.")
        return hostel

    def clean(self):
        cleaned_data = super().clean()
        hostel = cleaned_data.get("hostel")

        if not hostel:
            self.add_error("hostel", "Please select a hostel.")

        different_hostel = cleaned_data.get("different_hostel", False)
        outside_own_hostel = False
        if getattr(self, "user", None) and getattr(self.user, "hostel", None):
            if hostel and hostel != self.user.hostel:
                outside_own_hostel = True
        elif different_hostel:
            outside_own_hostel = True

        cleaned_data["outside_own_hostel"] = outside_own_hostel
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.visibility = TicketVisibility.PRIVATE
        instance.room = None
        instance.location_detail = ""
        instance.outside_own_hostel = self.cleaned_data.get("outside_own_hostel", False)
        instance.show_reporter_name = False
        instance.base_priority = instance.priority
        if commit:
            instance.save()
        return instance

    def clean_images(self, files):
        uploaded_files = files.getlist("images")
        if len(uploaded_files) > 3:
            raise ValidationError("You can upload a maximum of 3 images.")

        valid_extensions = (".jpg", ".jpeg", ".png", ".webp")
        max_size = 5 * 1024 * 1024  # 5 MB

        for f in uploaded_files:
            if f.size > max_size:
                raise ValidationError(f"File {f.name} exceeds the 5 MB size limit.")
            if not f.name.lower().endswith(valid_extensions):
                raise ValidationError(f"File {f.name} is not a valid image format.")

        return uploaded_files


class CommentForm(forms.ModelForm):
    is_internal = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(),
        help_text="Visible only to staff",
    )

    class Meta:
        model = TicketComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "Write a reply or status update...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["is_internal"].initial = self.instance.is_internal

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("is_internal"):
            instance.scope = CommentScope.INTERNAL
        else:
            instance.scope = CommentScope.PRIVATE
        if commit:
            instance.save()
        return instance
