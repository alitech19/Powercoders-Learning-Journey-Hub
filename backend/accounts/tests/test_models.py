from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import AuditLog, User
from test_utils.cohorts import make_cohort, make_group
from test_utils.users import make_student, make_teacher


class UserManagerTests(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='x', display_name='X')


class UserModelTests(TestCase):
    def test_str_uses_display_name(self):
        user = make_student('s@example.com', display_name='Sam')
        self.assertEqual(str(user), 'Sam')

    def test_student_cohort_synced_from_group_on_save(self):
        cohort = make_cohort()
        group = make_group(cohort)
        user = make_student('s@example.com', group=group)
        user.refresh_from_db()
        self.assertEqual(user.cohort_id, cohort.pk)

    def test_teacher_clears_cohort_and_group_on_save(self):
        cohort = make_cohort()
        group = make_group(cohort)
        teacher = make_teacher('t@example.com')
        teacher.cohort = cohort
        teacher.group = group
        teacher.save()
        teacher.refresh_from_db()
        self.assertIsNone(teacher.cohort_id)
        self.assertIsNone(teacher.group_id)

    def test_student_cohort_must_match_group_cohort(self):
        cohort_a = make_cohort(name='A')
        cohort_b = make_cohort(name='B')
        group = make_group(cohort_a)
        user = User(
            email='bad@example.com',
            display_name='Bad',
            role=User.Role.STUDENT,
        )
        user.set_password('test-pass-123')
        user.group = group
        user.cohort = cohort_b
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_get_avatar_url_default_when_no_upload(self):
        user = make_student('s@example.com')
        url = user.get_avatar_url()
        self.assertIn('student.svg', url)

    def test_has_custom_avatar_false_by_default(self):
        user = make_student('s@example.com')
        self.assertFalse(user.has_custom_avatar)


class AuditLogModelTests(TestCase):
    def test_str_uses_email_when_set(self):
        user = make_student('s@example.com')
        entry = AuditLog.objects.create(
            user=user,
            user_email=user.email,
            method='POST',
            path='/accounts/profile/',
        )
        self.assertIn('POST', str(entry))
        self.assertIn('/accounts/profile/', str(entry))
