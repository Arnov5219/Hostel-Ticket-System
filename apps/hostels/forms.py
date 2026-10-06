from django import forms

from apps.hostels.models import Block, Hostel, Room


class HostelForm(forms.ModelForm):
    class Meta:
        model = Hostel
        fields = ["name", "code", "gender_type", "address", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "gender_type": forms.Select(attrs={"class": "form-select"}),
            "address": forms.Textarea(attrs={"class": "form-textarea", "rows": 2}),
            "is_active": forms.CheckboxInput(),
        }


class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        fields = ["hostel", "name"]
        widgets = {
            "hostel": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["block", "room_number", "floor", "capacity"]
        widgets = {
            "block": forms.Select(attrs={"class": "form-select"}),
            "room_number": forms.TextInput(attrs={"class": "form-control"}),
            "floor": forms.NumberInput(attrs={"class": "form-control"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control"}),
        }
