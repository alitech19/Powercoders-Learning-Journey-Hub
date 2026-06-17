from django import forms

from .models import SlackWorkspaceConfig


class SlackWorkspaceSettingsForm(forms.ModelForm):
    oauth_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                'class': 'w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm',
                'placeholder': 'Leave blank to keep current secret',
                'autocomplete': 'new-password',
            },
        ),
        label='OAuth client secret',
    )
    webhook_url = forms.URLField(
        required=False,
        widget=forms.URLInput(
            attrs={
                'class': 'w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-mono',
                'placeholder': 'https://hooks.slack.com/services/… (leave blank to keep current)',
            },
        ),
        label='Incoming webhook URL',
    )
    bot_token = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                'class': 'w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-mono',
                'placeholder': 'xoxb-… (leave blank to keep current)',
                'autocomplete': 'new-password',
            },
        ),
        label='Bot token',
    )
    signing_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                'class': 'w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-mono',
                'placeholder': 'Leave blank to keep current',
                'autocomplete': 'new-password',
            },
        ),
        label='Signing secret',
    )

    class Meta:
        model = SlackWorkspaceConfig
        fields = (
            'oauth_enabled',
            'oauth_client_id',
            'oauth_redirect_uri',
            'webhook_enabled',
            'chat_sync_enabled',
        )
        widgets = {
            'oauth_enabled': forms.CheckboxInput(
                attrs={'class': 'rounded border-gray-300 text-[#B23149]'},
            ),
            'webhook_enabled': forms.CheckboxInput(
                attrs={'class': 'rounded border-gray-300 text-[#B23149]'},
            ),
            'chat_sync_enabled': forms.CheckboxInput(
                attrs={'class': 'rounded border-gray-300 text-[#B23149]'},
            ),
            'oauth_client_id': forms.TextInput(
                attrs={
                    'class': 'w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-mono',
                },
            ),
            'oauth_redirect_uri': forms.URLInput(
                attrs={
                    'class': 'w-full border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-mono',
                },
            ),
        }

    def save_secrets(self, instance: SlackWorkspaceConfig) -> None:
        secret = (self.cleaned_data.get('oauth_client_secret') or '').strip()
        if secret:
            instance.set_oauth_client_secret(secret)
        webhook = (self.cleaned_data.get('webhook_url') or '').strip()
        if webhook:
            instance.set_webhook_url(webhook)
        bot = (self.cleaned_data.get('bot_token') or '').strip()
        if bot:
            instance.set_bot_token(bot)
        signing = (self.cleaned_data.get('signing_secret') or '').strip()
        if signing:
            instance.set_signing_secret(signing)
