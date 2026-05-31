"""Habit feedback hooks for the generic feedback app."""

from cohorts.permissions import user_is_staff

from .models import Habit
from .permissions import can_view_habit


def can_view_habit_feedback(user, habit):
    if user.pk == habit.author_id:
        return can_view_habit(user, habit)
    if not can_view_habit(user, habit):
        return False
    return user_is_staff(user)


def can_add_habit_feedback(user, habit):
    if not user_is_staff(user):
        return False
    if habit.visibility != Habit.Visibility.SHARED:
        return False
    return can_view_habit_feedback(user, habit)


def habit_feedback_context(habit, viewer):
    placeholder = 'Leave feedback for this student…'
    if viewer.pk != habit.author_id:
        placeholder = f'Leave feedback for {habit.author.display_name}…'
    return {
        'visibility_shared': habit.visibility == Habit.Visibility.SHARED,
        'feedback_placeholder': placeholder,
    }


def register_habit_feedback_handlers():
    from feedback.registry import FeedbackHandlers, register

    register(
        Habit,
        FeedbackHandlers(
            can_view=can_view_habit_feedback,
            can_add=can_add_habit_feedback,
            extra_context=habit_feedback_context,
        ),
    )
