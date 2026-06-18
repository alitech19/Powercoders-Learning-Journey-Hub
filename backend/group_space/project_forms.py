from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from cohorts.models import Cohort, Group
from cohorts.permissions import get_active_students_for_cohort, get_active_students_for_group
from config.input_limits import TITLE_MAX_LENGTH

from tasks.services import resolve_assignee_target, resolve_student_ids

from .models import ProjectSpace, ProjectSpaceMembership

_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
)


class ProjectSpaceForm(forms.ModelForm):
    class Meta:
        model = ProjectSpace
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'Project title',
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': _INPUT_CLASS,
                'placeholder': 'Optional description',
            }),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('Title is required.')
        if len(title) > TITLE_MAX_LENGTH:
            raise forms.ValidationError('Title is too long.')
        return title


class ProjectMemberAddForm(forms.Form):
    user_id = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Teacher',
        widget=forms.Select(attrs={'class': _INPUT_CLASS}),
    )

    def __init__(self, *args, project_space=None, **kwargs):
        self.project_space = project_space
        super().__init__(*args, **kwargs)
        member_ids = set()
        if project_space is not None:
            member_ids = set(project_space.memberships.values_list('user_id', flat=True))
        self.fields['user_id'].queryset = (
            User.objects.filter(is_active=True, role=User.Role.TEACHER)
            .exclude(pk__in=member_ids)
            .order_by('display_name', 'email')
        )

    def clean_user_id(self):
        user = self.cleaned_data['user_id']
        if self.project_space and self.project_space.memberships.filter(user=user).exists():
            raise forms.ValidationError('This user is already a member.')
        return user

    @property
    def membership_role(self):
        return ProjectSpaceMembership.Role.MODERATOR


def get_project_member_picker_context(project_space: ProjectSpace) -> dict:
    cohorts = Cohort.objects.filter(status=Cohort.Status.ACTIVE).order_by('-start_date', 'name')
    groups = Group.objects.select_related('cohort').filter(
        cohort__status=Cohort.Status.ACTIVE,
    ).order_by('cohort__name', 'name')
    member_ids = set(project_space.memberships.values_list('user_id', flat=True))

    def _student_rows(students):
        return [
            {'id': student.pk, 'name': student.display_name}
            for student in students
            if student.pk not in member_ids
        ]

    cohort_students = {
        str(cohort.pk): _student_rows(get_active_students_for_cohort(cohort))
        for cohort in cohorts
    }
    group_students = {
        str(group.pk): _student_rows(get_active_students_for_group(group))
        for group in groups
    }
    has_addable_students = any(cohort_students.values()) or any(group_students.values())
    return {
        'cohorts': cohorts,
        'groups': groups,
        'cohort_students_json': cohort_students,
        'group_students_json': group_students,
        'has_addable_students': has_addable_students,
    }


@transaction.atomic
def add_project_members_from_post(*, project_space: ProjectSpace, user, post) -> int:
    assignee_type = post.get('assignee_type')
    target_id = post.get('assignee_target_id')
    if assignee_type not in ('cohort', 'group'):
        raise ValidationError('Select cohort or group.')
    if not target_id:
        raise ValidationError('Select a cohort or group.')

    cohort, group = resolve_assignee_target(assignee_type, target_id)
    student_ids = resolve_student_ids(post, assignee_type=assignee_type, cohort=cohort, group=group)
    if not student_ids:
        raise ValidationError('Select at least one student.')

    students = list(
        User.objects.filter(
            pk__in=student_ids,
            role=User.Role.STUDENT,
            is_active=True,
        )
    )
    if len(students) != len(student_ids):
        raise ValidationError('One or more selected students are invalid.')

    existing = set(project_space.memberships.values_list('user_id', flat=True))
    new_students = [student for student in students if student.pk not in existing]
    if not new_students:
        raise ValidationError('All selected students are already members.')

    ProjectSpaceMembership.objects.bulk_create([
        ProjectSpaceMembership(
            project_space=project_space,
            user=student,
            role=ProjectSpaceMembership.Role.MEMBER,
            added_by=user,
        )
        for student in new_students
    ])
    return len(new_students)
