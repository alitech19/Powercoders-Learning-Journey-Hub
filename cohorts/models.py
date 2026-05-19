from django.conf import settings
from django.db import models


class Cohort(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'

    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'name']

    def __str__(self):
        return self.name


class Group(models.Model):
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name='groups',
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['cohort', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['cohort', 'name'],
                name='unique_group_name_per_cohort',
            ),
        ]

    def __str__(self):
        return f'{self.cohort.name} — {self.name}'


class GroupTeacher(models.Model):
    class Role(models.TextChoices):
        MENTOR = 'mentor', 'Mentor'
        TEACHER = 'teacher', 'Teacher'
        ASSISTANT = 'assistant', 'Assistant'
        OBSERVER = 'observer', 'Observer'

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='group_teachers',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_teacher_assignments',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TEACHER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['group', 'teacher']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'teacher'],
                name='unique_teacher_per_group',
            ),
        ]

    def __str__(self):
        return f'{self.teacher} → {self.group} ({self.get_role_display()})'
