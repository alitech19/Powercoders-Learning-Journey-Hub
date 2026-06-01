from django import forms
from django.core.exceptions import ValidationError

from config.input_limits import RESOURCE_LABEL_MAX_LENGTH, TITLE_MAX_LENGTH

from .models import ResourceContainer, ResourceItem


_INPUT = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#C0392B] focus:border-[#C0392B]'
)


class ResourceContainerForm(forms.ModelForm):
    class Meta:
        model = ResourceContainer
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': _INPUT,
                'maxlength': TITLE_MAX_LENGTH,
                'placeholder': 'Container name',
            }),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise ValidationError('Name is required.')
        return title


class ResourceItemForm(forms.ModelForm):
    class Meta:
        model = ResourceItem
        fields = ['title', 'url']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': _INPUT,
                'maxlength': RESOURCE_LABEL_MAX_LENGTH,
                'placeholder': 'Resource name',
            }),
            'url': forms.URLInput(attrs={
                'class': _INPUT,
                'placeholder': 'https://…',
            }),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise ValidationError('Name is required.')
        return title

    def clean_url(self):
        url = (self.cleaned_data.get('url') or '').strip()
        if not url:
            raise ValidationError('URL is required.')
        if url.startswith('/'):
            return url
        if not url.startswith(('http://', 'https://')):
            raise ValidationError('URL must start with http:// or https://.')
        return url
