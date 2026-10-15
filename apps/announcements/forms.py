from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.models import Role
from apps.announcements.models import (
    Announcement,
    AnnouncementSeverity,
)
from apps.hostels.models import Hostel
from apps.tickets.models import Ticket


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            "title",
            "body",
            "kind",
            "severity",
            "all_hostels",
            "hostels",
            "is_pinned",
            "publish_at",
            "expires_at",
            "attachment",
            "related_ticket",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Announcement headline...",
                    "maxlength": 150,
                    "x-model": "title",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 6,
                    "maxlength": 2000,
                    "placeholder": "Detailed message, guidelines, or instructions...",
                    "x-model": "body",
                    "@input": "charsLeft = 2000 - $event.target.value.length",
                }
            ),
            "kind": forms.Select(attrs={"class": "form-select", "x-model": "kind"}),
            "severity": forms.HiddenInput(attrs={"x-model": "severity"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_pinned": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "publish_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "expires_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "all_hostels": forms.CheckboxInput(
                attrs={"class": "form-check-input", "x-model": "allHostels"}
            ),
            "hostels": forms.SelectMultiple(attrs={"class": "form-select"}),
            "related_ticket": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if not self.initial.get("severity"):
            self.initial["severity"] = AnnouncementSeverity.INFO

        # Restrict hostel choices and all_hostels for Wardens
        if user and user.role == Role.WARDEN:
            if user.hostel:
                self.fields["hostels"].queryset = Hostel.objects.filter(id=user.hostel.id)
                self.fields["hostels"].initial = [user.hostel]
            else:
                self.fields["hostels"].queryset = Hostel.objects.none()
            self.fields["all_hostels"].disabled = True
            self.fields["all_hostels"].initial = False
        else:
            self.fields["hostels"].queryset = Hostel.objects.filter(is_active=True)

        self.fields["related_ticket"].queryset = Ticket.objects.all()[:100]
        self.fields["related_ticket"].required = False
        self.fields["publish_at"].required = False
        self.fields["expires_at"].required = False
        self.fields["attachment"].required = False

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment:
            max_size = 5 * 1024 * 1024  # 5 MB
            if attachment.size > max_size:
                raise ValidationError("Attachment exceeds maximum allowed size of 5 MB.")
            valid_exts = (".pdf", ".png", ".jpg", ".jpeg", ".webp")
            if not attachment.name.lower().endswith(valid_exts):
                raise ValidationError("Only PDF, PNG, JPG, or WEBP attachments are supported.")
        return attachment

    def clean(self):
        cleaned_data = super().clean()
        user = self.user
        all_hostels = cleaned_data.get("all_hostels")
        hostels = cleaned_data.get("hostels")

        if user and user.role == Role.WARDEN:
            if all_hostels:
                raise ValidationError("Wardens cannot publish announcements to all hostels.")
            if hostels and user.hostel:
                for h in hostels:
                    if h.id != user.hostel.id:
                        raise ValidationError("Wardens can only publish to their assigned hostel.")
            elif not user.hostel:
                raise ValidationError("You do not have an assigned hostel.")

        if not all_hostels and not hostels:
            raise ValidationError("Please select at least one hostel or select 'All hostels'.")

        return cleaned_data
