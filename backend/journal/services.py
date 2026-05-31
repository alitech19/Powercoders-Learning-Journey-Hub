from datetime import date, timedelta

from .models import JournalEntry


def writing_streak(user):
    dates = set(
        JournalEntry.objects.filter(author=user)
        .values_list('entry_date', flat=True)
        .distinct()
    )
    today = date.today()
    cursor = today if today in dates else today - timedelta(days=1)
    if cursor not in dates:
        return 0
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
