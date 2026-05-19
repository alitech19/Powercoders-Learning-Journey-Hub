from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Students usually have cohort and group.
    Teachers access groups via cohorts.GroupTeacher.
    Admins typically do not need cohort or group.
    """

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
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

    def __str__(self):
        return self.username
