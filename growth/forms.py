from django import forms
from django.utils import timezone

from .models import Feedback, Goal, WeeklyReflection

DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = (
            'title', 'specific', 'measurable', 'achievable',
            'relevant', 'time_bound', 'visibility',
        )
        widgets = {'time_bound': DATE_WIDGET}
        labels = {
            'visibility': 'Visibility',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['visibility'].choices = [
            (Goal.Visibility.PRIVATE, 'Private'),
            (Goal.Visibility.PUBLIC, 'Share with teaching team'),
        ]

    def clean_time_bound(self):
        time_bound = self.cleaned_data.get('time_bound')
        if time_bound and not self.instance.pk:
            if time_bound < timezone.now().date():
                raise forms.ValidationError(
                    'Time-bound date cannot be in the past for a new goal.'
                )
        return time_bound


class ReflectionForm(forms.ModelForm):
    class Meta:
        model = WeeklyReflection
        fields = (
            'week_start', 'week_end',
            'more_of', 'less_of', 'start_doing',
            'stop_doing', 'continue_doing',
        )
        widgets = {
            'week_start': DATE_WIDGET,
            'week_end': DATE_WIDGET,
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._student = student

    def clean(self):
        cleaned = super().clean()
        week_start = cleaned.get('week_start')
        week_end = cleaned.get('week_end')

        if week_start and week_end and week_end <= week_start:
            self.add_error('week_end', 'Week end must be after week start.')

        agile_fields = [
            cleaned.get('more_of', ''),
            cleaned.get('less_of', ''),
            cleaned.get('start_doing', ''),
            cleaned.get('stop_doing', ''),
            cleaned.get('continue_doing', ''),
        ]
        if not any(f.strip() for f in agile_fields):
            raise forms.ValidationError(
                'At least one reflection field must be filled.'
            )

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


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'cols': 60}),
        }
