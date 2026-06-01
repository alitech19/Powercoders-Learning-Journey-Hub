import secrets
import string

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from cohorts.models import Cohort, Group, GroupTeacher
from cohorts.permissions import get_teacher_group_ids

from .models import User


_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#C0392B] focus:border-[#C0392B]'
)


class EmailAuthenticationForm(AuthenticationForm):
    """Login with email + password (USERNAME_FIELD on User is email)."""

    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(
            attrs={
                'autofocus': True,
                'autocomplete': 'email',
                'class': _INPUT_CLASS,
                'placeholder': 'you@example.com',
            },
        ),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'class': _INPUT_CLASS,
                'placeholder': '••••••••',
            },
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields['username'].label = 'Email address'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'avatar', 'email_notifications_enabled']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False


class CreateUserForm(forms.Form):
    email = forms.EmailField(label='Email address')
    display_name = forms.CharField(max_length=150, label='Display name')
    role = forms.ChoiceField(choices=User.Role.choices, label='Role')
    cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.none(),
        required=False,
        label='Cohort',
        empty_label='— No cohort —',
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        label='Group',
        empty_label='— No group —',
    )

    def __init__(self, *args, creator=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs.setdefault('class', _INPUT_CLASS)
        if creator and creator.role == User.Role.TEACHER:
            del self.fields['role']
            del self.fields['cohort']
            group_ids = get_teacher_group_ids(creator)
            self.fields['group'].queryset = Group.objects.filter(pk__in=group_ids).select_related(
                'cohort'
            )
        else:
            self.fields['cohort'].queryset = Cohort.objects.order_by('-start_date')
            self.fields['group'].queryset = Group.objects.select_related('cohort').order_by(
                'cohort__name', 'name'
            )

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    @staticmethod
    def generate_temp_password():
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        return ''.join(secrets.choice(alphabet) for _ in range(14))


class CohortForm(forms.ModelForm):
    class Meta:
        model = Cohort
        fields = ['name', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': _INPUT_CLASS}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': _INPUT_CLASS}),
            'name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'status': forms.Select(attrs={'class': _INPUT_CLASS}),
        }


class GroupForm(forms.ModelForm):
    teachers = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Assigned teachers',
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ['cohort', 'name']
        widgets = {
            'cohort': forms.Select(attrs={'class': _INPUT_CLASS}),
            'name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cohort'].queryset = Cohort.objects.order_by('-start_date')
        self.fields['teachers'].queryset = User.objects.filter(role=User.Role.TEACHER).order_by(
            'display_name'
        )
        if self.instance and self.instance.pk:
            assigned = GroupTeacher.objects.filter(group=self.instance).values_list(
                'teacher_id', flat=True
            )
            self.fields['teachers'].initial = list(assigned)
