"""
MVP visibility helpers for the tracker.

Privacy rules:
- Public task content: visible to users within scope (same group/cohort, teacher of group, admin).
- Private task content: owner/assignee only.
- Private task metadata: teachers (assigned groups) and admins — never title/description/updates/comments.
"""

from django.db.models import Q

from accounts.models import User
from cohorts.models import GroupTeacher

from .models import Task


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


def task_owner(task):
    return task.assignee or task.created_by


def _student_in_teacher_groups(student, teacher_group_ids):
    return bool(student and student.group_id and student.group_id in teacher_group_ids)


def user_can_view_task_content(user, task):
    """Full title, description, updates, comments."""
    if not user.is_authenticated:
        return False

    owner = task_owner(task)
    if owner and owner.pk == user.pk:
        return True

    if task.is_private:
        return False

    # Public task — check scope access
    if task.scope_type == Task.ScopeType.USER:
        if task.user_id == user.pk:
            return True
        if user_is_teacher(user):
            return _student_in_teacher_groups(task.user, get_teacher_group_ids(user))
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
        if user_is_admin(user):
            return True
        return False

    return False


def user_can_view_task_metadata(user, task):
    """At least status/priority/dates — may hide title and body."""
    if user_can_view_task_content(user, task):
        return True
    if user_is_admin(user):
        return True
    if task.is_private and task.is_personal and user_is_teacher(user):
        return _student_in_teacher_groups(task.user, get_teacher_group_ids(user))
    return False


def user_can_comment_on_task(user, task):
    return user_can_view_task_content(user, task)


def user_can_reply_to_comment(user, comment):
    return user_can_comment_on_task(user, comment.task)


def user_can_create_group_task(user, group):
    if user_is_admin(user):
        return True
    return group.pk in get_teacher_group_ids(user)


def user_can_edit_task_status(user, task):
    if not user_can_view_task_content(user, task):
        return False
    owner = task_owner(task)
    if owner and owner.pk == user.pk:
        return True
    if user_is_teacher(user) and task.is_public:
        if task.scope_type == Task.ScopeType.GROUP:
            return task.group_id in get_teacher_group_ids(user)
    if user_is_admin(user) and task.is_public:
        return True
    return False


def user_can_add_subtask(user, task):
    if not user_can_view_task_content(user, task):
        return False
    if task.parent_id is not None:
        return False
    owner = task_owner(task)
    return owner is not None and owner.pk == user.pk


def user_can_add_update(user, task):
    owner = task_owner(task)
    return (
        user_can_view_task_content(user, task)
        and owner is not None
        and owner.pk == user.pk
    )


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
    conditions = Q()

    # Own personal tasks (any visibility)
    conditions |= Q(scope_type=Task.ScopeType.USER, user=user)
    conditions |= Q(assignee=user) | Q(created_by=user)

    # Group public tasks
    if user.group_id:
        conditions |= Q(
            scope_type=Task.ScopeType.GROUP,
            group_id=user.group_id,
            visibility=Task.Visibility.PUBLIC,
        )

    # Cohort public tasks
    if user.cohort_id:
        conditions |= Q(
            scope_type=Task.ScopeType.COHORT,
            cohort_id=user.cohort_id,
            visibility=Task.Visibility.PUBLIC,
        )

    # Teacher: groups + student personal tasks
    if teacher_group_ids:
        conditions |= Q(
            scope_type=Task.ScopeType.GROUP,
            group_id__in=teacher_group_ids,
            visibility=Task.Visibility.PUBLIC,
        )
        conditions |= Q(
            scope_type=Task.ScopeType.USER,
            user__group_id__in=teacher_group_ids,
        )

    return qs.filter(conditions).distinct()


def wrap_tasks_for_display(user, tasks):
    """Attach template-friendly visibility flags."""
    wrapped = []
    for task in tasks:
        can_content = user_can_view_task_content(user, task)
        can_meta = user_can_view_task_metadata(user, task)
        wrapped.append(
            {
                'task': task,
                'can_view_content': can_content,
                'can_view_metadata': can_meta,
                'can_edit_status': user_can_edit_task_status(user, task),
                'display_title': (
                    task.title if can_content else 'Private task - content hidden'
                ),
            }
        )
    return wrapped
