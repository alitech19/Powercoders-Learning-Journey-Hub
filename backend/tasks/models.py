from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone

from config.input_limits import (
    BODY_TEXT_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)


class Task(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Only me'
        SHARED = 'shared', 'Visible to teachers'

    class Status(models.TextChoices):
        TODO = 'todo', 'To do'
        DOING = 'doing', 'Doing'
        BLOCKED = 'blocked', 'Blocked'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'

    class AssigneeType(models.TextChoices):
        USER = 'user', 'User'
        GROUP = 'group', 'Group'

    class ProgressMode(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual'
        SHARED = 'shared', 'Shared'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authored_tasks',
        null=True,
        blank=True,
        help_text='Set for student-created tasks; null for staff-assigned templates.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks_created_for_students',
    )
    assignee_type = models.CharField(
        max_length=20,
        choices=AssigneeType.choices,
        default=AssigneeType.USER,
    )
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='personal_tasks',
    )
    assignee_group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='group_tasks',
    )
    assignee_cohort = models.ForeignKey(
        'cohorts.Cohort',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cohort_tasks',
        help_text='Set when staff assigns via cohort picker (individual progress per student).',
    )
    progress_mode = models.CharField(
        max_length=20,
        choices=ProgressMode.choices,
        default=ProgressMode.INDIVIDUAL,
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    allow_updates = models.BooleanField(default=True)
    allow_comments = models.BooleanField(default=True)
    allow_subtasks = models.BooleanField(default=True)
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(DESCRIPTION_MAX_LENGTH)],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    resource_container = models.ForeignKey(
        'resources.ResourceContainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )
    scheduled_publish_at = models.DateTimeField(null=True, blank=True)
    scheduled_publish_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['visibility']),
            models.Index(fields=['assignee_type']),
            models.Index(fields=['progress_mode']),
        ]

    def __str__(self):
        if self.author_id:
            return f'{self.author} — {self.title}'
        return self.title

    @property
    def is_staff_assigned(self):
        return self.author_id is None

    @property
    def is_group_shared(self):
        return (
            self.assignee_type == self.AssigneeType.GROUP
            and self.progress_mode == self.ProgressMode.SHARED
        )

    class ListKind(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual'
        COHORT = 'cohort', 'Cohort'
        GROUP = 'group', 'Group'

    @property
    def list_kind(self):
        if self.is_group_shared:
            return self.ListKind.GROUP
        if self.assignee_cohort_id:
            return self.ListKind.COHORT
        return self.ListKind.INDIVIDUAL

    @property
    def scope_label(self):
        if self.is_group_shared and self.assignee_group_id:
            return str(self.assignee_group)
        if self.assignee_cohort_id:
            return self.assignee_cohort.name
        if self.assignee_user_id:
            return self.assignee_user.display_name
        if self.enrolled_count:
            return f'{self.enrolled_count} student{"s" if self.enrolled_count != 1 else ""}'
        return '—'

    @property
    def enrolled_count(self):
        if 'enrollments' in getattr(self, '_prefetched_objects_cache', {}):
            return len(self._prefetched_objects_cache['enrollments'])
        return self.enrollments.count()

    def clean(self):
        errors = {}
        if self.assignee_type == self.AssigneeType.GROUP:
            if not self.assignee_group_id:
                errors['assignee_group'] = 'Group is required for group assignment.'
            if self.assignee_user_id:
                errors['assignee_user'] = 'User must be empty for group assignment.'
            if self.progress_mode != self.ProgressMode.SHARED:
                errors['progress_mode'] = 'Group tasks must use shared progress.'
        elif self.assignee_type == self.AssigneeType.USER:
            if self.assignee_group_id:
                errors['assignee_group'] = 'Group must be empty for user assignment.'
            if self.assignee_cohort_id and self.author_id:
                errors['assignee_cohort'] = 'Cohort scope applies to staff-assigned tasks only.'
            if self.author_id and not self.assignee_user_id:
                errors['assignee_user'] = 'Personal tasks require an assignee user.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.assignee_type == self.AssigneeType.GROUP:
            self.progress_mode = self.ProgressMode.SHARED
        if self.is_group_shared:
            if self.status == self.Status.DONE:
                if not self.completed_at:
                    self.completed_at = timezone.now()
            else:
                self.completed_at = None
        super().save(*args, **kwargs)


class TaskEnrollment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_enrollments',
    )
    status = models.CharField(
        max_length=20,
        choices=Task.Status.choices,
        default=Task.Status.TODO,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task', 'student'], name='unique_task_enrollment'),
        ]
        ordering = ['student__display_name', 'pk']
        indexes = [
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f'{self.student} → {self.task.title}'

    def subtasks_for_student(self):
        return self.task.subtasks.filter(
            models.Q(added_by__isnull=True) | models.Q(added_by_id=self.student_id)
        )

    def completed_subtask_ids(self):
        return set(
            self.subtask_enrollments.filter(status=Task.Status.DONE).values_list(
                'subtask_id', flat=True
            )
        )

    @property
    def subtasks_done(self):
        return self.subtask_enrollments.filter(status=Task.Status.DONE).count()

    @property
    def subtasks_total(self):
        return self.subtasks_for_student().count()

    @property
    def progress(self):
        total = self.subtasks_total
        if not total:
            return {
                Task.Status.TODO: 0,
                Task.Status.DOING: 50,
                Task.Status.BLOCKED: 0,
                Task.Status.DONE: 100,
            }.get(self.status, 0)
        return round(self.subtasks_done / total * 100)

    def save(self, *args, **kwargs):
        if self.status == Task.Status.DONE:
            if not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.completed_at = None
        super().save(*args, **kwargs)


class Subtask(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(DESCRIPTION_MAX_LENGTH)],
    )
    priority = models.CharField(
        max_length=20,
        choices=Task.Priority.choices,
        default=Task.Priority.NORMAL,
    )
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_subtasks',
        help_text='Null = staff template subtask synced on edit.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    @property
    def is_template(self):
        return self.added_by_id is None


