"""
Teacher dashboard helpers for the growth app.
"""

from django.utils import timezone

from ..models import Feedback, Goal, WeeklyReflection


def get_growth_summary_for_student(student):
    """
    Return a dict with high-level growth stats for *public* goals
    and all reflections belonging to ``student``.
    """
    public_goals = Goal.objects.filter(
        student=student,
        visibility=Goal.Visibility.PUBLIC,
    )
    today = timezone.now().date()

    return {
        'public_goals_count': public_goals.count(),
        'active_public_goals_count': public_goals.filter(
            status=Goal.Status.ACTIVE,
        ).count(),
        'overdue_public_goals_count': public_goals.filter(
            status=Goal.Status.ACTIVE,
            time_bound__lt=today,
        ).count(),
        'latest_reflection': WeeklyReflection.objects.filter(
            student=student,
        ).first(),
        'feedback_count': Feedback.objects.filter(
            student=student,
        ).count(),
    }
