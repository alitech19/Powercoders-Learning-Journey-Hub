from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Task(models.Model):
    """
    Owner (created_by) controls the task: edit, delete, reassign.
    Assignee (assignee_type + assignee_user/group/cohort) performs the task.
    Private: visible only to owner.
    Public: visible to owner + assignee.
    """

    class AssigneeType(models.TextChoices):
        USER = 'user', 'User'
        GROUP = 'group', 'Group'
        COHORT = 'cohort', 'Cohort'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'

    class Status(models.TextChoices):
        TODO = 'todo', 'To do'
        DOING = 'doing', 'Doing'
        BLOCKED = 'blocked', 'Blocked'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
    )
    assignee_type = models.CharField(max_length=20, choices=AssigneeType.choices)
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )
    assignee_group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )
    assignee_cohort = models.ForeignKey(
        'cohorts.Cohort',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at', 'title']

    def __str__(self):
        return self.title

    @property
    def is_subtask(self):
        return self.parent_id is not None

    @property
    def is_private(self):
        return self.visibility == self.Visibility.PRIVATE

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC

    def clean(self):
        errors = {}
        if self.assignee_type == self.AssigneeType.USER:
            if not self.assignee_user_id:
                errors['assignee_user'] = 'Assignee user is required for user-assigned tasks.'
            if self.assignee_group_id or self.assignee_cohort_id:
                errors['assignee_type'] = 'Only assignee_user should be set for user type.'
        elif self.assignee_type == self.AssigneeType.GROUP:
            if not self.assignee_group_id:
                errors['assignee_group'] = 'Assignee group is required for group-assigned tasks.'
            if self.assignee_user_id or self.assignee_cohort_id:
                errors['assignee_type'] = 'Only assignee_group should be set for group type.'
        elif self.assignee_type == self.AssigneeType.COHORT:
            if not self.assignee_cohort_id:
                errors['assignee_cohort'] = 'Assignee cohort is required for cohort-assigned tasks.'
            if self.assignee_user_id or self.assignee_group_id:
                errors['assignee_type'] = 'Only assignee_cohort should be set for cohort type.'

        if self.parent_id is not None:
            if self.pk and self.parent_id == self.pk:
                errors['parent'] = 'A task cannot be its own parent.'
            parent = self.parent
            if parent:
                if parent.assignee_type != self.assignee_type:
                    errors['parent'] = 'Subtask must have same assignee type as parent.'
                if self.assignee_type == self.AssigneeType.USER and parent.assignee_user_id != self.assignee_user_id:
                    errors['parent'] = 'Subtask must be assigned to same user as parent.'
                if self.assignee_type == self.AssigneeType.GROUP and parent.assignee_group_id != self.assignee_group_id:
                    errors['parent'] = 'Subtask must be assigned to same group as parent.'
                if self.assignee_type == self.AssigneeType.COHORT and parent.assignee_cohort_id != self.assignee_cohort_id:
                    errors['parent'] = 'Subtask must be assigned to same cohort as parent.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.parent_id is not None and self.parent:
            self.visibility = self.parent.visibility
            self.assignee_type = self.parent.assignee_type
            self.assignee_user = self.parent.assignee_user
            self.assignee_group = self.parent.assignee_group
            self.assignee_cohort = self.parent.assignee_cohort

        if self.status == self.Status.DONE:
            if not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.completed_at = None
        self.full_clean()
        super().save(*args, **kwargs)


class TaskUpdate(models.Model):
    """Progress updates on a task. Visibility follows the parent Task."""

    class UpdateType(models.TextChoices):
        PROGRESS = 'progress', 'Progress'
        BLOCKER = 'blocker', 'Blocker'
        NOTE = 'note', 'Note'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='updates')
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
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'task update'
        verbose_name_plural = 'task updates'

    def __str__(self):
        return f'{self.get_update_type_display()} on {self.task}'


class TaskComment(models.Model):
    """
    Threaded discussion on a task. Visibility follows the parent Task.
    parent=null: top-level comment; parent set: reply (any depth).
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
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
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.task}'

    def clean(self):
        errors = {}
        if self.parent_id is not None:
            if self.pk and self.parent_id == self.pk:
                errors['parent'] = 'A comment cannot be its own parent.'
            else:
                parent = self.parent
                if parent is None:
                    errors['parent'] = 'Parent comment does not exist.'
                elif parent.task_id != self.task_id:
                    errors['parent'] = 'Parent comment must belong to the same task.'
                elif self.pk:
                    ancestor = parent
                    while ancestor is not None:
                        if ancestor.pk == self.pk:
                            errors['parent'] = (
                                'A comment cannot be placed under its own reply.'
                            )
                            break
                        ancestor = ancestor.parent
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
