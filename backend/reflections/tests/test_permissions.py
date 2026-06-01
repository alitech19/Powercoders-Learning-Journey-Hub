from django.test import TestCase

from reflections.constants import TAG_WEEKLY
from reflections.models import Reflection
from reflections.permissions import (
    can_create_reflections,
    can_view_reflection,
    filter_reflections_queryset,
    get_visible_reflections_for_user,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.reflections import make_reflection
from test_utils.users import make_admin, make_student, make_teacher


class ReflectionPermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.other_group = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('t@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            's@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.other = make_student(
            'o@example.com',
            cohort=self.cohort,
            group=self.other_group,
        )
        self.admin = make_admin('a@example.com')

    def test_student_views_own_reflection(self):
        r = make_reflection(self.student)
        self.assertTrue(can_view_reflection(self.student, r))

    def test_student_cannot_view_other_private(self):
        r = make_reflection(self.other)
        self.assertFalse(can_view_reflection(self.student, r))

    def test_teacher_views_shared_in_scope(self):
        r = make_reflection(
            self.student,
            visibility=Reflection.Visibility.SHARED,
        )
        self.assertTrue(can_view_reflection(self.teacher, r))

    def test_teacher_cannot_view_private(self):
        r = make_reflection(self.student, visibility=Reflection.Visibility.PRIVATE)
        self.assertFalse(can_view_reflection(self.teacher, r))

    def test_teacher_out_of_scope(self):
        r = make_reflection(
            self.other,
            visibility=Reflection.Visibility.SHARED,
        )
        self.assertFalse(can_view_reflection(self.teacher, r))

    def test_can_create_reflections_student_only(self):
        self.assertTrue(can_create_reflections(self.student))
        self.assertFalse(can_create_reflections(self.teacher))

    def test_filter_by_tag(self):
        make_reflection(self.student, tags=[TAG_WEEKLY], title='W')
        make_reflection(self.student, tags=['project'], title='P')
        qs = filter_reflections_queryset(
            get_visible_reflections_for_user(self.student),
            tag=TAG_WEEKLY,
        )
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().title, 'W')
