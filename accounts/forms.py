from django.contrib.auth.forms import AuthenticationForm
from django import forms


class EmailAuthenticationForm(AuthenticationForm):
    """Login with email + password (USERNAME_FIELD on User is email)."""

    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'
