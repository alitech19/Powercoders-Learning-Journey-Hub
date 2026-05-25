"""
Teacher dashboard helpers for the growth app.
"""

from django.utils import timezone

from ..models import DailyJournalEntry, Feedback, Goal, Habit, WeeklyReflection
from .habits import get_done_count_for_week, get_week_start


def get_growth_summary_for_student(student):
    """
    Return a dict with high-level growth stats for *public* goals,
    all reflections, journal entries, and habits belonging to ``student``.
    """
    public_goals = Goal.objects.filter(
        student=student,
        visibility=Goal.Visibility.PUBLIC,
    )

    today = timezone.now().date()
    week_start = get_week_start(today)

    active_habits = Habit.objects.filter(
        student=student, status=Habit.Status.ACTIVE,
    )
    active_count = active_habits.count()
    on_track = sum(
        1 for h in active_habits
        if get_done_count_for_week(h, week_start) >= h.target_days_per_week
    )

    return {
        'public_goals_count': public_goals.count(),
        'latest_reflection': WeeklyReflection.objects.filter(
            student=student,
        ).first(),
        'latest_journal_entry': DailyJournalEntry.objects.filter(
            student=student,
        ).first(),
        'active_habits_count': active_count,
        'habits_on_track': on_track,
        'completed_habits_count': Habit.objects.filter(
            student=student, status=Habit.Status.COMPLETED,
        ).count(),
        'feedback_count': Feedback.objects.filter(
            student=student,
        ).count(),
    }
