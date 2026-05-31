from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (
    DAYS_PER_WEEK_DEFAULT,
    DAYS_PER_WEEK_MAX,
    DAYS_PER_WEEK_MIN,
    DESCRIPTION_MAX,
    TITLE_MAX,
)


class Habit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Only me'
        SHARED = 'shared', 'Visible to teachers'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habits',
    )
    title = models.CharField(max_length=TITLE_MAX)
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(DESCRIPTION_MAX)],
    )
    target_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    target_days_per_week = models.PositiveSmallIntegerField(
        default=DAYS_PER_WEEK_DEFAULT,
        validators=[
            MinValueValidator(DAYS_PER_WEEK_MIN),
            MaxValueValidator(DAYS_PER_WEEK_MAX),
        ],
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_weekly_streak = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'status']),
            models.Index(fields=['author', 'visibility']),
            models.Index(fields=['title']),
        ]

    def __str__(self):
        return f'{self.author} — {self.title}'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE


class HabitLog(models.Model):
    class Status(models.TextChoices):
        DONE = 'done', 'Done'
        NOT_DONE = 'not_done', 'Not done'

    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name='logs',
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['habit', 'date'],
                name='unique_habit_log_per_day',
            ),
        ]

    def __str__(self):
        return f'{self.habit.title} — {self.date} — {self.get_status_display()}'
