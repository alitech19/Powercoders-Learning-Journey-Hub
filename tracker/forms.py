from django import forms

from accounts.models import User

from .models import Task, TaskComment, TaskUpdate

DUE_DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})


class StudentTaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'priority', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False


class StudentTaskUpdateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False


class TeacherGroupTaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'assignee', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].required = False
        self.fields['due_date'].required = False
        if group:
            self.fields['assignee'].queryset = User.objects.filter(
                is_active=True, group=group, role=User.Role.STUDENT
            ).order_by('display_name')
        else:
            self.fields['assignee'].queryset = User.objects.none()


class TeacherCohortTaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'assignee', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, cohort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].required = False
        self.fields['due_date'].required = False
        if cohort:
            self.fields['assignee'].queryset = User.objects.filter(
                is_active=True, cohort=cohort, role=User.Role.STUDENT
            ).order_by('display_name')
        else:
            self.fields['assignee'].queryset = User.objects.none()


class TeacherTaskUpdateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'assignee', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].required = False
        self.fields['due_date'].required = False
        if task:
            if task.scope_type == Task.ScopeType.GROUP and task.group:
                self.fields['assignee'].queryset = User.objects.filter(
                    is_active=True, group=task.group, role=User.Role.STUDENT
                ).order_by('display_name')
            elif task.scope_type == Task.ScopeType.COHORT and task.cohort:
                self.fields['assignee'].queryset = User.objects.filter(
                    is_active=True, cohort=task.cohort, role=User.Role.STUDENT
                ).order_by('display_name')
            else:
                self.fields['assignee'].queryset = User.objects.none()
        else:
            self.fields['assignee'].queryset = User.objects.none()


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('status',)


class SubtaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'assignee', 'priority', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, parent_task=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].required = False
        self.fields['due_date'].required = False
        if parent_task and parent_task.scope_type == Task.ScopeType.GROUP and parent_task.group:
            self.fields['assignee'].queryset = User.objects.filter(
                is_active=True, group=parent_task.group, role=User.Role.STUDENT
            ).order_by('display_name')
        elif parent_task and parent_task.scope_type == Task.ScopeType.COHORT and parent_task.cohort:
            self.fields['assignee'].queryset = User.objects.filter(
                is_active=True, cohort=parent_task.cohort, role=User.Role.STUDENT
            ).order_by('display_name')
        elif user and parent_task and parent_task.is_personal:
            self.fields['assignee'].queryset = User.objects.filter(pk=user.pk)
        else:
            self.fields['assignee'].queryset = User.objects.filter(is_active=True).order_by('display_name')


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
