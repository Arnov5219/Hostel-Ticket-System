from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel, Room
from apps.tickets.models import (
    Category,
    CommentScope,
    CriticalityRule,
    Priority,
    RoutingRule,
    SLAPolicy,
    Tag,
    Ticket,
    TicketComment,
    TicketVisibility,
)


class CriticalityRuleForm(forms.ModelForm):
    class Meta:
        model = CriticalityRule
        fields = ["min_reposts", "bump_levels", "force_priority", "notify_level"]
        widgets = {
            "min_reposts": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "e.g. 3"}),
            "bump_levels": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 3, "placeholder": "e.g. 1"}),
            "force_priority": forms.Select(attrs={"class": "form-select"}),
            "notify_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 4, "placeholder": "e.g. 2"}),
        }


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
    share_with_community = forms.BooleanField(
        required=False,
        initial=True,
        label="Share this with other hostelers in my hostel",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_share_with_community"}),
    )
    show_reporter_name = forms.BooleanField(
        required=False,
        initial=False,
        label="Show my name",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_show_reporter_name"}),
    )
    different_hostel = forms.BooleanField(
        required=False,
        initial=False,
        label="This issue is in a different hostel",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_different_hostel"}),
    )

    floor = forms.IntegerField(required=False, widget=forms.HiddenInput(attrs={"id": "id_floor"}))

    class Meta:
        model = Ticket
        fields = [
            "title",
            "category",
            "priority",
            "description",
            "hostel",
            "room",
            "location_detail",
            "show_reporter_name",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief summary of the issue...",
                    "autofocus": True,
                    "hx-get": "/community/similar/",
                    "hx-trigger": "keyup changed delay:400ms",
                    "hx-target": "#similar-issues-target",
                    "hx-include": "#id_category",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select", "id": "id_category"}),
            "priority": forms.HiddenInput(),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Provide detailed description of the problem, exact physical location (room/floor/corridor), symptoms...",
                }
            ),
            "hostel": forms.Select(attrs={"class": "form-select", "id": "id_hostel"}),
            "room": forms.Select(attrs={"class": "form-select", "id": "id_room"}),
            "location_detail": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "id_location_detail",
                    "placeholder": "e.g. 2nd floor washroom (optional)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["hostel"].queryset = Hostel.objects.filter(is_active=True)
        self.fields["hostel"].required = True
        self.fields["room"].required = True

        hostel_id = None
        floor_val = None
        if self.data:
            hostel_id = self.data.get("hostel")
            floor_val = self.data.get("floor")
        elif user and user.is_authenticated:
            if user.hostel:
                self.fields["hostel"].initial = user.hostel
                hostel_id = user.hostel_id
            if getattr(user, "room", None) and user.room:
                self.fields["room"].initial = user.room
                self.fields["floor"].initial = user.room.floor
                floor_val = user.room.floor

        if hostel_id:
            room_qs = Room.objects.filter(hostel_id=hostel_id, is_active=True)
            if floor_val:
                room_qs = room_qs.filter(floor=floor_val)
            self.fields["room"].queryset = room_qs
        else:
            self.fields["room"].queryset = Room.objects.none()

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
        room = cleaned_data.get("room")
        floor = cleaned_data.get("floor")

        if not hostel:
            self.add_error("hostel", "Please select a hostel.")
        if not room:
            self.add_error("room", "Select your room.")

        if hostel and room:
            from apps.tickets.services.location import validate_location
            try:
                h, r, outside = validate_location(
                    hostel.id,
                    room.id,
                    reporter=getattr(self, "user", None),
                    floor=floor,
                )
                cleaned_data["hostel"] = h
                cleaned_data["room"] = r
                cleaned_data["outside_own_hostel"] = outside
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for field, msgs in e.message_dict.items():
                        for msg in msgs:
                            self.add_error(field, msg)
                else:
                    self.add_error(None, str(e.message if hasattr(e, "message") else e))

        cat = cleaned_data.get("category")
        if cat and not cat.allow_community:
            cleaned_data["share_with_community"] = False
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        cat = self.cleaned_data.get("category")
        share = self.cleaned_data.get("share_with_community")
        if share and (not cat or cat.allow_community):
            instance.visibility = TicketVisibility.HOSTEL
        else:
            instance.visibility = TicketVisibility.PRIVATE

        instance.room = self.cleaned_data.get("room")
        instance.location_detail = self.cleaned_data.get("location_detail", "")
        instance.outside_own_hostel = self.cleaned_data.get("outside_own_hostel", False)
        instance.show_reporter_name = bool(self.cleaned_data.get("show_reporter_name"))
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
        elif instance.scope == CommentScope.INTERNAL:
            instance.scope = CommentScope.PRIVATE
        if commit:
            instance.save()
        return instance
