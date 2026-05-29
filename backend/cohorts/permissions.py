"""Shared cohort/group scope helpers for staff-facing apps."""

from accounts.models import User
from cohorts.models import Cohort, Group, GroupTeacher


def user_is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'role', None) == User.Role.ADMIN
    )


def user_is_teacher(user):
    return user.is_authenticated and getattr(user, 'role', None) == User.Role.TEACHER


def user_is_student(user):
    return user.is_authenticated and getattr(user, 'role', None) == User.Role.STUDENT


def user_is_staff(user):
    return user.is_authenticated and getattr(user, 'role', None) in (
        User.Role.TEACHER,
        User.Role.ADMIN,
    )


def get_teacher_group_ids(user):
    if not user.is_authenticated:
        return []
    return list(
        GroupTeacher.objects.filter(teacher=user).values_list('group_id', flat=True)
    )


def get_teacher_cohort_ids(user):
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
        is_active=True,
        role=User.Role.STUDENT,
        group_id__in=group_ids,
    ).order_by('display_name')


def get_teacher_accessible_groups(user):
    group_ids = get_teacher_group_ids(user)
    return Group.objects.filter(pk__in=group_ids).select_related('cohort')


def get_teacher_accessible_cohorts(user):
    cohort_ids = get_teacher_cohort_ids(user)
    return Cohort.objects.filter(pk__in=cohort_ids)


def get_active_students_for_group(group):
    return User.objects.filter(
        is_active=True,
        role=User.Role.STUDENT,
        group=group,
    ).order_by('display_name')


def get_active_students_for_cohort(cohort):
    return User.objects.filter(
        is_active=True,
        role=User.Role.STUDENT,
        cohort=cohort,
        group__isnull=False,
    ).order_by('display_name')
