from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Private'
        PUBLIC = 'public', 'Share with teaching team'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ACHIEVED = 'achieved', 'Achieved'
        PAUSED = 'paused', 'Paused'
        ABANDONED = 'abandoned', 'Abandoned'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    target_date = models.DateField()
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
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
    achieved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    feedback = GenericRelation(
        'growth.Feedback',
        content_type_field='content_type',
        object_id_field='object_id',
    )

    class Meta:
        ordering = ['-updated_at', 'title']

    def __str__(self):
        return self.title

    @property
    def is_private(self):
        return self.visibility == self.Visibility.PRIVATE

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC

    @property
    def is_overdue(self):
        return (
            self.status == self.Status.ACTIVE
            and self.target_date < timezone.now().date()
        )

    def save(self, *args, **kwargs):
        if self.status == self.Status.ACHIEVED:
            self.progress_percent = 100
            if not self.achieved_at:
                self.achieved_at = timezone.now()
        elif self.status != self.Status.ACHIEVED:
            self.achieved_at = None
        super().save(*args, **kwargs)


class WeeklyReflection(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_reflections',
    )
    week_start = models.DateField()
    week_end = models.DateField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    feedback = GenericRelation(
        'growth.Feedback',
        content_type_field='content_type',
        object_id_field='object_id',
    )

    class Meta:
        ordering = ['-week_start']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'week_start'],
                name='unique_reflection_per_student_per_week',
            ),
        ]

    def __str__(self):
        return f'{self.student} — {self.week_start}'

    def clean(self):
        errors = {}
        if self.week_end and self.week_start and self.week_end <= self.week_start:
            errors['week_end'] = 'Week end must be after week start.'
        if not self.content or not self.content.strip():
            errors['content'] = 'Content is required.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DailyJournalEntry(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_entries',
    )
    entry_date = models.DateField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    feedback = GenericRelation(
        'growth.Feedback',
        content_type_field='content_type',
        object_id_field='object_id',
    )

    class Meta:
        ordering = ['-entry_date']
        verbose_name = 'daily journal entry'
        verbose_name_plural = 'daily journal entries'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'entry_date'],
                name='unique_journal_entry_per_student_per_day',
            ),
        ]

    def __str__(self):
        return f'{self.student} — {self.entry_date}'


class Habit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habits',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    target_days_per_week = models.PositiveSmallIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
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

    feedback = GenericRelation(
        'growth.Feedback',
        content_type_field='content_type',
        object_id_field='object_id',
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )
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


class WellbeingCheckIn(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wellbeing_checkins',
    )
    check_date = models.DateField()
    energy = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    calmness = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    engagement = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    concentration = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    sleep = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    physical_activity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    feedback = GenericRelation(
        'growth.Feedback',
        content_type_field='content_type',
        object_id_field='object_id',
    )

    class Meta:
        ordering = ['-check_date']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'check_date'],
                name='unique_wellbeing_per_student_per_day',
            ),
        ]

    def __str__(self):
        return f'{self.student} — {self.check_date}'

    @property
    def wellbeing_average(self):
        return round(
            (
                self.energy
                + self.calmness
                + self.engagement
                + self.concentration
                + self.sleep
                + self.physical_activity
            ) / 6,
            1,
        )


class Feedback(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='growth_feedback_given',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='growth_feedback_received',
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Feedback by {self.author} for {self.student}'
