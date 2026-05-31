from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

from .constants import CONTENT_MAX_LENGTH, MOOD_OPTIONS, TAGS_MAX_LENGTH, TITLE_MAX_LENGTH


class JournalEntry(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Only me'
        SHARED = 'shared', 'Visible to teachers'

    class Mood(models.TextChoices):
        GREAT = 'great', 'Great'
        GOOD = 'good', 'Good'
        OKAY = 'okay', 'Okay'
        STRUGGLING = 'struggling', 'Struggling'
        TOUGH = 'tough', 'Tough'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_entries',
    )
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    content = models.TextField(validators=[MaxLengthValidator(CONTENT_MAX_LENGTH)])
    entry_date = models.DateField()
    mood = models.CharField(max_length=20, choices=Mood.choices, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    tags = models.CharField(max_length=TAGS_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']
        indexes = [
            models.Index(fields=['author', '-entry_date']),
            models.Index(fields=['author', 'visibility']),
            models.Index(fields=['title']),
        ]

    def __str__(self):
        return f'{self.author} — {self.title} ({self.entry_date})'

    def get_tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def mood_emoji(self):
        for level, emoji, _label in MOOD_OPTIONS:
            if level == self.mood:
                return emoji
        return ''

    @property
    def word_count(self):
        return len(self.content.split()) if (self.content or '').strip() else 0

    @property
    def excerpt(self):
        text = (self.content or '').strip()
        if len(text) <= 160:
            return text
        return text[:160].rsplit(' ', 1)[0] + '…'
