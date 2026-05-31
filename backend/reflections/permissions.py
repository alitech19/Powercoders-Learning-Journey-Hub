"""Reflection access control."""

from django.db.models import DateTimeField
from django.db.models.functions import Coalesce

from accounts.models import User
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher

from config.input_limits import SEARCH_QUERY_MAX_LENGTH
from .models import Reflection


def _teacher_supervises_student(user, student):
    if not student or not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


def can_view_reflection(user, reflection):
    if not user.is_authenticated:
        return False
    if user.role == User.Role.STUDENT:
        return reflection.author_id == user.pk
    if reflection.visibility != Reflection.Visibility.SHARED:
        return False
    if user_is_admin(user):
        return True
    if user_is_teacher(user):
        return _teacher_supervises_student(user, reflection.author)
    return False


def can_edit_reflection(user, reflection):
    if not user.is_authenticated:
        return False
    if reflection.author_id == user.pk:
        return True
    if user_is_admin(user) and can_view_reflection(user, reflection):
        return True
    return False


def can_delete_reflection(user, reflection):
    return can_edit_reflection(user, reflection)


def can_create_reflections(user):
    return user.is_authenticated and user.role == User.Role.STUDENT


def get_visible_reflections_for_user(user):
    qs = Reflection.objects.select_related('author', 'author__group')

    if user.role == User.Role.STUDENT:
        return qs.filter(author=user)

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        if not group_ids:
            return qs.none()
        return qs.filter(
            visibility=Reflection.Visibility.SHARED,
            author__group_id__in=group_ids,
        )

    if user_is_admin(user):
        return qs.filter(visibility=Reflection.Visibility.SHARED)

    return qs.none()


def filter_reflections_queryset(qs, *, tag=None, search=None, student_id=None):
    if tag:
        qs = qs.filter(tags__contains=[tag])
    if search:
        term = search.strip()[:SEARCH_QUERY_MAX_LENGTH]
        if term:
            qs = qs.filter(title__icontains=term)
    if student_id:
        qs = qs.filter(author_id=student_id)
    return qs


def order_reflections_newest_first(qs):
    """Default list order: newest activity first (finish → start → created)."""
    return qs.order_by(
        Coalesce(
            'final_reflection_at',
            'expectations_at',
            'created_at',
            output_field=DateTimeField(),
        ).desc(nulls_last=True),
        '-updated_at',
        '-pk',
    )
