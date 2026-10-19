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
            role__in=[Role.CARETAKER, Role.WARDEN, Role.CHIEF_WARDEN, Role.DEAN, Role.ADMIN]
        )


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
            "room_number",
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
            "room_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Room 204",
                    "id": "id_room_number",
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
        self.fields["room_number"].required = True
        self.fields["room_number"].error_messages["required"] = (
            "Room number is required. Please specify your room (e.g. Room 204)."
        )

        if user and user.is_authenticated and user.hostel:
            self.fields["hostel"].initial = user.hostel

        if user and user.is_authenticated and getattr(user, "room", None) and not self.initial.get("room_number"):
            self.fields["room_number"].initial = user.room.room_number

        if not self.initial.get("priority"):
            self.initial["priority"] = Priority.MEDIUM

    def clean_room_number(self):
        val = self.cleaned_data.get("room_number", "")
        if not val or not val.strip():
            raise ValidationError("Room number is required. Please specify your room (e.g. Room 204).")
        return val.strip()

    def clean_hostel(self):
        # Server-side enforcement: If the user is an authenticated hosteler with an assigned hostel,
        # always enforce their assigned hostel and ignore any forged or manipulated client value.
        if self.user and self.user.is_authenticated and self.user.is_hosteler and self.user.hostel:
            return self.user.hostel

        hostel = self.cleaned_data.get("hostel")
        if hostel and not hostel.is_active:
            raise ValidationError("Cannot create tickets for an inactive hostel.")
        return hostel

    def clean(self):
        cleaned_data = super().clean()

        # Enforce server-side rule for hostelers
        if self.user and self.user.is_authenticated and self.user.is_hosteler and self.user.hostel:
            cleaned_data["hostel"] = self.user.hostel
            cleaned_data["outside_own_hostel"] = False
            return cleaned_data

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
        instance.room_number = self.cleaned_data.get("room_number", "").strip()
        instance.location_detail = ""
        instance.outside_own_hostel = self.cleaned_data.get("outside_own_hostel", False)
        instance.show_reporter_name = False
        instance.base_priority = instance.priority

        if instance.hostel and instance.room_number:
            from apps.hostels.models import Room
            clean_rn = instance.room_number.replace("Room", "").replace("room", "").strip()
            matched_room = Room.objects.filter(
                hostel=instance.hostel,
                room_number__in=[instance.room_number, clean_rn],
            ).first()
            instance.room = matched_room
        else:
            instance.room = None

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
