from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import Q

from config.input_limits import BODY_TEXT_MAX_LENGTH, RESOURCE_LABEL_MAX_LENGTH, TITLE_MAX_LENGTH


class GroupSpace(models.Model):
    """One chat space per cohort group — created when the group is created."""

    group = models.OneToOneField(
        'cohorts.Group',
        on_delete=models.CASCADE,
        related_name='group_space',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['group__cohort__name', 'group__name']

    def __str__(self):
        return f'Group Space — {self.group}'


class ProjectSpace(models.Model):
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_project_spaces',
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'pk']
        indexes = [
            models.Index(fields=['is_archived', 'title']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return self.title


class ProjectSpaceMembership(models.Model):
    class Role(models.TextChoices):
        MEMBER = 'member', 'Member'
        MODERATOR = 'moderator', 'Moderator'

    project_space = models.ForeignKey(
        ProjectSpace,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_space_memberships',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_memberships_added',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project_space', 'user'], name='group_space_unique_project_member'),
        ]
        indexes = [
            models.Index(fields=['project_space', 'role']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'{self.user} in {self.project_space}'


class Post(models.Model):
    class SnapshotKind(models.TextChoices):
        JOURNAL = 'journal', 'Journal entry'
        HABIT = 'habit', 'Habit'
        GOAL = 'goal', 'Goal'
        TASK = 'task', 'Task'

    class DriveStorageBackend(models.TextChoices):
        SHARED_ORG = 'shared_org', 'Org Shared drive'
        PERSONAL = 'personal', 'My Drive'

    class DriveUploadStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    class DriveDocKind(models.TextChoices):
        DOCUMENT = 'document', 'Google Doc'
        SPREADSHEET = 'spreadsheet', 'Google Sheet'
        PRESENTATION = 'presentation', 'Google Slides'
        FORM = 'form', 'Google Form'

    group_space = models.ForeignKey(
        GroupSpace,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )
    project_space = models.ForeignKey(
        ProjectSpace,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_posts',
    )
    body = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(BODY_TEXT_MAX_LENGTH)],
    )
    file = models.FileField(upload_to='group_files/%Y/%m/', null=True, blank=True)
    drive_storage_backend = models.CharField(
        max_length=20,
        choices=DriveStorageBackend.choices,
        blank=True,
    )
    drive_file_id = models.CharField(max_length=128, blank=True)
    drive_web_view_link = models.URLField(max_length=2048, blank=True)
    drive_upload_status = models.CharField(
        max_length=20,
        choices=DriveUploadStatus.choices,
        blank=True,
    )
    drive_upload_error = models.TextField(blank=True)
    drive_doc_kind = models.CharField(
        max_length=20,
        choices=DriveDocKind.choices,
        blank=True,
    )
    resource_label = models.CharField(
        max_length=RESOURCE_LABEL_MAX_LENGTH,
        blank=True,
        help_text='Required when the post includes a file or URL — title on Resources tiles.',
    )
    pinned = models.BooleanField(default=False)
    snapshot_kind = models.CharField(
        max_length=20,
        choices=SnapshotKind.choices,
        blank=True,
    )
    snapshot_html = models.TextField(blank=True)
    snapshot_meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group_space', 'created_at']),
            models.Index(fields=['group_space', 'pinned']),
            models.Index(fields=['project_space', 'created_at']),
            models.Index(fields=['project_space', 'pinned']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(group_space__isnull=False, project_space__isnull=True)
                    | Q(group_space__isnull=True, project_space__isnull=False)
                ),
                name='group_space_post_exactly_one_parent',
            ),
        ]

    def __str__(self):
        parent = self.group_space or self.project_space
        preview = self.body[:50] if self.body else self.resource_label or 'Post'
        return f'[{parent}] {preview}'

    @property
    def group(self):
        if self.group_space_id:
            return self.group_space.group
        return None

    @property
    def space_ref(self):
        from .space import post_space_ref

        return post_space_ref(self)

    @property
    def has_snapshot(self):
        return bool(self.snapshot_meta) or bool(self.snapshot_html)

    @property
    def has_file(self):
        return bool(self.file) or bool(self.drive_file_id)

    @property
    def has_drive_file(self):
        return bool(self.drive_file_id) or self.drive_upload_status in {
            self.DriveUploadStatus.PENDING,
            self.DriveUploadStatus.READY,
        }

    def clean(self):
        from django.core.exceptions import ValidationError

        from .services import detect_urls

        errors = {}
        has_content = bool(self.body.strip()) or bool(self.file) or self.has_snapshot
        if not has_content:
            errors['body'] = 'Post must include a message, file, or shared snapshot.'

        has_link_or_file = bool(self.file) or bool(detect_urls(self.body))
        if has_link_or_file and not self.has_snapshot and not self.resource_label.strip():
            errors['resource_label'] = 'Resource name is required when posting a file or link.'

        if errors:
            raise ValidationError(errors)

        if self.group_space_id or self.project_space_id:
            if bool(self.group_space_id) == bool(self.project_space_id):
                raise ValidationError('Post must belong to exactly one space.')


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_comments',
    )
    body = models.TextField(validators=[MaxLengthValidator(BODY_TEXT_MAX_LENGTH)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} on post {self.post_id}'
