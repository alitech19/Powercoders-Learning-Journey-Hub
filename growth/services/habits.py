"""
Weekly tracking and streak helpers for the Habits module.
"""

from datetime import timedelta

from django.utils import timezone

from ..models import HabitLog


def get_week_start(d):
    """Return Monday of the week containing *d*."""
    return d - timedelta(days=d.weekday())


def get_week_end(d):
    """Return Sunday of the week containing *d*."""
    return d + timedelta(days=6 - d.weekday())


def get_habit_week_logs(habit, week_start):
    """Return logs for *habit* from Monday to Sunday of the given week."""
    week_end = week_start + timedelta(days=6)
    return habit.logs.filter(date__gte=week_start, date__lte=week_end)


def get_done_count_for_week(habit, week_start):
    """Count logs with status=done in the given week."""
    return get_habit_week_logs(habit, week_start).filter(
        status=HabitLog.Status.DONE,
    ).count()


def is_habit_week_successful(habit, week_start):
    """True if done_count >= habit.target_days_per_week."""
    return get_done_count_for_week(habit, week_start) >= habit.target_days_per_week


def get_current_weekly_streak(habit, today=None):
    """
    Count consecutive successful weeks ending with (or near) today.

    - If the current week already meets the target, it counts.
    - If the current week hasn't met the target yet but isn't over
      (today < Sunday), we start counting from the previous week
      so the streak isn't broken prematurely.
    - Walk backwards week by week until a week fails.
    """
    if today is None:
        today = timezone.now().date()

    current_week_start = get_week_start(today)
    current_week_end = get_week_end(today)

    if is_habit_week_successful(habit, current_week_start):
        check_from = current_week_start
    elif today < current_week_end:
        check_from = current_week_start - timedelta(days=7)
    else:
        check_from = current_week_start - timedelta(days=7)

    streak = 0
    ws = check_from
    while True:
        if is_habit_week_successful(habit, ws):
            streak += 1
            ws -= timedelta(days=7)
        else:
            break

    return streak


def build_week_table(habit, today=None):
    """
    Return a list of 7 dicts (Mon-Sun) for the current week,
    each with 'date', 'weekday', 'log' (HabitLog or None).
    """
    if today is None:
        today = timezone.now().date()

    week_start = get_week_start(today)
    logs = {
        log.date: log
        for log in get_habit_week_logs(habit, week_start)
    }

    weekdays = [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday',
        'Friday', 'Saturday', 'Sunday',
    ]
    table = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        table.append({
            'date': d,
            'weekday': weekdays[i],
            'log': logs.get(d),
        })
    return table
