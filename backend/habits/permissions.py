"""Habit access control."""

from accounts.models import User
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher

from config.input_limits import SEARCH_QUERY_MAX_LENGTH

from .models import Habit


def _teacher_supervises_student(user, student):
    if not student or not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


def can_view_habit(user, habit):
    if not user.is_authenticated:
        return False
    if user.role == User.Role.STUDENT:
        return habit.author_id == user.pk
    if habit.visibility != Habit.Visibility.SHARED:
        return False
    if user_is_admin(user):
        return True
    if user_is_teacher(user):
        return _teacher_supervises_student(user, habit.author)
    return False


def can_edit_habit(user, habit):
    return (
        user.is_authenticated
        and habit.author_id == user.pk
        and habit.status == Habit.Status.ACTIVE
    )


def can_delete_habit(user, habit):
    return (
        user.is_authenticated
        and habit.author_id == user.pk
        and habit.status == Habit.Status.COMPLETED
    )


def can_reactivate_habit(user, habit):
    return (
        user.is_authenticated
        and habit.author_id == user.pk
        and habit.status == Habit.Status.COMPLETED
    )


def can_log_habit(user, habit):
    return (
        user.is_authenticated
        and habit.author_id == user.pk
        and habit.status == Habit.Status.ACTIVE
    )


def can_complete_habit(user, habit):
    return can_log_habit(user, habit)


def can_create_habits(user):
    return user.is_authenticated and user.role == User.Role.STUDENT


def get_visible_habits_for_user(user):
    qs = Habit.objects.select_related('author', 'author__group')

    if user.role == User.Role.STUDENT:
        return qs.filter(author=user)

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        if not group_ids:
            return qs.none()
        return qs.filter(
            visibility=Habit.Visibility.SHARED,
            author__group_id__in=group_ids,
        )

    if user_is_admin(user):
        return qs.filter(visibility=Habit.Visibility.SHARED)

    return qs.none()


def filter_habits_queryset(qs, *, search=None, student_id=None):
    if search:
        term = search.strip()[:SEARCH_QUERY_MAX_LENGTH]
        if term:
            qs = qs.filter(title__icontains=term)
    if student_id:
        qs = qs.filter(author_id=student_id)
    return qs


def order_habits_newest_first(qs):
    return qs.order_by('-created_at', '-pk')
