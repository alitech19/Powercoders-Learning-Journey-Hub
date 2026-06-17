from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from google_storage.crypto import decrypt_secret, encrypt_secret


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('display_name', 'Admin')
        if settings.DEBUG:
            extra_fields.setdefault('privacy_policy_accepted', True)
            extra_fields.setdefault('privacy_policy_accepted_at', timezone.now())
            extra_fields.setdefault('welcome_seen', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Login: email + password.
    Public identity: display_name + optional avatar (no legal name required).
    Cohort/group membership is added in a later migration when the cohorts app exists.
    """

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'
        ADMIN = 'admin', 'Admin'

    username = None
    email = models.EmailField('email address', unique=True)
    display_name = models.CharField(
        max_length=150,
        help_text='Name shown on the site (not your legal name).',
    )
    avatar_data = models.TextField(blank=True)
    avatar_content_type = models.CharField(max_length=64, blank=True)
    avatar_updated_at = models.DateTimeField(null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    email_notifications_enabled = models.BooleanField(default=True)
    privacy_policy_accepted = models.BooleanField(default=False)
    privacy_policy_accepted_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    welcome_seen = models.BooleanField(default=False)
    cohort = models.ForeignKey(
        'cohorts.Cohort',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    group = models.ForeignKey(
        'cohorts.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']

    objects = UserManager()

    DEFAULT_AVATAR_BY_ROLE = {
        Role.STUDENT: 'img/avatars/student.svg',
        Role.TEACHER: 'img/avatars/teacher.svg',
        Role.ADMIN: 'img/avatars/admin.svg',
    }

    def __str__(self):
        return self.display_name

    def clean(self):
        errors = {}
        if self.role == self.Role.STUDENT:
            if self.group_id and self.cohort_id and self.group.cohort_id != self.cohort_id:
                errors['cohort'] = "Cohort must match the selected group's cohort."
        elif self.role in (self.Role.TEACHER, self.Role.ADMIN):
            if self.cohort_id or self.group_id:
                errors['cohort'] = (
                    'Teachers and admins are not assigned to a cohort or group here. '
                    'Assign teachers via Group teachers in admin.'
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.role == self.Role.STUDENT and self.group_id:
            self.cohort = self.group.cohort
        if self.role in (self.Role.TEACHER, self.Role.ADMIN):
            self.cohort = None
            self.group = None
        if self.role == self.Role.STUDENT and bool(self.password):
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def has_custom_avatar(self):
        return bool(self.avatar_data)

    def clear_avatar(self):
        self.avatar_data = ''
        self.avatar_content_type = ''
        self.avatar_updated_at = None

    def get_default_avatar_path(self):
        return self.DEFAULT_AVATAR_BY_ROLE.get(
            self.role,
            self.DEFAULT_AVATAR_BY_ROLE[self.Role.STUDENT],
        )

    def get_avatar_url(self):
        if self.avatar_data:
            from django.urls import reverse

            url = reverse('accounts:avatar', args=[self.pk])
            if self.avatar_updated_at:
                url = f'{url}?v={int(self.avatar_updated_at.timestamp())}'
            return url
        from django.templatetags.static import static

        return static(self.get_default_avatar_path())


class Notification(models.Model):
    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f'→ {self.recipient}: {self.title}'


class UserNotificationSettings(models.Model):
    class DigestMode(models.TextChoices):
        INSTANT = 'instant', 'Instant'
        HOURLY = 'hourly', 'Hourly'
        DAILY = 'daily', 'Daily'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
    )
    slack_enabled = models.BooleanField(default=False)
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    # Legacy fields kept for migration compatibility.
    notify_new_workflow = models.BooleanField(default=True)
    notify_new_task = models.BooleanField(default=True)
    notify_new_goal = models.BooleanField(default=True)
    notify_feedback = models.BooleanField(default=True)
    notify_deadline_reminder = models.BooleanField(default=True)
    notify_group_chat_mentions = models.BooleanField(default=True)
    notify_group_chat_all_messages = models.BooleanField(default=False)
    email_new_workflow = models.BooleanField(default=True)
    email_new_task = models.BooleanField(default=True)
    email_new_goal = models.BooleanField(default=True)
    email_feedback = models.BooleanField(default=True)
    email_deadline_reminder = models.BooleanField(default=True)
    email_group_chat_mentions = models.BooleanField(default=True)
    email_group_chat_all_messages = models.BooleanField(default=False)
    slack_new_workflow = models.BooleanField(default=True)
    slack_new_task = models.BooleanField(default=True)
    slack_new_goal = models.BooleanField(default=True)
    slack_feedback = models.BooleanField(default=True)
    slack_deadline_reminder = models.BooleanField(default=True)
    slack_group_chat_mentions = models.BooleanField(default=True)
    slack_group_chat_all_messages = models.BooleanField(default=False)
    digest_mode = models.CharField(
        max_length=16,
        choices=DigestMode.choices,
        default=DigestMode.INSTANT,
    )
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default='Europe/Zurich')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'notification settings'
        verbose_name_plural = 'notification settings'

    def __str__(self):
        return f'Notification settings — {self.user.display_name}'


class NotificationDeliveryLog(models.Model):
    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'In-app'
        EMAIL = 'email', 'Email'
        SLACK = 'slack', 'Slack'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    event_key = models.CharField(max_length=255)
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_deliveries',
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'created_at'])]
        constraints = [
            models.UniqueConstraint(
                fields=['event_key', 'recipient', 'channel'],
                name='accounts_deliverylog_event_recipient_channel_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.channel} {self.status} — {self.recipient_id} ({self.event_key})'


class NotificationDigestItem(models.Model):
    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        SLACK = 'slack', 'Slack'

    class DigestBucket(models.TextChoices):
        HOURLY = 'hourly', 'Hourly'
        DAILY = 'daily', 'Daily'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_digest_items',
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    digest_bucket = models.CharField(max_length=16, choices=DigestBucket.choices)

    # We reuse the same dedupe_key from dispatch_event, so an event appears
    # at most once per (recipient, channel, digest_bucket).
    event_key = models.CharField(max_length=255)
    event_type = models.CharField(max_length=64, blank=True)

    title = models.CharField(max_length=255)
    # For email digests
    email_subject = models.CharField(max_length=255, blank=True)
    email_body = models.TextField(blank=True)
    # For Slack digests
    slack_text = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)

    scheduled_for = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['recipient', 'digest_bucket', 'scheduled_for', 'status']),
            models.Index(fields=['channel', 'digest_bucket', 'scheduled_for', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['event_key', 'recipient', 'channel', 'digest_bucket'],
                name='accounts_digestitem_event_recipient_channel_bucket_uniq',
            )
        ]

    def __str__(self):
        return f'DigestItem {self.channel} {self.digest_bucket} — {self.recipient_id} ({self.event_key})'


class SlackIntegration(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='slack_integration',
    )
    is_active = models.BooleanField(default=True)
    slack_user_id = models.CharField(max_length=64)
    slack_team_id = models.CharField(max_length=64)
    access_token_encrypted = models.TextField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['slack_team_id', 'slack_user_id'],
                name='accounts_slack_team_user_uniq',
            ),
        ]

    def __str__(self):
        return f'Slack — {self.user.display_name}'

    @property
    def is_connected(self):
        return self.is_active and self.disconnected_at is None and bool(self.access_token_encrypted)

    def set_access_token(self, token: str) -> None:
        self.access_token_encrypted = encrypt_secret(token) if token else ''

    def get_access_token(self) -> str:
        return decrypt_secret(self.access_token_encrypted)

    def mark_disconnected(self) -> None:
        self.is_active = False
        self.disconnected_at = timezone.now()
        self.access_token_encrypted = ''
        self.save(
            update_fields=[
                'is_active',
                'disconnected_at',
                'access_token_encrypted',
            ],
        )


class AuditLog(models.Model):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    user_email = models.EmailField(blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['user', 'timestamp'])]

    def __str__(self):
        who = self.user_email or (self.user.display_name if self.user_id else 'anonymous')
        return f'{self.method} {self.path} — {who}'
