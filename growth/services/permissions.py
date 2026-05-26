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

from ..models import DailyJournalEntry, Goal, GoalSubgoal, Habit, WellbeingCheckIn, WeeklyReflection


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
    if not user.is_authenticated:
        return False
    if goal.student_id == user.pk and (goal.created_by_id is None or goal.created_by_id == user.pk):
        return True
    if goal.created_by_id == user.pk and (user_is_teacher(user) or user_is_admin(user)):
        return True
    return False


def can_mark_goal_achieved(user, goal):
    if not user.is_authenticated:
        return False
    if goal.status != Goal.Status.ACTIVE:
        return False
    if goal.student_id == user.pk:
        return True
    if goal.created_by_id == user.pk and (user_is_teacher(user) or user_is_admin(user)):
        return True
    return False


def can_delete_goal(user, goal):
    if not user.is_authenticated:
        return False
    if goal.student_id == user.pk and (goal.created_by_id is None or goal.created_by_id == user.pk):
        return True
    if goal.created_by_id == user.pk and (user_is_teacher(user) or user_is_admin(user)):
        return True
    return False


def can_create_goal_for_student(user, student):
    if not user.is_authenticated:
        return False
    if user_is_student(user):
        return student.pk == user.pk
    if user_is_teacher(user):
        return _teacher_supervises_student(user, student)
    if user_is_admin(user):
        return True
    return False


def can_manage_goal_subgoals(user, goal):
    return can_edit_goal(user, goal)


def can_toggle_subgoal(user, subgoal):
    return can_manage_goal_subgoals(user, subgoal.goal)


def can_edit_subgoal(user, subgoal):
    return can_manage_goal_subgoals(user, subgoal.goal)


def can_delete_subgoal(user, subgoal):
    return can_manage_goal_subgoals(user, subgoal.goal)


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


# -- Habit permissions -----------------------------------------------------

def can_view_habit(user, habit):
    if not user.is_authenticated:
        return False
    if habit.student_id == user.pk:
        return True
    if user_is_admin(user):
        return True
    if user_is_teacher(user) and _teacher_supervises_student(user, habit.student):
        return True
    return False


def can_edit_habit(user, habit):
    return (
        user.is_authenticated
        and habit.student_id == user.pk
        and habit.status == Habit.Status.ACTIVE
    )


def can_delete_habit(user, habit):
    return (
        user.is_authenticated
        and habit.student_id == user.pk
        and habit.status == Habit.Status.COMPLETED
    )


def can_reactivate_habit(user, habit):
    return (
        user.is_authenticated
        and habit.student_id == user.pk
        and habit.status == Habit.Status.COMPLETED
    )


def can_log_habit(user, habit):
    return (
        user.is_authenticated
        and habit.student_id == user.pk
        and habit.status == Habit.Status.ACTIVE
    )


def can_complete_habit(user, habit):
    return (
        user.is_authenticated
        and habit.student_id == user.pk
        and habit.status == Habit.Status.ACTIVE
    )


# -- Wellbeing permissions -------------------------------------------------

def can_view_wellbeing_checkin(user, checkin):
    if not user.is_authenticated:
        return False
    if checkin.student_id == user.pk:
        return True
    if user_is_admin(user):
        return True
    if user_is_teacher(user) and _teacher_supervises_student(user, checkin.student):
        return True
    return False


def can_edit_wellbeing_checkin(user, checkin):
    return user.is_authenticated and checkin.student_id == user.pk


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
    if isinstance(target, Habit):
        return can_view_habit(user, target)
    if isinstance(target, WellbeingCheckIn):
        return can_view_wellbeing_checkin(user, target)
    return False
