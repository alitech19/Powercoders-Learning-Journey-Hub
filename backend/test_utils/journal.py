from datetime import date

from journal.models import JournalEntry


def make_journal_entry(
    author,
    *,
    title='Journal',
    content='Today I learned something useful.',
    entry_date=None,
    visibility=JournalEntry.Visibility.PRIVATE,
    mood='',
    tags='',
    **kwargs,
):
    return JournalEntry.objects.create(
        author=author,
        title=title,
        content=content,
        entry_date=entry_date or date.today(),
        visibility=visibility,
        mood=mood,
        tags=tags,
        **kwargs,
    )
