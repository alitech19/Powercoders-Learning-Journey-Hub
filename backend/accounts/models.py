from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


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
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True)
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
        return bool(self.avatar)

    def get_default_avatar_path(self):
        return self.DEFAULT_AVATAR_BY_ROLE.get(
            self.role,
            self.DEFAULT_AVATAR_BY_ROLE[self.Role.STUDENT],
        )

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
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
