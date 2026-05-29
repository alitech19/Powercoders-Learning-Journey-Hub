from django.contrib.auth.models import AbstractUser, BaseUserManager
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
