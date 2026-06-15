import json

from django.conf import settings
from django.db import models

from .constants import ROOT_FOLDER_NAME
from .crypto import decrypt_secret, encrypt_secret, mask_secret


class GoogleWorkspaceStorageConfig(models.Model):
    """Singleton — all Google integration credentials live here (not in .env)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    is_enabled = models.BooleanField(
        default=False,
        help_text='Master switch for staff Shared drive uploads.',
    )

    # Org Shared drive (staff uploads via service account)
    shared_drive_id = models.CharField(max_length=128, blank=True)
    shared_drive_name = models.CharField(max_length=255, blank=True)
    shared_root_folder_id = models.CharField(max_length=128, blank=True)
    root_folder_name = models.CharField(max_length=128, default=ROOT_FOLDER_NAME)
    service_account_email = models.EmailField(blank=True, editable=False)
    service_account_json_encrypted = models.TextField(blank=True)

    # Student OAuth (My Drive uploads)
    student_oauth_enabled = models.BooleanField(default=False)
    oauth_client_id = models.CharField(max_length=255, blank=True)
    oauth_client_secret_encrypted = models.TextField(blank=True)
    oauth_redirect_uri = models.URLField(blank=True, max_length=512)
    workspace_hosted_domain = models.CharField(
        max_length=255,
        blank=True,
        help_text='Expected Google Workspace domain (e.g. powercoders.org).',
    )

    # Diagnostics
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    last_health_ok = models.BooleanField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='google_storage_config_updates',
    )

    class Meta:
        verbose_name = 'Google workspace storage'
        verbose_name_plural = 'Google workspace storage'

    def __str__(self):
        return 'Google workspace storage configuration'

    def save(self, *args, **kwargs):
        self.id = 1
        email = self._parse_service_account_email(self._service_account_json_plain)
        if email:
            self.service_account_email = email
        super().save(*args, **kwargs)

    @property
    def _service_account_json_plain(self) -> str:
        if hasattr(self, '_service_account_json_plain_cache'):
            return self._service_account_json_plain_cache
        return decrypt_secret(self.service_account_json_encrypted)

    def set_service_account_json(self, raw_json: str) -> None:
        raw_json = (raw_json or '').strip()
        self._service_account_json_plain_cache = raw_json
        self.service_account_json_encrypted = encrypt_secret(raw_json) if raw_json else ''

    def get_service_account_json(self) -> str:
        return decrypt_secret(self.service_account_json_encrypted)

    def set_oauth_client_secret(self, secret: str) -> None:
        secret = (secret or '').strip()
        self.oauth_client_secret_encrypted = encrypt_secret(secret) if secret else ''

    def get_oauth_client_secret(self) -> str:
        return decrypt_secret(self.oauth_client_secret_encrypted)

    @staticmethod
    def _parse_service_account_email(raw_json: str) -> str:
        if not raw_json:
            return ''
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return ''
        return (data.get('client_email') or '').strip()

    @property
    def masked_service_account_json(self) -> str:
        return mask_secret(self.get_service_account_json())

    @property
    def masked_oauth_client_secret(self) -> str:
        return mask_secret(self.get_oauth_client_secret())

    def staff_uploads_enabled(self) -> bool:
        return bool(
            self.is_enabled
            and self.shared_drive_id
            and self.service_account_json_encrypted
        )

    def student_uploads_enabled(self) -> bool:
        return bool(
            self.student_oauth_enabled
            and self.oauth_client_id
            and self.oauth_client_secret_encrypted
        )


class GoogleAccountConnection(models.Model):
    """Student Google OAuth connection for My Drive uploads."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_account_connection',
    )
    google_subject = models.CharField(max_length=128)
    google_email = models.EmailField()
    access_token_encrypted = models.TextField(blank=True)
    refresh_token_encrypted = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    root_folder_id = models.CharField(max_length=128, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['google_email']),
        ]

    def __str__(self):
        return f'Google — {self.google_email}'

    @property
    def is_active(self) -> bool:
        return self.disconnected_at is None and bool(self.refresh_token_encrypted)

    def set_tokens(self, *, access_token: str, refresh_token: str) -> None:
        self.access_token_encrypted = encrypt_secret(access_token or '')
        if refresh_token:
            self.refresh_token_encrypted = encrypt_secret(refresh_token)
        self.disconnected_at = None
        self.last_error = ''

    def get_access_token(self) -> str:
        return decrypt_secret(self.access_token_encrypted)

    def get_refresh_token(self) -> str:
        return decrypt_secret(self.refresh_token_encrypted)

    def mark_disconnected(self, error: str = '') -> None:
        from django.utils import timezone

        self.disconnected_at = timezone.now()
        self.last_error = error
        self.access_token_encrypted = ''
        self.refresh_token_encrypted = ''
        self.save(
            update_fields=[
                'disconnected_at',
                'last_error',
                'access_token_encrypted',
                'refresh_token_encrypted',
            ]
        )


class GoogleDriveFolder(models.Model):
    """Cache of created Drive folder ids (org Shared drive or student My Drive)."""

    class StorageBackend(models.TextChoices):
        SHARED_ORG = 'shared_org', 'Org Shared drive'
        PERSONAL = 'personal', 'My Drive'

    class FolderKind(models.TextChoices):
        ROOT = 'root', 'PowerHUB root'
        GROUP = 'group', 'Group folder'

    storage_backend = models.CharField(max_length=20, choices=StorageBackend.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='google_drive_folders',
    )
    folder_kind = models.CharField(max_length=20, choices=FolderKind.choices)
    group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='google_drive_folders',
    )
    drive_folder_id = models.CharField(max_length=128)
    drive_path = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['storage_backend', 'folder_kind', 'group'],
                condition=models.Q(storage_backend='shared_org'),
                name='google_storage_unique_shared_folder',
            ),
            models.UniqueConstraint(
                fields=['storage_backend', 'user', 'folder_kind', 'group'],
                condition=models.Q(storage_backend='personal'),
                name='google_storage_unique_personal_folder',
            ),
        ]
        indexes = [
            models.Index(fields=['storage_backend', 'folder_kind']),
        ]

    def __str__(self):
        return self.drive_path


class DriveUploadLog(models.Model):
    """Upload attempt audit trail."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    post = models.ForeignKey(
        'group_space.Post',
        on_delete=models.CASCADE,
        related_name='drive_upload_logs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='drive_upload_logs',
    )
    storage_backend = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'Upload log post={self.post_id} {self.status}'
