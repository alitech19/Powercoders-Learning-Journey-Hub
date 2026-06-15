from django import forms

from .models import GoogleWorkspaceStorageConfig


class WorkspaceStorageSettingsForm(forms.ModelForm):
    """Admin storage settings — secrets optional on edit (leave blank to keep)."""

    service_account_json = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 6,
                'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono',
                'placeholder': 'Paste service account JSON (leave blank to keep current)',
            },
        ),
        label='Service account JSON',
    )
    oauth_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm',
                'placeholder': 'Leave blank to keep current secret',
                'autocomplete': 'new-password',
            },
        ),
        label='OAuth client secret',
    )

    class Meta:
        model = GoogleWorkspaceStorageConfig
        fields = (
            'is_enabled',
            'shared_drive_id',
            'shared_drive_name',
            'shared_root_folder_id',
            'root_folder_name',
            'student_oauth_enabled',
            'oauth_client_id',
            'oauth_redirect_uri',
            'workspace_hosted_domain',
        )
        widgets = {
            'is_enabled': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-[#B23149]'}),
            'student_oauth_enabled': forms.CheckboxInput(
                attrs={'class': 'rounded border-gray-300 text-[#B23149]'},
            ),
            'shared_drive_id': forms.TextInput(
                attrs={'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm'},
            ),
            'shared_drive_name': forms.TextInput(
                attrs={'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm'},
            ),
            'shared_root_folder_id': forms.TextInput(
                attrs={
                    'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50',
                    'readonly': True,
                },
            ),
            'root_folder_name': forms.TextInput(
                attrs={'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm'},
            ),
            'oauth_client_id': forms.TextInput(
                attrs={'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm'},
            ),
            'oauth_redirect_uri': forms.URLInput(
                attrs={'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono'},
            ),
            'workspace_hosted_domain': forms.TextInput(
                attrs={
                    'class': 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm',
                    'placeholder': 'powercoders.org',
                },
            ),
        }

    def save_secrets(self, instance: GoogleWorkspaceStorageConfig) -> None:
        raw_json = (self.cleaned_data.get('service_account_json') or '').strip()
        if raw_json:
            instance.set_service_account_json(raw_json)
        secret = (self.cleaned_data.get('oauth_client_secret') or '').strip()
        if secret:
            instance.set_oauth_client_secret(secret)
