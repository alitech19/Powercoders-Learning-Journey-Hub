from datetime import timedelta

from django.utils import timezone

from .models import Habit, HabitLog


def get_week_start(d):
    return d - timedelta(days=d.weekday())


def get_week_end(d):
    return d + timedelta(days=6 - d.weekday())


def get_habit_week_logs(habit, week_start):
    week_end = week_start + timedelta(days=6)
    return habit.logs.filter(date__gte=week_start, date__lte=week_end)


def get_done_count_for_week(habit, week_start):
    return get_habit_week_logs(habit, week_start).filter(
        status=HabitLog.Status.DONE,
    ).count()


def is_habit_week_successful(habit, week_start):
    return get_done_count_for_week(habit, week_start) >= habit.target_days_per_week


def get_current_weekly_streak(habit, today=None):
    if today is None:
        today = timezone.localdate()

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
    while is_habit_week_successful(habit, ws):
        streak += 1
        ws -= timedelta(days=7)
    return streak


def build_week_table(habit, today=None):
    if today is None:
        today = timezone.localdate()

    week_start = get_week_start(today)
    logs = {log.date: log for log in get_habit_week_logs(habit, week_start)}
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    table = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        table.append({
            'date': d,
            'weekday': weekdays[i],
            'log': logs.get(d),
            'is_today': d == today,
        })
    return table


def build_habit_row(habit, *, today, week_start, can_log=False):
    today_log = habit.logs.filter(date=today).first()
    done_this_week = get_done_count_for_week(habit, week_start)
    streak = get_current_weekly_streak(habit, today)
    return {
        'habit': habit,
        'today_log': today_log,
        'done_this_week': done_this_week,
        'streak': streak,
        'on_track': done_this_week >= habit.target_days_per_week,
        'can_log': can_log,
        'week_table': build_week_table(habit, today),
    }


def student_habit_stats(habits_qs, today=None):
    if today is None:
        today = timezone.localdate()
    week_start = get_week_start(today)
    active = habits_qs.filter(status=Habit.Status.ACTIVE)
    active_count = active.count()
    on_track = sum(
        1 for h in active
        if get_done_count_for_week(h, week_start) >= h.target_days_per_week
    )
    best_streak = max(
        (get_current_weekly_streak(h, today) for h in active),
        default=0,
    )
    return {
        'active_count': active_count,
        'on_track': on_track,
        'best_streak': best_streak,
        'completed_count': habits_qs.filter(status=Habit.Status.COMPLETED).count(),
    }
