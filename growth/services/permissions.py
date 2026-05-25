"""
Object-level permission helpers for the growth app.

Reuses the role helpers from tracker.permissions to stay consistent
with the rest of the project.
"""

from tracker.permissions import (
    get_teacher_group_ids,
    user_is_admin,
    user_is_student,
    user_is_teacher,
)

from ..models import DailyJournalEntry, Goal, WeeklyReflection


# -- helpers ---------------------------------------------------------------

def _teacher_supervises_student(user, student):
    """True when the teacher is assigned to the student's group."""
    if not student.group_id:
        return False
    return student.group_id in get_teacher_group_ids(user)


# -- Goal permissions ------------------------------------------------------

def can_view_goal(user, goal):
    if not user.is_authenticated:
        return False
    if goal.student_id == user.pk:
        return True
    if goal.is_private:
        return False
    if user_is_admin(user):
        return True
    if user_is_teacher(user) and _teacher_supervises_student(user, goal.student):
        return True
    return False


def can_edit_goal(user, goal):
    return user.is_authenticated and goal.student_id == user.pk


def can_mark_goal_achieved(user, goal):
    return (
        user.is_authenticated
        and goal.student_id == user.pk
        and goal.status == Goal.Status.ACTIVE
    )


def can_delete_goal(user, goal):
    return user.is_authenticated and goal.student_id == user.pk


# -- Reflection permissions ------------------------------------------------

def can_view_reflection(user, reflection):
    if not user.is_authenticated:
        return False
    if reflection.student_id == user.pk:
        return True
    if user_is_admin(user):
        return True
    if user_is_teacher(user) and _teacher_supervises_student(user, reflection.student):
        return True
    return False


def can_edit_reflection(user, reflection):
    return user.is_authenticated and reflection.student_id == user.pk


# -- Journal permissions ---------------------------------------------------

def can_view_journal_entry(user, entry):
    if not user.is_authenticated:
        return False
    if entry.student_id == user.pk:
        return True
    if user_is_admin(user):
        return True
    if user_is_teacher(user) and _teacher_supervises_student(user, entry.student):
        return True
    return False


def can_edit_journal_entry(user, entry):
    return user.is_authenticated and entry.student_id == user.pk


# -- Feedback permissions --------------------------------------------------

def can_view_feedback(user, feedback):
    if not user.is_authenticated:
        return False
    if feedback.student_id == user.pk:
        return True
    if user_is_admin(user):
        return True
    if user_is_teacher(user) and _teacher_supervises_student(user, feedback.student):
        return True
    return False


def can_create_feedback(user, target):
    """
    Teachers and admins can leave feedback on targets they are allowed to view.
    Students cannot create feedback in this MVP.
    """
    if not user.is_authenticated:
        return False
    if user_is_student(user):
        return False

    if isinstance(target, Goal):
        return can_view_goal(user, target)
    if isinstance(target, WeeklyReflection):
        return can_view_reflection(user, target)
    if isinstance(target, DailyJournalEntry):
        return can_view_journal_entry(user, target)
    return False
