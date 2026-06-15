from django import forms
from django.core.exceptions import ValidationError

from config.input_limits import BODY_TEXT_MAX_LENGTH, RESOURCE_LABEL_MAX_LENGTH

from .constants import SNAPSHOT_KINDS
from .models import Comment, Post
from .services import detect_urls, validate_uploaded_file


_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
)


class ChatComposerForm(forms.ModelForm):
    """Inline message form at the bottom of the chat."""

    class Meta:
        model = Post
        fields = ['body', 'file', 'resource_label']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 2,
                'class': (
                    'w-full px-3 py-2 rounded-xl border border-gray-300 text-sm resize-none '
                    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
                ),
                'placeholder': 'Write a message… Paste a link? Open “Attach file” to name it for Resources.',
            }),
            'resource_label': forms.TextInput(attrs={
                'class': (
                    'w-full px-3 py-2 rounded-lg border border-gray-300 text-sm '
                    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
                ),
                'placeholder': 'Resource name (for links or attachments)',
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'text-xs text-gray-600',
                'accept': '.pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False
        self.fields['resource_label'].required = False
        self.fields['file'].required = False

    def clean_body(self):
        return (self.cleaned_data.get('body') or '').strip()

    def clean_resource_label(self):
        return (self.cleaned_data.get('resource_label') or '').strip()

    def clean_file(self):
        uploaded = self.cleaned_data.get('file')
        if uploaded:
            validate_uploaded_file(uploaded)
            if self.user:
                from google_storage.integration import student_must_connect_google_for_upload

                if student_must_connect_google_for_upload(self.user):
                    raise ValidationError(
                        'Connect Google Drive on your profile before attaching files.',
                    )
                from google_storage.integration import (
                    should_upload_file_to_drive,
                    staff_drive_uploads_enabled,
                )
                from accounts.models import User

                if self.user.role in (User.Role.TEACHER, User.Role.ADMIN) and not staff_drive_uploads_enabled():
                    raise ValidationError(
                        'Org file storage is not configured. Contact an admin.',
                    )
                if should_upload_file_to_drive(self.user):
                    pass
        return uploaded

    def clean(self):
        cleaned = super().clean()
        body = cleaned.get('body', '')
        uploaded = cleaned.get('file')
        label = cleaned.get('resource_label', '')

        if uploaded:
            if not label:
                raise ValidationError({
                    'resource_label': 'Give the file a name — it appears on the group Resources list.',
                })
            if body and len(body) > BODY_TEXT_MAX_LENGTH:
                raise ValidationError({'body': 'Message is too long.'})
            return cleaned

        if not body:
            raise ValidationError('Write a message or attach a file.')

        if detect_urls(body) and not label:
            raise ValidationError({
                'resource_label': 'Name this resource — it appears on the group Resources list.',
            })
        if body and len(body) > BODY_TEXT_MAX_LENGTH:
            raise ValidationError({'body': 'Message is too long.'})
        return cleaned


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['body', 'file', 'resource_label', 'pinned']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'class': _INPUT_CLASS,
                'placeholder': 'Write a message… You can paste links to resources.',
            }),
            'resource_label': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'Resource name (required if you attach a file or paste a link)',
            }),
            'file': forms.ClearableFileInput(attrs={'class': 'text-sm text-gray-600'}),
            'pinned': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300'}),
        }

    def __init__(self, *args, can_pin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False
        self.fields['resource_label'].required = False
        self.fields['file'].required = False
        if not can_pin:
            del self.fields['pinned']

    def clean_body(self):
        return (self.cleaned_data.get('body') or '').strip()

    def clean_resource_label(self):
        return (self.cleaned_data.get('resource_label') or '').strip()

    def clean_file(self):
        uploaded = self.cleaned_data.get('file')
        if uploaded:
            validate_uploaded_file(uploaded)
        return uploaded

    def clean(self):
        cleaned = super().clean()
        body = cleaned.get('body', '')
        uploaded = cleaned.get('file')
        label = cleaned.get('resource_label', '')
        has_snapshot = False
        if self.instance and self.instance.pk:
            has_snapshot = self.instance.has_snapshot

        if not body and not uploaded and not has_snapshot:
            raise ValidationError('Add a message, file, or share content from your work.')

        has_link_or_file = bool(uploaded) or bool(detect_urls(body))
        if has_link_or_file and not label:
            raise ValidationError({
                'resource_label': 'Give this resource a name — it appears on the group Resources tile.',
            })
        if label and len(label) > RESOURCE_LABEL_MAX_LENGTH:
            raise ValidationError({'resource_label': 'Name is too long.'})
        if body and len(body) > BODY_TEXT_MAX_LENGTH:
            raise ValidationError({'body': 'Message is too long.'})
        return cleaned


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Write a comment…',
            }),
        }


class ShareConfirmForm(forms.Form):
    body = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': _INPUT_CLASS,
            'placeholder': 'Optional message to go with your share…',
        }),
    )
    resource_label = forms.CharField(
        required=False,
        max_length=RESOURCE_LABEL_MAX_LENGTH,
        widget=forms.TextInput(attrs={
            'class': _INPUT_CLASS,
            'placeholder': 'Resource name (if you add a link in the message)',
        }),
    )

    def clean_body(self):
        return (self.cleaned_data.get('body') or '').strip()

    def clean_resource_label(self):
        return (self.cleaned_data.get('resource_label') or '').strip()

    def clean(self):
        cleaned = super().clean()
        body = cleaned.get('body', '')
        label = cleaned.get('resource_label', '')
        has_link = bool(detect_urls(body))
        if has_link and not label:
            raise ValidationError({
                'resource_label': 'Give the link a name for the group Resources list.',
            })
        return cleaned


class ShareKindForm(forms.Form):
    kind = forms.ChoiceField(
        choices=[
            (Post.SnapshotKind.JOURNAL, 'Journal entry'),
            (Post.SnapshotKind.HABIT, 'Habit'),
            (Post.SnapshotKind.GOAL, 'Goal'),
            (Post.SnapshotKind.TASK, 'Task'),
        ],
        widget=forms.RadioSelect,
    )

    def clean_kind(self):
        kind = self.cleaned_data['kind']
        if kind not in SNAPSHOT_KINDS:
            raise ValidationError('Invalid share type.')
        return kind
