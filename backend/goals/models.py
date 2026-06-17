from datetime import date

from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

from config.input_limits import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH


class Goal(models.Model):
    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Hard Skill'
        SOFT_SKILL = 'soft_skill', 'Soft Skill'
        LANGUAGE = 'language', 'Language'
        PROJECT = 'project', 'Project'
        CAREER = 'career', 'Career'
        OTHER = 'other', 'Other'

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Only me'
        SHARED = 'shared', 'Visible to my teacher'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
        null=True,
        blank=True,
        help_text='Set for student-created goals; null for staff-assigned templates.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goals_created_for_students',
    )
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(DESCRIPTION_MAX_LENGTH)],
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TECHNICAL,
    )
    target_date = models.DateField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    resource_container = models.ForeignKey(
        'resources.ResourceContainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goals',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visibility']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        if self.author_id:
            return f'{self.author} — {self.title}'
        return self.title

    @property
    def is_staff_assigned(self):
        return self.author_id is None

    @property
    def enrolled_count(self):
        if 'enrollments' in getattr(self, '_prefetched_objects_cache', {}):
            return len(self._prefetched_objects_cache['enrollments'])
        return self.enrollments.count()

    @property
    def milestones_total(self):
        return self.milestones.count()


class GoalEnrollment(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        ABANDONED = 'abandoned', 'Abandoned'

    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goal_enrollments',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    achieved_at = models.DateTimeField(null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['goal', 'student'], name='unique_goal_enrollment'),
        ]
        ordering = ['student__display_name', 'pk']
        indexes = [
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f'{self.student} → {self.goal.title}'

    def completed_milestone_ids(self):
        return set(
            self.milestone_completions.values_list('milestone_id', flat=True)
        )

    @property
    def milestones_done(self):
        return self.milestone_completions.count()

    @property
    def milestones_total(self):
        return self.goal.milestones.count()

    @property
    def progress(self):
        total = self.milestones_total
        if not total:
            return {
                self.Status.NOT_STARTED: 0,
                self.Status.IN_PROGRESS: 50,
                self.Status.COMPLETED: 100,
                self.Status.ABANDONED: 0,
            }.get(self.status, 0)
        return round(self.milestones_done / total * 100)

    @property
    def all_milestones_complete(self):
        total = self.milestones_total
        if total == 0:
            return False
        return self.milestones_done >= total

    @property
    def is_overdue(self):
        return (
            self.goal.target_date
            and self.goal.target_date < date.today()
            and self.status not in (self.Status.COMPLETED, self.Status.ABANDONED)
        )

    def milestone_is_complete(self, milestone):
        return milestone.pk in self.completed_milestone_ids()


class Milestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title


class MilestoneCompletion(models.Model):
    enrollment = models.ForeignKey(
        GoalEnrollment,
        on_delete=models.CASCADE,
        related_name='milestone_completions',
    )
    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.CASCADE,
        related_name='completions',
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'milestone'],
                name='unique_milestone_completion',
            ),
        ]
        ordering = ['completed_at']

    def __str__(self):
        return f'{self.enrollment.student} ✓ {self.milestone.title}'
