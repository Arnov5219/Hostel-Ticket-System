from django import forms
from django.contrib.auth import authenticate

from apps.accounts.models import User


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
            user = authenticate(username=login_id.strip(), password=password)
            if not user:
                raise forms.ValidationError("Invalid Roll No / Employee ID or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self.user = user
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "avatar"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
        }
