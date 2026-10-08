from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.models import Role, User
from apps.tickets.models import (
    Category,
    CommentScope,
    Priority,
    RoutingRule,
    SLAPolicy,
    SubCategory,
    Tag,
    Ticket,
    TicketComment,
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
    class Meta:
        model = Ticket
        fields = [
            "title",
            "category",
            "sub_category",
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
            "category": forms.Select(attrs={"class": "form-select"}),
            "sub_category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.HiddenInput(),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Provide detailed description of the problem, exact physical location (room/floor/corridor), symptoms...",
                }
            ),
            "hostel": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["sub_category"].queryset = SubCategory.objects.none()
        self.fields["sub_category"].required = False
        self.fields["hostel"].queryset = self.fields["hostel"].queryset.filter(is_active=True)

        if "category" in self.data:
            try:
                category_id = int(self.data.get("category"))
                self.fields["sub_category"].queryset = SubCategory.objects.filter(
                    category_id=category_id
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields["sub_category"].queryset = self.instance.category.subcategories.all()

        if user and user.is_authenticated:
            if user.hostel:
                self.fields["hostel"].initial = user.hostel

        if not self.initial.get("priority"):
            self.initial["priority"] = Priority.MEDIUM

    def clean_hostel(self):
        hostel = self.cleaned_data.get("hostel")
        if hostel and not hostel.is_active:
            raise ValidationError("Cannot create tickets for an inactive hostel.")
        return hostel

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
        elif instance.scope == CommentScope.INTERNAL:
            instance.scope = CommentScope.PRIVATE
        if commit:
            instance.save()
        return instance
