from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

from config.input_limits import BODY_TEXT_MAX_LENGTH, RESOURCE_LABEL_MAX_LENGTH


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
        ]

    def __str__(self):
        preview = self.body[:50] if self.body else self.resource_label or 'Post'
        return f'[{self.group_space.group}] {preview}'

    @property
    def group(self):
        return self.group_space.group

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
