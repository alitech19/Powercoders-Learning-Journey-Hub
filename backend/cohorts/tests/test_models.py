from django.db import IntegrityError
from django.test import TestCase

from cohorts.models import Cohort, Group, GroupTeacher
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import make_teacher


class CohortModelTests(TestCase):
    def test_str(self):
        cohort = make_cohort(name='Spring 2026')
        self.assertEqual(str(cohort), 'Spring 2026')


class GroupModelTests(TestCase):
    def test_str_includes_cohort_and_group_name(self):
        cohort = make_cohort(name='C1')
        group = make_group(cohort, name='G1')
        self.assertEqual(str(group), 'C1 — G1')

    def test_unique_name_per_cohort(self):
        cohort = make_cohort()
        make_group(cohort, name='Alpha')
        with self.assertRaises(IntegrityError):
            make_group(cohort, name='Alpha')


class GroupTeacherModelTests(TestCase):
    def test_unique_teacher_per_group(self):
        cohort = make_cohort()
        group = make_group(cohort)
        teacher = make_teacher('t@example.com')
        assign_teacher(group, teacher)
        with self.assertRaises(IntegrityError):
            assign_teacher(group, teacher)

    def test_str_contains_teacher_group_and_role(self):
        cohort = make_cohort()
        group = make_group(cohort, name='G2')
        teacher = make_teacher('t2@example.com', display_name='Tea')
        gt = assign_teacher(group, teacher, role=GroupTeacher.Role.MENTOR)
        text = str(gt)
        self.assertIn('Tea', text)
        self.assertIn('G2', text)
        self.assertIn('Mentor', text)
