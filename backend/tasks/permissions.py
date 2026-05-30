"""Task access control — hardcoded business rules."""

from django.db.models import Q

from accounts.models import User
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_staff, user_is_teacher

from .models import Task, TaskEnrollment


def is_staff_assigned(task):
    return task.author_id is None


def is_personal_task(task):
    return task.author_id is not None


def get_enrollment_for_user(user, task):
    if not user.is_authenticated:
        return None
    return task.enrollments.filter(student=user).first()


def _teacher_supervises_student(user, student):
    if not student or not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


def _staff_private_draft():
    return Q(author__isnull=True) & Q(visibility=Task.Visibility.PRIVATE)


def _student_in_teacher_groups(student, teacher_group_ids):
    return bool(student and student.group_id and student.group_id in teacher_group_ids)


def can_view_task_metadata(user, task):
    """Status, priority, dates — may hide title/body for private student tasks."""
    if can_view_task_content(user, task):
        return True
    if user_is_admin(user):
        return True
    if (
        is_personal_task(task)
        and task.visibility == Task.Visibility.PRIVATE
        and user_is_teacher(user)
        and task.assignee_user_id
    ):
        return _student_in_teacher_groups(task.assignee_user, get_teacher_group_ids(user))
    if is_staff_assigned(task) and user_is_teacher(user):
        if task.is_group_shared and task.assignee_group_id in get_teacher_group_ids(user):
            return True
        return task.enrollments.filter(
            student__group_id__in=get_teacher_group_ids(user),
        ).exists()
    return False


def can_view_task(user, task):
    return can_view_task_metadata(user, task)


def can_view_task_content(user, task):
    if not user.is_authenticated:
        return False

    if is_personal_task(task):
        if task.assignee_user_id == user.pk:
            return True
        if task.visibility == Task.Visibility.PRIVATE:
            return False
        if user_is_teacher(user):
            return _teacher_supervises_student(user, task.assignee_user)
        if user_is_admin(user):
            return True
        return False

    if task.is_group_shared:
        if user_is_admin(user):
            return True
        if user_is_teacher(user):
            return task.assignee_group_id in get_teacher_group_ids(user)
        if user.role == User.Role.STUDENT:
            if task.visibility == Task.Visibility.PRIVATE:
                return False
            return user.group_id == task.assignee_group_id
        return False

    enrollment = get_enrollment_for_user(user, task)
    if user.role == User.Role.STUDENT:
        if not enrollment:
            return False
        if task.visibility == Task.Visibility.PRIVATE:
            return False
        return True

    if user_is_admin(user):
        if task.visibility == Task.Visibility.SHARED:
            return True
        return task.visibility == Task.Visibility.PRIVATE

    if user_is_teacher(user):
        in_scope = task.enrollments.filter(
            student__group_id__in=get_teacher_group_ids(user),
        ).exists()
        if not in_scope:
            return False
        if task.visibility == Task.Visibility.PRIVATE:
            return True
        return True

    return False


def can_manage_task(user, task):
    if not can_view_task(user, task):
        return False
    if user_is_admin(user):
        return True
    if is_staff_assigned(task):
        if user_is_teacher(user):
            if task.is_group_shared:
                return task.assignee_group_id in get_teacher_group_ids(user)
            return task.enrollments.filter(
                student__group_id__in=get_teacher_group_ids(user),
            ).exists()
        return False
    return task.author_id == user.pk


def can_edit_task(user, task):
    return can_manage_task(user, task)


def can_delete_task(user, task):
    return can_manage_task(user, task)


def can_edit_task_fields(user, task):
    """Title/description — staff-assigned blocks students."""
    if not can_manage_task(user, task):
        return False
    if user.role == User.Role.STUDENT and is_staff_assigned(task):
        return False
    return True


