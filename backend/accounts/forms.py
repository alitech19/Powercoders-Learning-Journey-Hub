import secrets
import string

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from config.form_widgets import configure_html5_date_field, html5_date_widget

from cohorts.models import Cohort, Group, GroupTeacher
from cohorts.permissions import get_teacher_group_ids

from .avatar_storage import AvatarUploadError, encode_upload
from .models import User, UserNotificationSettings
from .notifications.settings import get_notification_settings, sync_email_enabled


_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
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
    avatar = forms.ImageField(required=False, label='Profile photo')

    class Meta:
        model = User
        fields = ['display_name', 'email_notifications_enabled']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False

    def clean_avatar(self):
        upload = self.cleaned_data.get('avatar')
        if not upload:
            return None
        try:
            self._avatar_payload = encode_upload(upload)
        except AvatarUploadError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return upload

    def save(self, commit=True):
        user = super().save(commit=False)
        if hasattr(self, '_avatar_payload'):
            avatar_data, content_type = self._avatar_payload
            user.avatar_data = avatar_data
            user.avatar_content_type = content_type
            user.avatar_updated_at = timezone.now()
        if commit:
            user.save()
            sync_email_enabled(user, user.email_notifications_enabled)
        return user


class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = UserNotificationSettings
        fields = [
            'email_enabled',
            'notify_feedback',
            'notify_new_task',
            'notify_new_goal',
            'notify_new_workflow',
            'notify_deadline_reminder',
            'notify_group_chat_mentions',
            'notify_group_chat_all_messages',
            'slack_enabled',
        ]
        labels = {
            'notify_feedback': 'Feedback from teachers',
            'notify_new_task': 'New tasks',
            'notify_new_goal': 'New goals',
            'notify_new_workflow': 'New workflows',
            'notify_deadline_reminder': 'Deadline reminders',
            'notify_group_chat_mentions': 'Mentions in group chat',
            'notify_group_chat_all_messages': 'All group chat messages',
        }

    _CHECKBOX_CLASS = (
        'rounded border-gray-300 dark:border-gray-600 text-[#B23149] focus:ring-[#B23149]'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', self._CHECKBOX_CLASS)

    def save(self, commit=True):
        settings = super().save(commit=commit)
        if commit:
            sync_email_enabled(settings.user, settings.email_enabled)
        return settings


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
            'start_date': html5_date_widget(**{'class': _INPUT_CLASS}),
            'end_date': html5_date_widget(**{'class': _INPUT_CLASS}),
            'name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'status': forms.Select(attrs={'class': _INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configure_html5_date_field(self.fields['start_date'])
        configure_html5_date_field(self.fields['end_date'])


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
