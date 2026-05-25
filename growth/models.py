from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
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
    specific = models.TextField()
    measurable = models.TextField()
    achievable = models.TextField()
    relevant = models.TextField()
    time_bound = models.DateField()
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
            and self.time_bound < timezone.now().date()
        )

    def save(self, *args, **kwargs):
        if self.status == self.Status.ACHIEVED and not self.achieved_at:
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
    more_of = models.TextField(blank=True)
    less_of = models.TextField(blank=True)
    start_doing = models.TextField(blank=True)
    stop_doing = models.TextField(blank=True)
    continue_doing = models.TextField(blank=True)
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

        agile_fields = [
            self.more_of, self.less_of, self.start_doing,
            self.stop_doing, self.continue_doing,
        ]
        if not any(f.strip() for f in agile_fields if f):
            errors['__all__'] = 'At least one reflection field must be filled.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
