from django import forms

from accounts.models import User
from cohorts.models import Cohort, Group

from .models import Task, TaskComment, TaskUpdate

DUE_DATE_WIDGET = forms.DateInput(attrs={'type': 'date'})


class StudentTaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False


class TeacherPersonalTaskCreateForm(forms.ModelForm):
    assigned_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Assigned user',
    )

    class Meta:
        model = Task
        fields = ('assigned_user', 'title', 'description', 'visibility', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False
        if teacher:
            from .permissions import get_teacher_accessible_students
            students = get_teacher_accessible_students(teacher)
            self.fields['assigned_user'].queryset = (
                User.objects.filter(pk=teacher.pk) | students
            ).distinct().order_by('display_name')


class TeacherGroupTaskCreateForm(forms.ModelForm):
    assigned_group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label='Assigned group',
    )

    class Meta:
        model = Task
        fields = ('assigned_group', 'title', 'description', 'visibility', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False
        if teacher:
            from .permissions import get_teacher_accessible_groups
            self.fields['assigned_group'].queryset = get_teacher_accessible_groups(teacher)


class TeacherCohortTaskCreateForm(forms.ModelForm):
    assigned_cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.none(),
        label='Assigned cohort',
    )

    class Meta:
        model = Task
        fields = ('assigned_cohort', 'title', 'description', 'visibility', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False
        if teacher:
            from .permissions import get_teacher_accessible_cohorts
            self.fields['assigned_cohort'].queryset = get_teacher_accessible_cohorts(teacher)


class TaskEditForm(forms.ModelForm):
    """Used by owner to edit an existing task."""
    class Meta:
        model = Task
        fields = ('title', 'description', 'visibility', 'priority', 'status', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False
        if self.instance and self.instance.parent_id:
            del self.fields['visibility']


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('status',)


class SubtaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'priority', 'due_date')
        widgets = {'due_date': DUE_DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].required = False


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
