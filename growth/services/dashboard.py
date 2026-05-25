"""
Teacher dashboard helpers for the growth app.
"""

from django.db.models import Avg
from django.utils import timezone

from ..models import DailyJournalEntry, Feedback, Goal, WeeklyReflection


def get_growth_summary_for_student(student):
    """
    Return a dict with high-level growth stats for *public* goals,
    all reflections, and journal entries belonging to ``student``.
    """
    public_goals = Goal.objects.filter(
        student=student,
        visibility=Goal.Visibility.PUBLIC,
    )

    return {
        'public_goals_count': public_goals.count(),
        'latest_reflection': WeeklyReflection.objects.filter(
            student=student,
        ).first(),
        'latest_journal_entry': DailyJournalEntry.objects.filter(
            student=student,
        ).first(),
        'feedback_count': Feedback.objects.filter(
            student=student,
        ).count(),
    }
