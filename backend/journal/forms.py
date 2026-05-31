from datetime import date

from django import forms

from config.input_limits import LONG_TEXT_MAX_LENGTH, TITLE_MAX_LENGTH

from .constants import (
    CONTENT_TEMPLATE,
    MOOD_CHOICES,
    TAGS_MAX_LENGTH,
    TAG_MAX_ITEM_LENGTH,
)
from .models import JournalEntry


def normalize_tags(raw):
    tags = []
    for part in (raw or '').split(','):
        tag = part.strip().lstrip('#')[:TAG_MAX_ITEM_LENGTH]
        if tag and tag not in tags:
            tags.append(tag)
    return ','.join(tags)[:TAGS_MAX_LENGTH]


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'entry_date', 'mood', 'visibility', 'tags', 'content']
        widgets = {
            'entry_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
            'mood': forms.HiddenInput(),
            'tags': forms.HiddenInput(),
            'content': forms.Textarea(attrs={'rows': 12}),
        }

    def __init__(self, *args, creating=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs.update({
            'placeholder': 'What did you learn or experience today?',
            'maxlength': TITLE_MAX_LENGTH,
        })
        self.fields['content'].widget.attrs['maxlength'] = LONG_TEXT_MAX_LENGTH
        self.fields['mood'].required = False
        self.fields['tags'].required = False
        self.fields['mood'].choices = MOOD_CHOICES
        self.fields['entry_date'].input_formats = ['%Y-%m-%d']

        if creating and not self.data:
            if not self.initial.get('entry_date'):
                self.initial['entry_date'] = date.today()
            if not self.initial.get('content'):
                self.initial['content'] = CONTENT_TEMPLATE

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('Title is required.')
        return title

    def clean_content(self):
        content = self.cleaned_data.get('content') or ''
        if not content.strip():
            raise forms.ValidationError('Content is required.')
        return content

    def clean_tags(self):
        return normalize_tags(self.cleaned_data.get('tags'))

    def clean_mood(self):
        mood = self.cleaned_data.get('mood') or ''
        valid = {value for value, _label in MOOD_CHOICES}
        return mood if mood in valid else ''
