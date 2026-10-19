from django import forms
from django.contrib.auth import authenticate

from apps.accounts.models import User
from apps.hostels.models import Hostel


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


class StyledPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
        error_messages={
            "required": "Current password is required.",
        },
    )
    new_password1 = forms.CharField(
        label="New Password",
        min_length=8,
        help_text="At least 8 characters, not too common.",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "At least 8 characters",
                "autocomplete": "new-password",
                "minlength": "8",
            }
        ),
        error_messages={
            "min_length": "Password must be at least 8 characters long.",
            "required": "New password is required.",
        },
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Re-enter new password",
                "autocomplete": "new-password",
                "minlength": "8",
            }
        ),
        error_messages={
            "min_length": "Password must be at least 8 characters long.",
            "required": "Please confirm your new password.",
        },
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not old_password or not self.user.check_password(old_password):
            raise forms.ValidationError("Invalid current password. Please enter it again.")
        return old_password

    def clean(self):
        from django.contrib.auth.password_validation import validate_password

        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password1")
        p2 = cleaned_data.get("new_password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("new_password2", "The new passwords do not match.")
            else:
                try:
                    validate_password(p1, self.user)
                except forms.ValidationError as error:
                    self.add_error("new_password1", error)
        return cleaned_data

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.must_change_password = False
        if commit:
            self.user.save()
        return self.user


class ResidenceForm(forms.Form):
    hostel = forms.ModelChoiceField(
        queryset=Hostel.objects.filter(is_active=True),
        empty_label="Select hostel",
        widget=forms.Select(attrs={"class": "form-select", "id": "residence-hostel-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.hostels.services import natural_sort_key
        self.fields["hostel"].queryset = Hostel.objects.filter(is_active=True)
        self.fields["hostel"].choices = [
            (h.id, f"{h.code} ({h.name})")
            for h in sorted(Hostel.objects.filter(is_active=True), key=natural_sort_key)
        ]
        self.fields["hostel"].choices.insert(0, ("", "Select hostel"))


class HostelerRegistrationForm(forms.Form):
    full_name = forms.CharField(
        label="Full Name",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "", "autofocus": True}),
    )
    login_id = forms.CharField(
        label="Regd Number",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "",
            }
        ),
    )
    email = forms.EmailField(
        label="Email Address",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": ""}),
    )
    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": ""}),
    )
    hostel = forms.ModelChoiceField(
        label="Hostel",
        queryset=Hostel.objects.filter(is_active=True),
        empty_label="Select hostel",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_hostel"}),
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
        self.fields["hostel"].choices = [
            (h.id, f"{h.code} ({h.name})")
            for h in sorted(Hostel.objects.filter(is_active=True), key=natural_sort_key)
        ]
        self.fields["hostel"].choices.insert(0, ("", "Select hostel"))

    def clean_login_id(self):
        from django.conf import settings

        from apps.accounts.models import AllowedRollNumber

        login_id = (self.cleaned_data.get("login_id") or "").strip().upper()
        if login_id and User.objects.filter(login_id__iexact=login_id).exists():
            raise forms.ValidationError(f"Roll number '{login_id}' is already registered.")

        reg_mode = getattr(settings, "REGISTRATION_MODE", "OPEN")
        if reg_mode == "ALLOWLIST":
            if not login_id:
                raise forms.ValidationError("Roll number is required in allowlist registration mode.")
            if not AllowedRollNumber.objects.filter(roll_no__iexact=login_id, used_by__isnull=True).exists():
                raise forms.ValidationError("This roll number is not on the allowed list or has already been registered.")

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

        return cleaned_data