class SubtaskEnrollment(models.Model):
    enrollment = models.ForeignKey(
        TaskEnrollment,
        on_delete=models.CASCADE,
        related_name='subtask_enrollments',
    )
    subtask = models.ForeignKey(
        Subtask,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    status = models.CharField(
        max_length=20,
        choices=Task.Status.choices,
        default=Task.Status.TODO,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'subtask'],
                name='unique_subtask_enrollment',
            ),
        ]
        ordering = ['subtask__order', 'subtask__pk']

    def __str__(self):
        return f'{self.enrollment.student} — {self.subtask.title} ({self.status})'

    def save(self, *args, **kwargs):
        if self.status == Task.Status.DONE:
            if not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.completed_at = None
        super().save(*args, **kwargs)


class TaskUpdate(models.Model):
    class UpdateType(models.TextChoices):
        PROGRESS = 'progress', 'Progress'
        BLOCKER = 'blocker', 'Blocker'
        NOTE = 'note', 'Note'

    enrollment = models.ForeignKey(
        TaskEnrollment,
        on_delete=models.CASCADE,
        related_name='updates',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_updates',
    )
    update_type = models.CharField(
        max_length=20,
        choices=UpdateType.choices,
        default=UpdateType.NOTE,
    )
    text = models.TextField(validators=[MaxLengthValidator(BODY_TEXT_MAX_LENGTH)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_update_type_display()} on {self.enrollment.task.title}'


class TaskComment(models.Model):
    enrollment = models.ForeignKey(
        TaskEnrollment,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_comments',
    )
    text = models.TextField(validators=[MaxLengthValidator(BODY_TEXT_MAX_LENGTH)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.enrollment.task.title}'
