from django import forms

from .models import Goal, GoalEnrollment


class GoalForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=GoalEnrollment.Status.choices,
        required=False,
    )

    class Meta:
        model = Goal
        fields = ['title', 'description', 'category', 'target_date', 'visibility']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, enrollment=None, show_status=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['target_date'].required = False
        if not show_status:
            self.fields.pop('status')
        elif enrollment is not None:
            self.fields['status'].initial = enrollment.status
