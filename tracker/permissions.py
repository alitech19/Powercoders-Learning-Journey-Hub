"""
Hardcoded business rules for task access control.

Do NOT use user.has_perm() or Django admin permissions for task privacy.
All access is determined by user.role, scope, visibility, and GroupTeacher relations.
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


def teacher_has_group_access(user, group):
    if not user_is_teacher(user):
        return False
    return group.pk in get_teacher_group_ids(user)


def teacher_has_cohort_access(user, cohort):
    if not user_is_teacher(user):
        return False
    return cohort.pk in get_teacher_cohort_ids(user)


def task_owner(task):
    return task.assignee or task.created_by


# --- Content visibility ---

def can_view_task_content(user, task):
    """Full title, description, updates, comments."""
    if not user.is_authenticated:
        return False

    owner = task_owner(task)
    if owner and owner.pk == user.pk:
        return True

    # Private personal task: only owner
    if task.is_private and task.is_personal:
        return False

    # Private group task: teacher with group access + admin
    if task.is_private and task.scope_type == Task.ScopeType.GROUP:
        if user_is_teacher(user):
            return task.group_id in get_teacher_group_ids(user)
        if user_is_admin(user):
            return True
        return False

    # Private cohort task: teacher with cohort access + admin
    if task.is_private and task.scope_type == Task.ScopeType.COHORT:
        if user_is_teacher(user):
            return task.cohort_id in get_teacher_cohort_ids(user)
        if user_is_admin(user):
            return True
        return False

    # Public task — check scope access
    if task.scope_type == Task.ScopeType.USER:
        if task.user_id == user.pk:
            return True
        if user_is_teacher(user):
            task_user = task.user
            return bool(task_user and task_user.group_id and task_user.group_id in get_teacher_group_ids(user))
        if user_is_admin(user):
            return True
        return False

    if task.scope_type == Task.ScopeType.GROUP:
        if user.group_id == task.group_id:
            return True
        if user_is_teacher(user):
            return task.group_id in get_teacher_group_ids(user)
        if user_is_admin(user):
            return True
        return False

    if task.scope_type == Task.ScopeType.COHORT:
        if user.cohort_id == task.cohort_id:
            return True
        if user_is_teacher(user):
            return task.cohort_id in get_teacher_cohort_ids(user)
        if user_is_admin(user):
            return True
        return False

    return False


def can_view_task_metadata(user, task):
    """At least status/priority/dates — may hide title and body."""
    if can_view_task_content(user, task):
        return True
    # Admin can see private personal task metadata
    if user_is_admin(user) and task.is_private and task.is_personal:
        return True
    return False


# --- CRUD permissions ---

def can_create_personal_task(user):
    return user_is_student(user)


def can_create_group_task(user, group):
    if user_is_admin(user):
        return True
    return teacher_has_group_access(user, group)


def can_create_cohort_task(user, cohort):
    if user_is_admin(user):
        return True
    return teacher_has_cohort_access(user, cohort)


def can_update_task(user, task):
    if not user.is_authenticated:
        return False
    # Student can edit own personal tasks
    if user_is_student(user):
        if task.is_personal and task.user_id == user.pk:
            return True
        return False
    # Teacher can edit group/cohort tasks in their scope
    if user_is_teacher(user):
        if task.scope_type == Task.ScopeType.GROUP:
            return task.group_id in get_teacher_group_ids(user)
        if task.scope_type == Task.ScopeType.COHORT:
            return task.cohort_id in get_teacher_cohort_ids(user)
        return False
    # Admin can edit group/cohort tasks and public personal tasks
    if user_is_admin(user):
        if task.scope_type in (Task.ScopeType.GROUP, Task.ScopeType.COHORT):
            return True
        if task.is_personal and task.is_public:
            return True
        return False
    return False


def can_delete_task(user, task):
    if not user.is_authenticated:
        return False
    # Student can delete own personal tasks
    if user_is_student(user):
        if task.is_personal and task.user_id == user.pk:
            return True
        return False
    # Teacher can delete group/cohort tasks in their scope
    if user_is_teacher(user):
        if task.scope_type == Task.ScopeType.GROUP:
            return task.group_id in get_teacher_group_ids(user)
        if task.scope_type == Task.ScopeType.COHORT:
            return task.cohort_id in get_teacher_cohort_ids(user)
        return False
    # Admin can delete group/cohort tasks
    if user_is_admin(user):
        if task.scope_type in (Task.ScopeType.GROUP, Task.ScopeType.COHORT):
            return True
        return False
    return False


def can_comment_on_task(user, task):
    return can_view_task_content(user, task)


def can_reply_to_comment(user, comment):
    return can_comment_on_task(user, comment.task)


def can_add_update_to_task(user, task):
    return can_view_task_content(user, task)


def can_create_subtask(user, parent_task):
    if not can_view_task_content(user, parent_task):
        return False
    if parent_task.parent_id is not None:
        return False
    # Owner can add subtasks
    owner = task_owner(parent_task)
    if owner and owner.pk == user.pk:
        return True
    # Teacher/admin can add subtasks to group/cohort tasks they can edit
    if parent_task.scope_type != Task.ScopeType.USER:
        return can_update_task(user, parent_task)
    return False


def can_edit_task_status(user, task):
    """Anyone who can update the task can change status."""
    if can_update_task(user, task):
        return True
    # Owner/assignee can always change status of tasks they can view
    owner = task_owner(task)
    if owner and owner.pk == user.pk and can_view_task_content(user, task):
        return True
    return False


# --- Queryset helpers ---

def visible_tasks_queryset(user, *, main_tasks_only=True):
    """Tasks the user may see in lists (full or metadata-only)."""
    qs = Task.objects.select_related(
        'user',
        'group',
        'cohort',
        'assignee',
        'created_by',
    )
    if main_tasks_only:
        qs = qs.filter(parent__isnull=True)

    if user_is_admin(user):
        return qs

    teacher_group_ids = get_teacher_group_ids(user)
    teacher_cohort_ids = get_teacher_cohort_ids(user) if teacher_group_ids else []
    conditions = Q()

    # Own personal tasks (any visibility)
    conditions |= Q(scope_type=Task.ScopeType.USER, user=user)
    conditions |= Q(assignee=user) | Q(created_by=user)

    # Student: group public tasks
    if user.group_id:
        conditions |= Q(
            scope_type=Task.ScopeType.GROUP,
            group_id=user.group_id,
            visibility=Task.Visibility.PUBLIC,
        )

    # Student: cohort public tasks
    if user.cohort_id:
        conditions |= Q(
            scope_type=Task.ScopeType.COHORT,
            cohort_id=user.cohort_id,
            visibility=Task.Visibility.PUBLIC,
        )

    # Teacher: group tasks (public + private)
    if teacher_group_ids:
        conditions |= Q(
            scope_type=Task.ScopeType.GROUP,
            group_id__in=teacher_group_ids,
        )
        # Teacher: public personal tasks of students in assigned groups
        conditions |= Q(
            scope_type=Task.ScopeType.USER,
            user__group_id__in=teacher_group_ids,
            visibility=Task.Visibility.PUBLIC,
        )

    # Teacher: cohort tasks (public + private)
    if teacher_cohort_ids:
        conditions |= Q(
            scope_type=Task.ScopeType.COHORT,
            cohort_id__in=teacher_cohort_ids,
        )

    return qs.filter(conditions).distinct()


def wrap_tasks_for_display(user, tasks):
    """Attach template-friendly visibility flags."""
    wrapped = []
    for task in tasks:
        can_content = can_view_task_content(user, task)
        can_meta = can_view_task_metadata(user, task)
        wrapped.append(
            {
                'task': task,
                'can_view_content': can_content,
                'can_view_metadata': can_meta,
                'can_edit_status': can_edit_task_status(user, task),
                'can_update': can_update_task(user, task),
                'can_delete': can_delete_task(user, task),
                'display_title': (
                    task.title if can_content else 'Private task - content hidden'
                ),
            }
        )
    return wrapped
