from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    """Login with email + password (USERNAME_FIELD on User is email)."""

    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'avatar', 'email_notifications_enabled']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False
