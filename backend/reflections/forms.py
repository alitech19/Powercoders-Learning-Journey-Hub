from django import forms

from django.utils import timezone

from .constants import (
    CUSTOM_LABEL_MAX_LENGTH,
    EXPECTATIONS_MAX_LENGTH,
    EXPECTATIONS_TEMPLATE,
    FINAL_REFLECTION_MAX_LENGTH,
    FINAL_REFLECTION_TEMPLATE,
    MOOD_OPTIONS,
    TAG_CHOICES,
    TAG_CUSTOM,
    TITLE_MAX_LENGTH,
    WELLBEING_DIMENSIONS,
)
from .models import Reflection, expectations_is_started, final_reflection_is_started


def _sync_stage_timestamp(instance, attr, started, old_text, new_text):
    if started(new_text):
        if not getattr(instance, attr) or (old_text or '').strip() != (new_text or '').strip():
            setattr(instance, attr, timezone.now())
    else:
        setattr(instance, attr, None)


class ReflectionForm(forms.ModelForm):
    tag_weekly = forms.BooleanField(required=False, label='Weekly')
    tag_project = forms.BooleanField(required=False, label='Project')
    tag_custom = forms.BooleanField(required=False, label='Custom')

    class Meta:
        model = Reflection
        fields = [
            'title',
            'custom_label',
            'expectations',
            'final_reflection',
            'energy',
            'calmness',
            'engagement',
            'concentration',
            'sleep',
            'physical_activity',
            'visibility',
        ]
        widgets = {
            'expectations': forms.Textarea(),
            'final_reflection': forms.Textarea(),
            'custom_label': forms.TextInput(attrs={'placeholder': 'Optional label for custom tag'}),
        }

    def __init__(self, *args, creating=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs.update({
            'placeholder': 'e.g. Reflection week 7',
            'maxlength': TITLE_MAX_LENGTH,
            'class': 'w-full text-lg font-semibold border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#C0392B]/30',
        })
        self.fields['custom_label'].max_length = CUSTOM_LABEL_MAX_LENGTH
        self.fields['custom_label'].widget.attrs['maxlength'] = CUSTOM_LABEL_MAX_LENGTH
        self.fields['expectations'].widget.attrs.update({
            'maxlength': EXPECTATIONS_MAX_LENGTH,
            'rows': 6,
        })
        self.fields['final_reflection'].widget.attrs.update({
            'maxlength': FINAL_REFLECTION_MAX_LENGTH,
            'rows': 8,
        })
        for field_name in Reflection.wellbeing_field_names():
            self.fields[field_name].required = False
            self.fields[field_name].widget = forms.HiddenInput()

        if creating and not self.data:
            if not self.initial.get('expectations'):
                self.initial['expectations'] = EXPECTATIONS_TEMPLATE
            if not self.initial.get('final_reflection'):
                self.initial['final_reflection'] = FINAL_REFLECTION_TEMPLATE

        if self.instance.pk:
            tags = self.instance.tags or []
            self.fields['tag_weekly'].initial = 'weekly' in tags
            self.fields['tag_project'].initial = 'project' in tags
            self.fields['tag_custom'].initial = 'custom' in tags

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('Title is required.')
        return title

    def clean(self):
        cleaned = super().clean()
        tags = []
        if cleaned.get('tag_weekly'):
            tags.append('weekly')
        if cleaned.get('tag_project'):
            tags.append('project')
        if cleaned.get('tag_custom'):
            tags.append('custom')
        cleaned['tags'] = tags
        if 'custom' in tags and not (cleaned.get('custom_label') or '').strip():
            self.add_error('custom_label', 'Add a label when using the custom tag.')
        if not final_reflection_is_started(cleaned.get('final_reflection')):
            for field_name in Reflection.wellbeing_field_names():
                cleaned[field_name] = ''
        return cleaned

    def save(self, commit=True):
        old_expectations = self.instance.expectations if self.instance.pk else ''
        old_final = self.instance.final_reflection if self.instance.pk else ''
        instance = super().save(commit=False)
        instance.tags = self.cleaned_data.get('tags', [])
        _sync_stage_timestamp(
            instance, 'expectations_at', expectations_is_started,
            old_expectations, instance.expectations,
        )
        _sync_stage_timestamp(
            instance, 'final_reflection_at', final_reflection_is_started,
            old_final, instance.final_reflection,
        )
        if commit:
            instance.save()
        return instance


def wellbeing_form_context(form):
    """Wellbeing icon picker data for templates."""
    values = {}
    for field_name, label, hint in WELLBEING_DIMENSIONS:
        values[field_name] = form[field_name].value() or form.initial.get(field_name, '')
    final_text = form['final_reflection'].value() or form.initial.get('final_reflection', '')
    return {
        'wellbeing_dimensions': WELLBEING_DIMENSIONS,
        'mood_options': MOOD_OPTIONS,
        'wellbeing_values': values,
        'final_reflection_template': FINAL_REFLECTION_TEMPLATE.strip(),
        'final_reflection_initial': final_text,
        'final_reflection_started': final_reflection_is_started(final_text),
        'field_limits': {
            'title': TITLE_MAX_LENGTH,
            'custom_label': CUSTOM_LABEL_MAX_LENGTH,
            'expectations': EXPECTATIONS_MAX_LENGTH,
            'final_reflection': FINAL_REFLECTION_MAX_LENGTH,
        },
    }
