from django import forms
from django.contrib.auth.forms import AuthenticationForm

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
