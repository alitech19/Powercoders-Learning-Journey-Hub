from django.test import TestCase

from cohorts.permissions import (
    get_active_students_for_cohort,
    get_active_students_for_group,
    get_teacher_accessible_students,
    get_teacher_group_ids,
    user_is_admin,
    user_is_staff,
    user_is_student,
    user_is_teacher,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import make_admin, make_student, make_teacher


class RoleHelperTests(TestCase):
    def test_student_teacher_admin_flags(self):
        student = make_student('s@t.com')
        teacher = make_teacher('t@t.com')
        admin = make_admin('a@t.com')
        self.assertTrue(user_is_student(student))
        self.assertFalse(user_is_teacher(student))
        self.assertTrue(user_is_teacher(teacher))
        self.assertTrue(user_is_staff(teacher))
        self.assertTrue(user_is_admin(admin))

    def test_anonymous_not_staff(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(user_is_staff(AnonymousUser()))


class TeacherScopeTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group_a = make_group(self.cohort, name='A')
        self.group_b = make_group(self.cohort, name='B')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group_a, self.teacher)
        self.student_a = make_student(
            'sa@example.com',
            cohort=self.cohort,
            group=self.group_a,
        )
        self.student_b = make_student(
            'sb@example.com',
            cohort=self.cohort,
            group=self.group_b,
        )

    def test_teacher_group_ids_only_assigned(self):
        self.assertEqual(get_teacher_group_ids(self.teacher), [self.group_a.pk])

    def test_teacher_sees_only_assigned_group_students(self):
        qs = get_teacher_accessible_students(self.teacher)
        self.assertEqual(list(qs), [self.student_a])

    def test_active_students_for_group(self):
        qs = get_active_students_for_group(self.group_a)
        self.assertEqual(list(qs), [self.student_a])

    def test_active_students_for_cohort_requires_group(self):
        orphan = make_student(
            'orphan@example.com',
            cohort=self.cohort,
            group=None,
        )
        qs = get_active_students_for_cohort(self.cohort)
        pks = set(qs.values_list('pk', flat=True))
        self.assertIn(self.student_a.pk, pks)
        self.assertIn(self.student_b.pk, pks)
        self.assertNotIn(orphan.pk, pks)
