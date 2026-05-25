"""
Permission-aware querysets for the growth app.

Reuses the role helpers and teacher–group mapping from tracker.permissions
so that there is a single source of truth for role checks and group assignments.
"""

from tracker.permissions import (
    get_teacher_accessible_students,
    user_is_admin,
    user_is_student,
    user_is_teacher,
)

from .models import Feedback, Goal, WeeklyReflection


def get_students_for_teacher(user):
    """Return the queryset of students assigned to this teacher's groups."""
    return get_teacher_accessible_students(user)


def get_visible_goals_for_user(user):
    """
    student  → own goals (private + public)
    teacher  → public goals of assigned students
    admin    → all public goals
    other    → none
    """
    qs = Goal.objects.select_related('student')

    if user_is_student(user):
        return qs.filter(student=user)

    if user_is_teacher(user):
        student_ids = get_students_for_teacher(user).values_list('pk', flat=True)
        return qs.filter(
            student_id__in=student_ids,
            visibility=Goal.Visibility.PUBLIC,
        )

    if user_is_admin(user):
        return qs.filter(visibility=Goal.Visibility.PUBLIC)

    return qs.none()


def get_visible_reflections_for_user(user):
    """
    student  → own reflections
    teacher  → reflections of assigned students
    admin    → all reflections
    other    → none
    """
    qs = WeeklyReflection.objects.select_related('student')

    if user_is_student(user):
        return qs.filter(student=user)

    if user_is_teacher(user):
        student_ids = get_students_for_teacher(user).values_list('pk', flat=True)
        return qs.filter(student_id__in=student_ids)

    if user_is_admin(user):
        return qs.all()

    return qs.none()


def get_visible_feedback_for_user(user):
    """
    student  → feedback received by the student
    teacher  → feedback for assigned students
    admin    → all feedback
    other    → none
    """
    qs = Feedback.objects.select_related('author', 'student', 'content_type')

    if user_is_student(user):
        return qs.filter(student=user)

    if user_is_teacher(user):
        student_ids = get_students_for_teacher(user).values_list('pk', flat=True)
        return qs.filter(student_id__in=student_ids)

    if user_is_admin(user):
        return qs.all()

    return qs.none()
