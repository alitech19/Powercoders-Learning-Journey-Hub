"""
Task access control — hardcoded business rules.

Owner = created_by: can edit/delete/manage.
Assignee = assignee_user/group/cohort: can view public tasks, change status, comment, update.
Private = only owner sees it (no exceptions, not even admin).
Public = owner + assignee + admin see it.

Do NOT use user.has_perm() or Django auth Groups for task visibility.
"""

from django.db.models import Q

from accounts.models import User
from cohorts.models import GroupTeacher

from .models import Task


# --- Role helpers ---

def user_is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'role', None) == User.Role.ADMIN
    )


def user_is_teacher(user):
    return user.is_authenticated and getattr(user, 'role', None) == User.Role.TEACHER


def user_is_student(user):
    return user.is_authenticated and getattr(user, 'role', None) == User.Role.STUDENT


def get_teacher_group_ids(user):
    if not user.is_authenticated:
        return []
    return list(
        GroupTeacher.objects.filter(teacher=user).values_list('group_id', flat=True)
    )


def get_teacher_cohort_ids(user):
    from cohorts.models import Group
    group_ids = get_teacher_group_ids(user)
    if not group_ids:
        return []
    return list(
        Group.objects.filter(pk__in=group_ids).values_list('cohort_id', flat=True).distinct()
    )


def get_teacher_accessible_students(user):
    group_ids = get_teacher_group_ids(user)
    if not group_ids:
        return User.objects.none()
    return User.objects.filter(
        is_active=True, role=User.Role.STUDENT, group_id__in=group_ids
    ).order_by('display_name')


def get_teacher_accessible_groups(user):
    from cohorts.models import Group
    group_ids = get_teacher_group_ids(user)
    return Group.objects.filter(pk__in=group_ids).select_related('cohort')


def get_teacher_accessible_cohorts(user):
    from cohorts.models import Cohort
    cohort_ids = get_teacher_cohort_ids(user)
    return Cohort.objects.filter(pk__in=cohort_ids)


# --- Core permission checks ---

def is_task_owner(user, task):
    return user.is_authenticated and task.created_by_id == user.pk


def is_task_assignee(user, task):
    """Is the user (or their group/cohort) the assignee of this task?"""
    if not user.is_authenticated:
        return False
    if task.assignee_type == Task.AssigneeType.USER:
        return task.assignee_user_id == user.pk
    if task.assignee_type == Task.AssigneeType.GROUP:
        return user.group_id is not None and user.group_id == task.assignee_group_id
    if task.assignee_type == Task.AssigneeType.COHORT:
        return user.cohort_id is not None and user.cohort_id == task.assignee_cohort_id
    return False


def can_view_task(user, task):
    """
    Private: only owner.
    Public: owner + assignee + admin.
    """
    if not user.is_authenticated:
        return False
    if is_task_owner(user, task):
        return True
    if task.is_private:
        return False
    # Public task
    if user_is_admin(user):
        return True
    return is_task_assignee(user, task)


def can_view_task_content(user, task):
    """Same as can_view_task — if you can see it, you see full content."""
    return can_view_task(user, task)


def can_update_task(user, task):
    """Edit title, description, priority, visibility, due_date, assignee."""
    return is_task_owner(user, task)


def can_delete_task(user, task):
    return is_task_owner(user, task)


def can_change_task_status(user, task):
    """Owner or assignee (if they can view) can change status."""
    if is_task_owner(user, task):
        return True
    if task.is_public and is_task_assignee(user, task):
        return True
    return False


def can_comment_on_task(user, task):
    return can_view_task(user, task)


def can_add_update_to_task(user, task):
    return can_view_task(user, task)


def can_create_subtask(user, task):
    """Only owner can add subtasks (and task must not already be a subtask)."""
    if task.parent_id is not None:
        return False
    return is_task_owner(user, task)


# --- Creation permissions ---

def can_create_personal_task(user):
    return user_is_student(user) or user_is_teacher(user)


def can_create_personal_task_for_user(user, target_user):
    if not user.is_authenticated:
        return False
    if user_is_student(user):
        return target_user.pk == user.pk
    if user_is_teacher(user):
        if target_user.pk == user.pk:
            return True
        if target_user.role != User.Role.STUDENT:
            return False
        group_ids = get_teacher_group_ids(user)
        return bool(target_user.group_id and target_user.group_id in group_ids)
    return False


def can_create_group_task(user, group):
    if user_is_admin(user):
        return True
    if user_is_teacher(user):
        return group.pk in get_teacher_group_ids(user)
    return False


def can_create_cohort_task(user, cohort):
    if user_is_admin(user):
        return True
    if user_is_teacher(user):
        return cohort.pk in get_teacher_cohort_ids(user)
    return False


# --- Queryset helper ---

def get_visible_tasks_for_user(user, *, main_tasks_only=True):
    """
    Private: only tasks where created_by=user.
    Public: tasks where user is owner, assignee, or admin.
    """
    qs = Task.objects.select_related(
        'created_by', 'assignee_user', 'assignee_group', 'assignee_cohort',
    )
    if main_tasks_only:
        qs = qs.filter(parent__isnull=True)

    # Owner always sees own tasks (private + public)
    conditions = Q(created_by=user)

    # Public tasks visible to admin
    if user_is_admin(user):
        conditions |= Q(visibility=Task.Visibility.PUBLIC)
        return qs.filter(conditions).distinct()

    # Public tasks assigned to user
    conditions |= Q(
        visibility=Task.Visibility.PUBLIC,
        assignee_type=Task.AssigneeType.USER,
        assignee_user=user,
    )

    # Public tasks assigned to user's group
    if user.group_id:
        conditions |= Q(
            visibility=Task.Visibility.PUBLIC,
            assignee_type=Task.AssigneeType.GROUP,
            assignee_group_id=user.group_id,
        )

    # Public tasks assigned to user's cohort
    if user.cohort_id:
        conditions |= Q(
            visibility=Task.Visibility.PUBLIC,
            assignee_type=Task.AssigneeType.COHORT,
            assignee_cohort_id=user.cohort_id,
        )

    return qs.filter(conditions).distinct()


def wrap_tasks_for_display(user, tasks):
    """Attach template-friendly permission flags."""
    wrapped = []
    for task in tasks:
        wrapped.append({
            'task': task,
            'can_view_content': can_view_task(user, task),
            'can_update': can_update_task(user, task),
            'can_delete': can_delete_task(user, task),
            'can_change_status': can_change_task_status(user, task),
            'display_title': task.title,
        })
    return wrapped
