from django import forms

from config.input_limits import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH

from .constants import (
    DAYS_PER_WEEK_MAX,
    DAYS_PER_WEEK_MIN,
    MINUTES_MIN,
)
from .models import Habit


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = [
            'title',
            'description',
            'target_minutes',
            'target_days_per_week',
            'visibility',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'target_minutes': forms.NumberInput(attrs={'min': MINUTES_MIN}),
            'target_days_per_week': forms.NumberInput(
                attrs={'min': DAYS_PER_WEEK_MIN, 'max': DAYS_PER_WEEK_MAX},
            ),
            'visibility': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs.update({
            'placeholder': 'e.g. Practice Python for 30 minutes',
            'maxlength': TITLE_MAX_LENGTH,
        })
        self.fields['description'].widget.attrs['maxlength'] = DESCRIPTION_MAX_LENGTH
        self.fields['target_minutes'].required = False
        self.fields['description'].required = False

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('Title is required.')
        return title

    def clean_target_minutes(self):
        value = self.cleaned_data.get('target_minutes')
        if value is not None and value < MINUTES_MIN:
            raise forms.ValidationError('Target minutes must be at least 1.')
        return value

    def clean_target_days_per_week(self):
        value = self.cleaned_data.get('target_days_per_week')
        if value is not None and (value < DAYS_PER_WEEK_MIN or value > DAYS_PER_WEEK_MAX):
            raise forms.ValidationError('Days per week must be between 1 and 7.')
        return value

    def clean_visibility(self):
        visibility = self.cleaned_data.get('visibility')
        valid = {value for value, _label in Habit.Visibility.choices}
        return visibility if visibility in valid else Habit.Visibility.PRIVATE
