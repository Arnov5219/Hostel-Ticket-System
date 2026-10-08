from django import forms
from django.contrib.auth import authenticate

from apps.accounts.models import User
from apps.hostels.models import Block, Hostel, Room


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


class ResidenceForm(forms.Form):
    hostel = forms.ModelChoiceField(
        queryset=Hostel.objects.filter(is_active=True),
        empty_label="Select hostel",
        widget=forms.Select(attrs={"class": "form-select", "id": "residence-hostel-select"}),
    )
    block = forms.ModelChoiceField(
        queryset=Block.objects.none(),
        empty_label="Select block",
        widget=forms.Select(attrs={"class": "form-select", "id": "residence-block-select"}),
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        empty_label="Select room",
        widget=forms.Select(attrs={"class": "form-select", "id": "residence-room-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hostel_id = None
        block_id = None
        if self.data:
            hostel_id = self.data.get("hostel")
            block_id = self.data.get("block")
        elif self.initial:
            hostel_id = self.initial.get("hostel")
            block_id = self.initial.get("block")

        if hostel_id:
            self.fields["block"].queryset = Block.objects.filter(hostel_id=hostel_id, is_active=True)
        else:
            self.fields["block"].queryset = Block.objects.none()

        if block_id:
            self.fields["room"].queryset = Room.objects.filter(block_id=block_id, is_active=True)
        else:
            self.fields["room"].queryset = Room.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        hostel = cleaned_data.get("hostel")
        block = cleaned_data.get("block")
        room = cleaned_data.get("room")

        if hostel and block and block.hostel_id != hostel.id:
            self.add_error("block", f"Block '{block.name}' does not belong to {hostel.name}.")
        if block and room and room.block_id != block.id:
            self.add_error("room", f"Room '{room.room_number}' does not belong to block '{block.name}'.")

        return cleaned_data
