from django import forms

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel


class HostelForm(forms.ModelForm):
    class Meta:
        model = Hostel
        fields = ["name", "code", "gender_type", "address", "responsible_staff", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Boys Hostel A"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. BH-A"}),
            "gender_type": forms.Select(attrs={"class": "form-select"}),
            "address": forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Campus location or address..."}),
            "responsible_staff": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Responsible staff must be active Level 1 staff member
        self.fields["responsible_staff"].queryset = User.objects.filter(
            role=Role.CARETAKER,
            is_active=True,
        ).order_by("full_name", "login_id")
        self.fields["responsible_staff"].empty_label = "-- Select Responsible Staff --"
        self.fields["responsible_staff"].required = False


class ChangeResponsibleStaffForm(forms.Form):
    responsible_staff = forms.ModelChoiceField(
        queryset=User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name", "login_id"),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Responsible Level 1 Staff",
        empty_label="-- Select Level 1 Staff --",
    )


class AssignStaffHostelForm(forms.Form):
    hostel = forms.ModelChoiceField(
        queryset=Hostel.objects.filter(is_active=True).order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        label="Assigned Hostel",
        empty_label="-- No Hostel / All Hostels --",
    )