def can_change_status(user, task, enrollment=None):
    if not can_view_task_content(user, task):
        return False
    if task.is_group_shared:
        if user_is_admin(user):
            return True
        if user_is_teacher(user):
            return task.assignee_group_id in get_teacher_group_ids(user)
        if user.role == User.Role.STUDENT:
            return user.group_id == task.assignee_group_id
        return False
    if not enrollment:
        enrollment = get_enrollment_for_user(user, task)
    if not enrollment:
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def can_add_update(user, task, enrollment=None):
    if not task.allow_updates:
        return False
    if task.is_group_shared:
        return False
    if not enrollment:
        enrollment = get_enrollment_for_user(user, task)
    if not enrollment or not can_view_task_content(user, task):
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def can_comment(user, task, enrollment=None):
    if not task.allow_comments:
        return False
    if task.is_group_shared:
        return False
    if not enrollment:
        enrollment = get_enrollment_for_user(user, task)
    if not enrollment or not can_view_task_content(user, task):
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def can_toggle_subtasks(user, enrollment):
    if not task_allows_subtasks(enrollment.task):
        return False
    if not can_view_task_content(user, enrollment.task):
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def can_toggle_subtask(user, enrollment, subtask):
    if not can_toggle_subtasks(user, enrollment):
        return False
    return True


def can_add_participant_subtask(user, task, enrollment=None):
    if not task.allow_subtasks:
        return False
    if task.is_group_shared:
        return False
    if not enrollment:
        enrollment = get_enrollment_for_user(user, task)
    if not enrollment or not can_view_task_content(user, task):
        return False
    if user_is_admin(user):
        return True
    return enrollment.student_id == user.pk


def task_allows_subtasks(task):
    return task.allow_subtasks


def task_allows_updates(task):
    return task.allow_updates


def task_allows_comments(task):
    return task.allow_comments


def can_create_tasks(user):
    return user.is_authenticated and (
        user.role == User.Role.STUDENT or user_is_staff(user)
    )


def can_add_enrollment(user, task):
    if not is_staff_assigned(task) or task.is_group_shared:
        return False
    if not can_manage_task(user, task):
        return False
    return user_is_staff(user)


def get_visible_tasks_for_user(user):
    qs = (
        Task.objects.select_related(
            'author',
            'created_by',
            'assignee_user',
            'assignee_group',
            'assignee_group__cohort',
            'assignee_cohort',
        )
        .prefetch_related('subtasks', 'enrollments__student')
    )

    if user.role == User.Role.STUDENT:
        enrolled = Q(enrollments__student=user) & ~_staff_private_draft()
        group_shared = Q(
            assignee_type=Task.AssigneeType.GROUP,
            assignee_group_id=user.group_id,
            visibility=Task.Visibility.SHARED,
        )
        return qs.filter(enrolled | group_shared).distinct()

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        if not group_ids:
            return qs.none()
        in_scope = Q(enrollments__student__group_id__in=group_ids)
        group_tasks = Q(assignee_type=Task.AssigneeType.GROUP, assignee_group_id__in=group_ids)
        personal_shared = Q(
            author__isnull=False,
            visibility=Task.Visibility.SHARED,
            assignee_user__group_id__in=group_ids,
        )
        personal_private = Q(
            author__isnull=False,
            visibility=Task.Visibility.PRIVATE,
            assignee_user__group_id__in=group_ids,
        )
        staff_visible = in_scope & (
            Q(visibility=Task.Visibility.SHARED) | _staff_private_draft()
        )
        return qs.filter(staff_visible | group_tasks | personal_shared | personal_private).distinct()

    if user_is_admin(user):
        return qs.filter(
            Q(visibility=Task.Visibility.SHARED)
            | _staff_private_draft()
            | Q(author__isnull=False)
        ).distinct()

    return qs.none()


def get_visible_enrollments_for_user(user, *, task=None):
    qs = TaskEnrollment.objects.select_related('task', 'student', 'student__group')
    if task is not None:
        if not can_view_task(user, task):
            return qs.none()
        qs = qs.filter(task=task)
    if user.role == User.Role.STUDENT:
        return qs.filter(student=user)
    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        return qs.filter(student__group_id__in=group_ids)
    if user_is_admin(user):
        return qs
    return qs.none()
