from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

from config.input_limits import (
    LONG_TEXT_MAX_LENGTH,
    SHORT_LABEL_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)

from .constants import EXPECTATIONS_TEMPLATE, FINAL_REFLECTION_TEMPLATE


def expectations_is_started(text):
    """True when the student has written something beyond the default template."""
    normalized = (text or '').strip()
    if not normalized:
        return False
    return normalized != EXPECTATIONS_TEMPLATE.strip()


def final_reflection_is_started(text):
    """True when the student has written something beyond the default template."""
    normalized = (text or '').strip()
    if not normalized:
        return False
    return normalized != FINAL_REFLECTION_TEMPLATE.strip()


class Reflection(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Only me'
        SHARED = 'shared', 'Visible to teachers'

    class WellbeingLevel(models.TextChoices):
        GREAT = 'great', 'Great'
        GOOD = 'good', 'Good'
        OKAY = 'okay', 'Okay'
        STRUGGLING = 'struggling', 'Struggling'
        TOUGH = 'tough', 'Tough'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reflections',
    )
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    tags = models.JSONField(default=list, blank=True)
    custom_label = models.CharField(max_length=SHORT_LABEL_MAX_LENGTH, blank=True)
    expectations = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(LONG_TEXT_MAX_LENGTH)],
    )
    final_reflection = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(LONG_TEXT_MAX_LENGTH)],
    )
    energy = models.CharField(
        max_length=20, choices=WellbeingLevel.choices, blank=True,
    )
    calmness = models.CharField(
        max_length=20, choices=WellbeingLevel.choices, blank=True,
    )
    engagement = models.CharField(
        max_length=20, choices=WellbeingLevel.choices, blank=True,
    )
    concentration = models.CharField(
        max_length=20, choices=WellbeingLevel.choices, blank=True,
    )
    sleep = models.CharField(
        max_length=20, choices=WellbeingLevel.choices, blank=True,
    )
    physical_activity = models.CharField(
        max_length=20, choices=WellbeingLevel.choices, blank=True,
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expectations_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last save when expectations contain real content.',
    )
    final_reflection_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last save when final reflection contains real content.',
    )

    class Meta:
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['author', 'visibility']),
            models.Index(fields=['title']),
        ]

    def __str__(self):
        return f'{self.author} — {self.title}'

    @property
    def tag_labels(self):
        labels = []
        for tag in self.tags or []:
            if tag == TAG_WEEKLY:
                labels.append('Weekly')
            elif tag == TAG_PROJECT:
                labels.append('Project')
            elif tag == TAG_CUSTOM:
                labels.append(self.custom_label or 'Custom')
        return labels

    @property
    def has_expectations(self):
        return expectations_is_started(self.expectations)

    @property
    def has_final_reflection(self):
        return final_reflection_is_started(self.final_reflection)

    @property
    def show_wellbeing(self):
        return self.has_final_reflection

    @property
    def display_date(self):
        """Best date for list cards — finish if done, else start."""
        return self.final_reflection_at or self.expectations_at or self.created_at

    @property
    def wellbeing_filled_count(self):
        fields = (
            self.energy, self.calmness, self.engagement,
            self.concentration, self.sleep, self.physical_activity,
        )
        return sum(1 for value in fields if value)

    @classmethod
    def wellbeing_field_names(cls):
        return (
            'energy', 'calmness', 'engagement',
            'concentration', 'sleep', 'physical_activity',
        )

    def wellbeing_level_emoji(self, field_name):
        value = getattr(self, field_name, '')
        from .constants import MOOD_OPTIONS
        for level, emoji, _label in MOOD_OPTIONS:
            if level == value:
                return emoji
        return ''
