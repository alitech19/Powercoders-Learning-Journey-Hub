"""
Create or update development users, cohort, group, and GroupTeacher relation.

Safe to run multiple times (idempotent).
Skips entirely when DEBUG=False or ENABLE_DEV_LOGIN is not True.
"""

import os
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cohorts.models import Cohort, Group, GroupTeacher


class Command(BaseCommand):
    help = 'Create or update development users and demo data (DEV ONLY).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(self.style.WARNING('Skipping: DEBUG is False.'))
            return

        if not getattr(settings, 'ENABLE_DEV_LOGIN', False):
            self.stdout.write(self.style.WARNING('Skipping: ENABLE_DEV_LOGIN is not True.'))
            return

        User = get_user_model()

        cohort_name = os.environ.get('DEV_COHORT_NAME', 'Demo Cohort')
        group_name = os.environ.get('DEV_GROUP_NAME', 'Demo Group')

        # Cohort
        cohort, _ = Cohort.objects.update_or_create(
            name=cohort_name,
            defaults={
                'start_date': date.today(),
                'status': Cohort.Status.ACTIVE,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Cohort: {cohort.name}'))

        # Group
        group, _ = Group.objects.update_or_create(
            cohort=cohort,
            name=group_name,
        )
        self.stdout.write(self.style.SUCCESS(f'Group: {group}'))

        # Student
        student = self._upsert_user(
            User,
            email=os.environ.get('DEV_STUDENT_EMAIL', 'student@example.com'),
            display_name=os.environ.get('DEV_STUDENT_DISPLAY_NAME', 'Student'),
            password=os.environ.get('DEV_STUDENT_PASSWORD', 'student12345'),
            role=User.Role.STUDENT,
            cohort=cohort,
            group=group,
            is_staff=False,
            is_superuser=False,
        )
        self.stdout.write(self.style.SUCCESS(f'Student: {student.email}'))

        # Teacher
        teacher = self._upsert_user(
            User,
            email=os.environ.get('DEV_TEACHER_EMAIL', 'teacher@example.com'),
            display_name=os.environ.get('DEV_TEACHER_DISPLAY_NAME', 'Teacher'),
            password=os.environ.get('DEV_TEACHER_PASSWORD', 'teacher12345'),
            role=User.Role.TEACHER,
            cohort=None,
            group=None,
            is_staff=False,
            is_superuser=False,
        )
        self.stdout.write(self.style.SUCCESS(f'Teacher: {teacher.email}'))

        # Admin
        admin_user = self._upsert_user(
            User,
            email=os.environ.get('DEV_ADMIN_EMAIL', 'admin@example.com'),
            display_name=os.environ.get('DEV_ADMIN_DISPLAY_NAME', 'Admin'),
            password=os.environ.get('DEV_ADMIN_PASSWORD', 'admin12345'),
            role=User.Role.ADMIN,
            cohort=None,
            group=None,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Admin: {admin_user.email}'))

        # GroupTeacher relation
        GroupTeacher.objects.get_or_create(
            group=group,
            teacher=teacher,
            defaults={'role': GroupTeacher.Role.TEACHER},
        )
        self.stdout.write(self.style.SUCCESS(f'GroupTeacher: {teacher.email} → {group}'))

        self.stdout.write(self.style.SUCCESS('\nDev users ready. Quick login enabled.'))

    def _upsert_user(self, User, *, email, display_name, password, role, cohort, group, is_staff, is_superuser):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'display_name': display_name,
                'role': role,
                'cohort': cohort,
                'group': group,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
                'is_active': True,
            },
        )
        user.display_name = display_name
        user.role = role
        user.cohort = cohort
        user.group = group
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = True
        user.set_password(password)
        user.save()
        return user
