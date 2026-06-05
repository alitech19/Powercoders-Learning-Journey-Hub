from django import forms

from config.input_limits import BODY_TEXT_MAX_LENGTH, DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH

from .models import Subtask, Task, TaskComment, TaskEnrollment, TaskUpdate


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
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs['maxlength'] = TITLE_MAX_LENGTH
        self.fields['description'].required = False
        self.fields['description'].widget.attrs['maxlength'] = DESCRIPTION_MAX_LENGTH
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs['maxlength'] = BODY_TEXT_MAX_LENGTH


class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs['maxlength'] = BODY_TEXT_MAX_LENGTH


class SubtaskForm(forms.ModelForm):
    class Meta:
        model = Subtask
        fields = ['title', 'description', 'priority', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs['maxlength'] = TITLE_MAX_LENGTH
        self.fields['description'].required = False
        self.fields['description'].widget.attrs['maxlength'] = DESCRIPTION_MAX_LENGTH
        self.fields['due_date'].required = False


