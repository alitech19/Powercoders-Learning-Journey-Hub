"""
Load development cohorts, groups, and users from backend/dev/seed.yaml.

DEV ONLY — disable before production deploy.
See docs/PRODUCTION_CHECKLIST.md
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.dev_seed import (
    allowed_dev_login_emails,
    apply_dev_user_security_bypass,
    load_seed_data,
    resolve_group,
    seed_file_path,
)
from cohorts.models import Cohort, Group, GroupTeacher


class Command(BaseCommand):
    help = 'Seed development cohorts, groups, and users from backend/dev/seed.yaml.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                'Refusing to seed dev data when DEBUG=False. '
                'See docs/PRODUCTION_CHECKLIST.md'
            )

        if not settings.ENABLE_DEV_SEED:
            self.stdout.write(
                self.style.WARNING('Dev seed skipped (ENABLE_DEV_SEED is False).')
            )
            return

        if not seed_file_path().is_file():
            raise CommandError(f'Seed file not found: {seed_file_path()}')

        data = load_seed_data()
        User = get_user_model()

        with transaction.atomic():
            groups_map = self._seed_cohorts_and_groups(data)
            student_count = self._seed_students(data, User, groups_map)
            teacher_count = self._seed_teachers(data, User, groups_map)

        load_seed_data.cache_clear()
        allowed_dev_login_emails.cache_clear()

        self.stdout.write(
            self.style.SUCCESS(
                f'Dev seed complete: {student_count} students, {teacher_count} teachers.'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                'REMINDER: Disable ENABLE_DEV_SEED and remove seed_dev_data from '
                'production deploy. See docs/PRODUCTION_CHECKLIST.md'
            )
        )

    def _seed_cohorts_and_groups(self, data: dict) -> dict:
        groups_map = {}
        for cohort_data in data.get('cohorts', []):
            cohort, _ = Cohort.objects.update_or_create(
                name=cohort_data['name'],
                defaults={
                    'start_date': cohort_data['start_date'],
                    'end_date': cohort_data.get('end_date'),
                    'status': cohort_data.get('status', Cohort.Status.PLANNED),
                },
            )
            for group_data in cohort_data.get('groups', []):
                group, _ = Group.objects.update_or_create(
                    cohort=cohort,
                    name=group_data['name'],
                    defaults={},
                )
                groups_map[(cohort_data['slug'], group_data['slug'])] = group
        return groups_map

    def _seed_students(self, data: dict, user_model, groups_map: dict) -> int:
        count = 0
        for entry in data.get('students', []):
            group = resolve_group(groups_map, entry['cohort'], entry['group'])
            user, _ = user_model.objects.get_or_create(
                email=entry['email'],
                defaults={
                    'display_name': entry['display_name'],
                    'role': user_model.Role.STUDENT,
                    'is_active': True,
                },
            )
            user.display_name = entry['display_name']
            user.role = user_model.Role.STUDENT
            user.is_active = True
            user.set_password(entry['password'])
            user.group = group
            user.cohort = group.cohort
            apply_dev_user_security_bypass(user)
            user.save()
            count += 1
        return count

    def _seed_teachers(self, data: dict, user_model, groups_map: dict) -> int:
        count = 0
        for entry in data.get('teachers', []):
            user, _ = user_model.objects.get_or_create(
                email=entry['email'],
                defaults={
                    'display_name': entry['display_name'],
                    'role': user_model.Role.TEACHER,
                    'is_active': True,
                },
            )
            user.display_name = entry['display_name']
            user.role = user_model.Role.TEACHER
            user.is_active = True
            user.set_password(entry['password'])
            user.cohort = None
            user.group = None
            apply_dev_user_security_bypass(user)
            user.save()

            assigned_group_ids = set()
            for ref in entry.get('groups', []):
                group = resolve_group(groups_map, ref['cohort'], ref['group'])
                assigned_group_ids.add(group.pk)
                GroupTeacher.objects.update_or_create(
                    group=group,
                    teacher=user,
                    defaults={'role': GroupTeacher.Role.TEACHER},
                )

            user.group_teacher_assignments.exclude(group_id__in=assigned_group_ids).delete()
            count += 1
        return count
