"""Journal feedback hooks for the generic feedback app."""

from cohorts.permissions import user_is_staff

from .models import JournalEntry
from .permissions import _teacher_supervises_student, can_view_journal_entry


def can_view_journal_feedback(user, entry):
    if user.pk == entry.author_id:
        return can_view_journal_entry(user, entry)
    if not can_view_journal_entry(user, entry):
        return False
    if user_is_staff(user):
        return _teacher_supervises_student(user, entry.author)
    return False


def can_add_journal_feedback(user, entry):
    if not user_is_staff(user):
        return False
    if entry.visibility != JournalEntry.Visibility.SHARED:
        return False
    return can_view_journal_feedback(user, entry)


def journal_feedback_context(entry, viewer):
    placeholder = 'Leave feedback for this student…'
    if viewer.pk != entry.author_id:
        placeholder = f'Leave feedback for {entry.author.display_name}…'
    return {
        'visibility_shared': entry.visibility == JournalEntry.Visibility.SHARED,
        'feedback_placeholder': placeholder,
    }


def register_journal_feedback_handlers():
    from feedback.registry import FeedbackHandlers, register

    register(
        JournalEntry,
        FeedbackHandlers(
            can_view=can_view_journal_feedback,
            can_add=can_add_journal_feedback,
            extra_context=journal_feedback_context,
        ),
    )
