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
from .notifications.form_choices import (
    QUIET_HOURS_CHOICES,
    TIMEZONE_CHOICES,
    format_quiet_hour,
    parse_optional_quiet_hour,
)
from .notifications.settings import get_notification_settings, sync_email_enabled


_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
)
_SELECT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 '
    'bg-white dark:bg-gray-900 text-sm text-[#343534] dark:text-gray-100 '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149] '
    'max-h-48 overflow-y-auto'
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
            'in_app_enabled',
            'email_enabled',
            'slack_enabled',
            'digest_mode',
            'notify_feedback',
            'email_feedback',
            'slack_feedback',
            'notify_new_task',
            'email_new_task',
            'slack_new_task',
            'notify_new_goal',
            'email_new_goal',
            'slack_new_goal',
            'notify_new_workflow',
            'email_new_workflow',
            'slack_new_workflow',
            'notify_deadline_reminder',
            'email_deadline_reminder',
            'slack_deadline_reminder',
            'notify_group_chat_mentions',
            'email_group_chat_mentions',
            'slack_group_chat_mentions',
            'notify_group_chat_all_messages',
            'email_group_chat_all_messages',
            'slack_group_chat_all_messages',
            'quiet_hours_start',
            'quiet_hours_end',
            'timezone',
        ]
        labels = {
            'digest_mode': 'Email and Slack delivery',
        }
        help_texts = {
            'digest_mode': 'How often email and Slack notifications are delivered.',
        }

    _EVENT_CHECKBOX_CLASS = (
        'notif-event-cb h-5 w-5 rounded border-2 border-gray-300 dark:border-gray-500 '
        'text-[#B23149] focus:ring-2 focus:ring-[#B23149] focus:ring-offset-1 cursor-pointer '
        'accent-[#B23149]'
    )

    def __init__(self, *args, slack_connected=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.slack_connected = slack_connected
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                continue
            if name in ('email_enabled', 'slack_enabled', 'in_app_enabled'):
                continue
            field.widget.attrs.setdefault('class', self._EVENT_CHECKBOX_CLASS)
            if name.startswith('email_'):
                field.widget.attrs['data-notif-channel'] = 'email'
            elif name.startswith('slack_'):
                field.widget.attrs['data-notif-channel'] = 'slack'
            elif name.startswith('notify_'):
                field.widget.attrs['data-notif-channel'] = 'in_app'
        self.fields['quiet_hours_start'] = forms.ChoiceField(
            choices=QUIET_HOURS_CHOICES,
            required=False,
            label=self.fields['quiet_hours_start'].label,
            widget=forms.Select(attrs={'class': _SELECT_CLASS, 'size': 1}),
        )
        self.fields['quiet_hours_end'] = forms.ChoiceField(
            choices=QUIET_HOURS_CHOICES,
            required=False,
            label=self.fields['quiet_hours_end'].label,
            widget=forms.Select(attrs={'class': _SELECT_CLASS, 'size': 1}),
        )
        self.fields['timezone'] = forms.ChoiceField(
            choices=TIMEZONE_CHOICES,
            label=self.fields['timezone'].label,
            widget=forms.Select(attrs={'class': _SELECT_CLASS, 'size': 1}),
        )
        if self.instance.pk:
            self.initial['quiet_hours_start'] = format_quiet_hour(self.instance.quiet_hours_start)
            self.initial['quiet_hours_end'] = format_quiet_hour(self.instance.quiet_hours_end)
        if not slack_connected:
            self.initial['slack_enabled'] = False
        self.fields['digest_mode'].widget.attrs.setdefault('class', _INPUT_CLASS)

    def clean_quiet_hours_start(self):
        return parse_optional_quiet_hour(self.cleaned_data.get('quiet_hours_start'))

    def clean_quiet_hours_end(self):
        return parse_optional_quiet_hour(self.cleaned_data.get('quiet_hours_end'))

    def clean(self):
        cleaned_data = super().clean()
        if not self.slack_connected:
            cleaned_data['slack_enabled'] = False
            for name in list(cleaned_data):
                if name.startswith('slack_') and name != 'slack_enabled':
                    cleaned_data[name] = False
        return cleaned_data

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
