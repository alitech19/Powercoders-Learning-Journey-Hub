"""Workflow access control — hardcoded business rules."""

from django.db.models import Q

from accounts.models import User
from cohorts.permissions import (
    get_active_students_for_cohort,
    get_active_students_for_group,
    get_teacher_cohort_ids,
    get_teacher_group_ids,
    user_is_admin,
    user_is_staff,
    user_is_student,
    user_is_teacher,
)

from .models import Workflow, WorkflowEnrollment


def is_workflow_owner(user, workflow):
    return user.is_authenticated and workflow.created_by_id == user.pk


def _student_is_assigned(user, workflow):
    if not user.is_authenticated or not user_is_student(user):
        return False
    if workflow.progress_mode == Workflow.ProgressMode.SHARED:
        if workflow.assignee_type == Workflow.AssigneeType.GROUP:
            return user.group_id is not None and user.group_id == workflow.assignee_group_id
        if workflow.assignee_type == Workflow.AssigneeType.COHORT:
            return user.cohort_id is not None and user.cohort_id == workflow.assignee_cohort_id
        return False
    return WorkflowEnrollment.objects.filter(workflow=workflow, student=user).exists()


def get_workflow_assigned_students(workflow):
    if workflow.progress_mode == Workflow.ProgressMode.SHARED:
        if workflow.assignee_type == Workflow.AssigneeType.COHORT and workflow.assignee_cohort_id:
            return get_active_students_for_cohort(workflow.assignee_cohort)
        if workflow.assignee_type == Workflow.AssigneeType.GROUP and workflow.assignee_group_id:
            return get_active_students_for_group(workflow.assignee_group)
        return User.objects.none()
    return User.objects.filter(
        is_active=True,
        role=User.Role.STUDENT,
        workflow_enrollments__workflow=workflow,
    ).distinct()


def workflow_has_student_in_teacher_groups(user, workflow):
    if not user_is_teacher(user):
        return False
    group_ids = get_teacher_group_ids(user)
    if not group_ids:
        return False
    return get_workflow_assigned_students(workflow).filter(group_id__in=group_ids).exists()


def _teacher_in_workflow_scope(user, workflow):
    if not user_is_teacher(user):
        return False
    group_ids = get_teacher_group_ids(user)
    cohort_ids = get_teacher_cohort_ids(user)
    if workflow.assignee_type == Workflow.AssigneeType.GROUP:
        return workflow.assignee_group_id in group_ids
    if workflow.assignee_type == Workflow.AssigneeType.COHORT:
        return workflow.assignee_cohort_id in cohort_ids
    return False


def can_view_workflow(user, workflow):
    """
    Private = draft: staff only (admin + in-scope teachers). Students see it after release (public).
    """
    if not user.is_authenticated:
        return False
    if user_is_admin(user):
        return True
    if user_is_student(user):
        if workflow.is_private:
            return False
        return _student_is_assigned(user, workflow)
    if not user_is_staff(user):
        return False
    if is_workflow_owner(user, workflow):
        return True
    return workflow_has_student_in_teacher_groups(user, workflow) or _teacher_in_workflow_scope(
        user, workflow
    )


def can_manage_workflow(user, workflow):
    if not user.is_authenticated or not user_is_staff(user):
        return False
    if user_is_admin(user):
        return True
    return workflow_has_student_in_teacher_groups(user, workflow) or _teacher_in_workflow_scope(
        user, workflow
    )


def can_create_workflow(user):
    return user_is_staff(user)


def can_toggle_step(user, workflow):
    if workflow.is_private:
        return False
    return _student_is_assigned(user, workflow)


def can_assign_students(user, workflow, students):
    if not can_manage_workflow(user, workflow):
        return False
    if user_is_admin(user):
        return True
    group_ids = set(get_teacher_group_ids(user))
    return all(student.group_id in group_ids for student in students)


def get_visible_workflows_for_user(user):
    qs = Workflow.objects.select_related(
        'created_by', 'assignee_cohort', 'assignee_group', 'assignee_group__cohort',
    ).prefetch_related('steps', 'enrollments')

    if user_is_admin(user):
        return qs

    conditions = Q(created_by=user)

    if user_is_student(user):
        student_q = Q(visibility=Workflow.Visibility.PUBLIC) & Q(
            progress_mode=Workflow.ProgressMode.INDIVIDUAL,
            enrollments__student=user,
        )
        if user.group_id:
            student_q |= Q(
                visibility=Workflow.Visibility.PUBLIC,
                progress_mode=Workflow.ProgressMode.SHARED,
                assignee_type=Workflow.AssigneeType.GROUP,
                assignee_group_id=user.group_id,
            )
        if user.cohort_id:
            student_q |= Q(
                visibility=Workflow.Visibility.PUBLIC,
                progress_mode=Workflow.ProgressMode.SHARED,
                assignee_type=Workflow.AssigneeType.COHORT,
                assignee_cohort_id=user.cohort_id,
            )
        conditions |= student_q

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        cohort_ids = get_teacher_cohort_ids(user)
        scoped = Q()
        if group_ids:
            scoped |= Q(
                assignee_type=Workflow.AssigneeType.GROUP,
                assignee_group_id__in=group_ids,
            )
            scoped |= Q(
                progress_mode=Workflow.ProgressMode.INDIVIDUAL,
                enrollments__student__group_id__in=group_ids,
            )
        if cohort_ids:
            scoped |= Q(
                assignee_type=Workflow.AssigneeType.COHORT,
                assignee_cohort_id__in=cohort_ids,
            )
        conditions |= Q(visibility=Workflow.Visibility.PUBLIC) & scoped
        conditions |= Q(visibility=Workflow.Visibility.PRIVATE) & scoped

    return qs.filter(conditions).distinct()


def build_step_data(user, workflow, *, student=None):
    steps = list(workflow.steps.all())
    if workflow.is_shared:
        done_ids = set(
            workflow.completions.filter(student__isnull=True).values_list('step_id', flat=True)
        )
    else:
        target = student or user
        done_ids = set(
            workflow.completions.filter(student=target).values_list('step_id', flat=True)
        )

    step_data = []
    for idx, step in enumerate(steps):
        is_done = step.pk in done_ids
        locked = (
            step.requires_previous
            and idx > 0
            and steps[idx - 1].pk not in done_ids
        )
        step_data.append({'step': step, 'done': is_done, 'locked': locked})
    return step_data


def shared_progress_pct(workflow):
    total = workflow.steps.count()
    if not total:
        return 0
    done = workflow.completions.filter(student__isnull=True).count()
    return round(done / total * 100)
