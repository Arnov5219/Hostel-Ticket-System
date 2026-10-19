from django import forms

from apps.accounts.models import Role, User
from apps.hostels.models import Hostel


class HostelForm(forms.ModelForm):
    class Meta:
        model = Hostel
        fields = ["name", "code", "gender_type", "responsible_staff", "responsible_warden", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Boys Hostel A"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. BH-A"}),
            "gender_type": forms.Select(attrs={"class": "form-select"}),
            "responsible_staff": forms.Select(attrs={"class": "form-select"}),
            "responsible_warden": forms.Select(attrs={"class": "form-select"}),
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

        # Responsible warden must be active Level 2 staff member
        self.fields["responsible_warden"].queryset = User.objects.filter(
            role=Role.WARDEN,
            is_active=True,
        ).order_by("full_name", "login_id")
        self.fields["responsible_warden"].empty_label = "-- Select Responsible Warden --"
        self.fields["responsible_warden"].required = False


class ChangeResponsibleStaffForm(forms.Form):
    responsible_staff = forms.ModelChoiceField(
        queryset=User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name", "login_id"),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Responsible Level 1 Staff",
        empty_label="-- Select Level 1 Staff --",
    )


class ChangeHostelAssignmentsForm(forms.Form):
    responsible_staff = forms.ModelChoiceField(
        queryset=User.objects.filter(role=Role.CARETAKER, is_active=True).order_by("full_name", "login_id"),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        label="Level 1 Caretaker",
        empty_label="-- Select Caretaker --",
    )
    responsible_warden = forms.ModelChoiceField(
        queryset=User.objects.filter(role=Role.WARDEN, is_active=True).order_by("full_name", "login_id"),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        label="Level 2 Warden",
        empty_label="-- Select Warden --",
    )


class AssignStaffHostelForm(forms.Form):
    hostel = forms.ModelChoiceField(
        queryset=Hostel.objects.filter(is_active=True).order_by("name"),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        label="Assigned Hostel",
        empty_label="-- No Hostel / All Hostels --",
    )
