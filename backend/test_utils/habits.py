from datetime import date

from habits.models import Habit, HabitLog


def make_habit(
    author,
    *,
    title='Daily practice',
    visibility=Habit.Visibility.PRIVATE,
    status=Habit.Status.ACTIVE,
    target_days_per_week=3,
    **kwargs,
):
    return Habit.objects.create(
        author=author,
        title=title,
        visibility=visibility,
        status=status,
        target_days_per_week=target_days_per_week,
        **kwargs,
    )


def log_habit(habit, day, *, status=HabitLog.Status.DONE, note=''):
    return HabitLog.objects.create(habit=habit, date=day, status=status, note=note)
