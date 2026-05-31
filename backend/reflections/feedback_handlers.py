"""Reflection feedback hooks for the generic feedback app."""

from cohorts.permissions import user_is_staff

from .models import Reflection
from .permissions import _teacher_supervises_student, can_view_reflection


def can_view_reflection_feedback(user, reflection):
    if user.pk == reflection.author_id:
        return can_view_reflection(user, reflection)
    if not can_view_reflection(user, reflection):
        return False
    if user_is_staff(user):
        return _teacher_supervises_student(user, reflection.author)
    return False


def can_add_reflection_feedback(user, reflection):
    if not user_is_staff(user):
        return False
    if reflection.visibility != Reflection.Visibility.SHARED:
        return False
    return can_view_reflection_feedback(user, reflection)


def reflection_feedback_context(reflection, viewer):
    placeholder = 'Leave feedback for this student…'
    if viewer.pk != reflection.author_id:
        placeholder = f'Leave feedback for {reflection.author.display_name}…'
    return {
        'visibility_shared': reflection.visibility == Reflection.Visibility.SHARED,
        'feedback_placeholder': placeholder,
    }


def register_reflection_feedback_handlers():
    from feedback.registry import FeedbackHandlers, register

    register(
        Reflection,
        FeedbackHandlers(
            can_view=can_view_reflection_feedback,
            can_add=can_add_reflection_feedback,
            extra_context=reflection_feedback_context,
        ),
    )
