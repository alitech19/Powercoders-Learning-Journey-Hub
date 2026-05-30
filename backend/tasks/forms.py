from django import forms

from .models import Task, TaskComment, TaskEnrollment, TaskUpdate


class TaskForm(forms.ModelForm):
    status = forms.ChoiceField(choices=Task.Status.choices, required=False)

    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'priority',
            'due_date',
            'visibility',
            'allow_updates',
            'allow_comments',
            'allow_subtasks',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, enrollment=None, show_status=True, show_toggles=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['due_date'].required = False
        if not show_status:
            self.fields.pop('status')
        elif enrollment is not None:
            self.fields['status'].initial = enrollment.status
        if not show_toggles:
            for field in ('allow_updates', 'allow_comments', 'allow_subtasks'):
                self.fields.pop(field, None)


class TaskUpdateForm(forms.ModelForm):
    class Meta:
        model = TaskUpdate
        fields = ['update_type', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4}),
        }


class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }


class ParticipantSubtaskForm(forms.Form):
    title = forms.CharField(max_length=255)
