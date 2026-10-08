from django import forms
from django.contrib.auth import authenticate

from apps.accounts.models import User
from apps.hostels.models import Hostel, Room


class LoginForm(forms.Form):
    login_id = forms.CharField(
        label="Roll No / Employee ID",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. ROLL202601 or EMP001",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "••••••••",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        login_id = cleaned_data.get("login_id")
        password = cleaned_data.get("password")

        if login_id and password:
            clean_id = login_id.strip()
            # Support case-insensitive Login ID / Roll No / Email lookup
            matched_user = None
            if "@" in clean_id:
                matched_user = User.objects.filter(email__iexact=clean_id).first()
            else:
                matched_user = User.objects.filter(login_id__iexact=clean_id).first()

            if matched_user:
                user = authenticate(username=matched_user.login_id, password=password)
            else:
                user = authenticate(username=clean_id, password=password)

            if not user:
                raise forms.ValidationError("Invalid Roll No / Employee ID or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self.user = user
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email", "phone"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }


class ResidenceForm(forms.Form):
    hostel = forms.ModelChoiceField(
        queryset=Hostel.objects.filter(is_active=True),
        empty_label="Select hostel",
        widget=forms.Select(attrs={"class": "form-select", "id": "residence-hostel-select"}),
    )
    floor = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "residence-floor-input"}),
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        empty_label="Select room",
        widget=forms.Select(attrs={"class": "form-select", "id": "residence-room-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hostel_id = None
        floor_val = None
        if self.data:
            hostel_id = self.data.get("hostel")
            floor_val = self.data.get("floor")
        elif self.initial:
            hostel_id = self.initial.get("hostel")
            floor_val = self.initial.get("floor")

        if hostel_id:
            qs = Room.objects.filter(hostel_id=hostel_id, is_active=True)
            if floor_val:
                qs = qs.filter(floor=floor_val)
            self.fields["room"].queryset = qs
        else:
            self.fields["room"].queryset = Room.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        hostel = cleaned_data.get("hostel")
        room = cleaned_data.get("room")
        floor = cleaned_data.get("floor")

        if hostel and room and room.hostel_id != hostel.id:
            self.add_error("room", f"Room '{room.room_number}' does not belong to {hostel.code}.")
        if floor and room and str(room.floor) != str(floor):
            self.add_error("room", f"Room '{room.room_number}' is not on floor {floor}.")

        return cleaned_data


class HostelerRegistrationForm(forms.Form):
    full_name = forms.CharField(
        label="Full Name",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Oyaan Ahmed ", "autofocus": True}),
    )
    login_id = forms.CharField(
        label="Regd Number",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 24E118B08 (optional)",
                
            }
        ),
    )
    email = forms.EmailField(
        label="Email Address",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "e.g. chandanho222@gmail.com (optional)"}),
    )
    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 7608088181 (optional)"}),
    )
    hostel = forms.ModelChoiceField(
        label="Hostel",
        queryset=Hostel.objects.filter(is_active=True),
        empty_label="Select hostel",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_hostel"}),
    )
    floor = forms.ChoiceField(
        label="Floor",
        choices=[("", "Select floor"), ("1", "Floor 1"), ("2", "Floor 2"), ("3", "Floor 3")],
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_floor"}),
    )
    room = forms.ModelChoiceField(
        label="Room",
        queryset=Room.objects.none(),
        empty_label="Select room",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_room"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "At least 8 characters"}),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Re-enter password"}),
    )
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_website", "autocomplete": "off"}),
    )
    ts_token = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_ts_token"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.hostels.services import natural_sort_key
        self.fields["hostel"].queryset = Hostel.objects.filter(is_active=True)
        # Order hostels naturally
        self.fields["hostel"].choices = [
            (h.id, f"{h.code} ({h.name})")
            for h in sorted(Hostel.objects.filter(is_active=True), key=natural_sort_key)
        ]
        self.fields["hostel"].choices.insert(0, ("", "Select hostel"))

        hostel_id = None
        floor_val = None
        if self.data:
            hostel_id = self.data.get("hostel")
            floor_val = self.data.get("floor")

        if hostel_id:
            qs = Room.objects.filter(hostel_id=hostel_id, is_active=True)
            if floor_val:
                qs = qs.filter(floor=floor_val)
            self.fields["room"].queryset = qs.order_by("floor", "room_number")
        else:
            self.fields["room"].queryset = Room.objects.none()

    def clean_login_id(self):
        login_id = (self.cleaned_data.get("login_id") or "").strip().upper()
        if login_id and User.objects.filter(login_id__iexact=login_id).exists():
            raise forms.ValidationError(f"Roll number '{login_id}' is already registered.")
        return login_id

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(f"Email '{email}' is already in use.")
        return email

    def clean_phone(self):
        return (self.cleaned_data.get("phone") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get("password")
        cpw = cleaned_data.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")

        hostel = cleaned_data.get("hostel")
        room = cleaned_data.get("room")
        if hostel and room and room.hostel_id != hostel.id:
            self.add_error("room", f"Room {room.room_number} does not belong to {hostel.code}.")

        return cleaned_data

