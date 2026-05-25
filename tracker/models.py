from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Task(models.Model):
    """
    A task scoped directly to a user, group, or cohort.
    Public tasks: full content visible to users with scope access.
    Private tasks: full content only for owner/assignee; teachers/admins
    may see metadata only (enforced in views/permissions).
    """

    class ScopeType(models.TextChoices):
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

    scope_type = models.CharField(max_length=20, choices=ScopeType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='scoped_tasks',
    )
    group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
    )
    cohort = models.ForeignKey(
        'cohorts.Cohort',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
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

    @property
    def is_personal(self):
        return self.scope_type == self.ScopeType.USER

    def owner_user(self):
        return self.assignee or self.created_by

    def clean(self):
        errors = {}
        if self.scope_type == self.ScopeType.USER:
            if not self.user_id:
                errors['user'] = 'User is required for user-scoped tasks.'
            if self.group_id or self.cohort_id:
                errors['scope_type'] = 'Only user should be set for user scope.'
        elif self.scope_type == self.ScopeType.GROUP:
            if not self.group_id:
                errors['group'] = 'Group is required for group-scoped tasks.'
            if self.user_id or self.cohort_id:
                errors['scope_type'] = 'Only group should be set for group scope.'
        elif self.scope_type == self.ScopeType.COHORT:
            if not self.cohort_id:
                errors['cohort'] = 'Cohort is required for cohort-scoped tasks.'
            if self.user_id or self.group_id:
                errors['scope_type'] = 'Only cohort should be set for cohort scope.'

        # Private visibility is allowed for all scope types.

        if self.parent_id is not None:
            if self.pk and self.parent_id == self.pk:
                errors['parent'] = 'A task cannot be its own parent.'
            parent = self.parent
            if parent and parent.scope_type != self.scope_type:
                errors['parent'] = 'Subtask must belong to the same scope as parent.'
            if parent and self.scope_type == self.ScopeType.USER and parent.user_id != self.user_id:
                errors['parent'] = 'Subtask must belong to the same user as parent.'
            if parent and self.scope_type == self.ScopeType.GROUP and parent.group_id != self.group_id:
                errors['parent'] = 'Subtask must belong to the same group as parent.'
            if parent and self.scope_type == self.ScopeType.COHORT and parent.cohort_id != self.cohort_id:
                errors['parent'] = 'Subtask must belong to the same cohort as parent.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
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
