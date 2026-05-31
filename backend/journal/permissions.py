"""Journal access control."""

from accounts.models import User
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher

from config.input_limits import SEARCH_QUERY_MAX_LENGTH

from .models import JournalEntry


def _teacher_supervises_student(user, student):
    if not student or not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


def can_view_journal_entry(user, entry):
    if not user.is_authenticated:
        return False
    if user.role == User.Role.STUDENT:
        return entry.author_id == user.pk
    if entry.visibility != JournalEntry.Visibility.SHARED:
        return False
    if user_is_admin(user):
        return True
    if user_is_teacher(user):
        return _teacher_supervises_student(user, entry.author)
    return False


def can_edit_journal_entry(user, entry):
    return user.is_authenticated and entry.author_id == user.pk


def can_delete_journal_entry(user, entry):
    if not user.is_authenticated:
        return False
    if entry.author_id == user.pk:
        return True
    if (
        user_is_admin(user)
        and entry.visibility == JournalEntry.Visibility.SHARED
        and can_view_journal_entry(user, entry)
    ):
        return True
    return False


def can_create_journal_entries(user):
    return user.is_authenticated and user.role == User.Role.STUDENT


def get_visible_journal_entries_for_user(user):
    qs = JournalEntry.objects.select_related('author', 'author__group')

    if user.role == User.Role.STUDENT:
        return qs.filter(author=user)

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        if not group_ids:
            return qs.none()
        return qs.filter(
            visibility=JournalEntry.Visibility.SHARED,
            author__group_id__in=group_ids,
        )

    if user_is_admin(user):
        return qs.filter(visibility=JournalEntry.Visibility.SHARED)

    return qs.none()


def filter_journal_entries_queryset(qs, *, tag=None, search=None, student_id=None):
    if tag:
        term = tag.strip()[:SEARCH_QUERY_MAX_LENGTH]
        if term:
            qs = qs.filter(tags__icontains=term)
    if search:
        term = search.strip()[:SEARCH_QUERY_MAX_LENGTH]
        if term:
            qs = qs.filter(title__icontains=term)
    if student_id:
        qs = qs.filter(author_id=student_id)
    return qs


def order_journal_entries_newest_first(qs):
    return qs.order_by('-entry_date', '-created_at', '-pk')
