from django import forms
from django.utils import timezone

from .models import DailyJournalEntry, Feedback, Goal, WeeklyReflection

DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})

REFLECTION_INITIAL_CONTENT = (
    'More of:\n\n'
    'Less of:\n\n'
    'Start doing:\n\n'
    'Stop doing:\n\n'
    'Continue doing:\n'
)

GOAL_DESCRIPTION_PLACEHOLDER = (
    'I want to understand how to build a small feature from start to finish: '
    'read the requirements, write the code, test the result, and explain how '
    'it works. I will know I achieved this when I can complete a simple '
    'feature without step-by-step help and describe the main decisions I '
    'made. This is realistic because I already know basic programming '
    'concepts. It is relevant because building complete features is an '
    'important skill for software development. Target date: end of this week.'
)

JOURNAL_INITIAL_CONTENT = (
    'What did I do today?\n\n'
    'What progress did I make?\n\n'
    'What blocked me?\n\n'
    'What should I do next?\n'
)


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = (
            'title', 'description', 'target_date',
            'progress_percent', 'visibility',
        )
        widgets = {
            'target_date': DATE_WIDGET,
            'description': forms.Textarea(attrs={
                'rows': 8,
                'cols': 70,
                'placeholder': GOAL_DESCRIPTION_PLACEHOLDER,
            }),
            'progress_percent': forms.NumberInput(attrs={
                'min': 0, 'max': 100, 'step': 5,
            }),
        }
        labels = {
            'visibility': 'Visibility',
            'progress_percent': 'Progress (%)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['visibility'].choices = [
            (Goal.Visibility.PRIVATE, 'Private'),
            (Goal.Visibility.PUBLIC, 'Share with teaching team'),
        ]

    def clean_target_date(self):
        target_date = self.cleaned_data.get('target_date')
        if target_date and not self.instance.pk:
            if target_date < timezone.now().date():
                raise forms.ValidationError(
                    'Target date cannot be in the past for a new goal.'
                )
        return target_date

    def clean_progress_percent(self):
        value = self.cleaned_data.get('progress_percent')
        if value is not None and (value < 0 or value > 100):
            raise forms.ValidationError(
                'Progress must be between 0 and 100.'
            )
        return value


class ReflectionForm(forms.ModelForm):
    class Meta:
        model = WeeklyReflection
        fields = ('week_start', 'week_end', 'content')
        widgets = {
            'week_start': DATE_WIDGET,
            'week_end': DATE_WIDGET,
            'content': forms.Textarea(attrs={'rows': 14, 'cols': 70}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._student = student
        if not self.instance.pk and not self.initial.get('content') and not self.data:
            self.initial['content'] = REFLECTION_INITIAL_CONTENT

    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        if not content.strip():
            raise forms.ValidationError('Content is required.')
        return content

    def clean(self):
        cleaned = super().clean()
        week_start = cleaned.get('week_start')
        week_end = cleaned.get('week_end')

        if week_start and week_end and week_end <= week_start:
            self.add_error('week_end', 'Week end must be after week start.')

        if week_start and self._student:
            qs = WeeklyReflection.objects.filter(
                student=self._student, week_start=week_start,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    'week_start',
                    'You already have a reflection for this week.',
                )

        return cleaned


class DailyJournalEntryForm(forms.ModelForm):
    class Meta:
        model = DailyJournalEntry
        fields = ('entry_date', 'content')
        widgets = {
            'entry_date': DATE_WIDGET,
            'content': forms.Textarea(attrs={'rows': 12, 'cols': 70}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._student = student
        if not self.instance.pk and not self.data:
            if not self.initial.get('entry_date'):
                self.initial['entry_date'] = timezone.now().date()
            if not self.initial.get('content'):
                self.initial['content'] = JOURNAL_INITIAL_CONTENT

    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        if not content.strip():
            raise forms.ValidationError('Content is required.')
        return content

    def clean(self):
        cleaned = super().clean()
        entry_date = cleaned.get('entry_date')

        if entry_date and self._student:
            qs = DailyJournalEntry.objects.filter(
                student=self._student, entry_date=entry_date,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    'entry_date',
                    'You already have a journal entry for this date.',
                )

        return cleaned


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'cols': 60}),
        }
