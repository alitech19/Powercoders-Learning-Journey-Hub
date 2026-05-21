from django import forms

from accounts.models import User

from .models import Task, TaskComment, TaskUpdate

DUE_DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})


class StudentTaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'priority', 'due_date')
        widgets = {
            'due_date': DUE_DATE_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('status',)


class SubtaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'assignee', 'priority', 'due_date')
        widgets = {
            'due_date': DUE_DATE_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].required = False
        self.fields['due_date'].required = False
        self.fields['assignee'].queryset = User.objects.filter(is_active=True).order_by(
            'display_name'
        )


class TaskUpdateForm(forms.ModelForm):
    class Meta:
        model = TaskUpdate
        fields = ('update_type', 'text')


class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'cols': 60}),
        }


class GroupTaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'assignee', 'priority', 'due_date')
        widgets = {
            'due_date': DUE_DATE_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].required = False
        self.fields['due_date'].required = False
        self.fields['assignee'].queryset = User.objects.filter(is_active=True).order_by(
            'display_name'
        )
