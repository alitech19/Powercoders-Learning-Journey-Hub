from django.test import TestCase

from group_space.permissions import (
    can_access_group,
    can_delete_post,
    can_edit_post,
    can_pin_post,
    get_accessible_groups,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.users import make_admin, make_student, make_teacher


class GroupSpacePermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.other = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('t@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            's@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.space = get_space_for_group(self.group)
        self.admin = make_admin('a@example.com')

    def test_student_accesses_own_group_only(self):
        self.assertTrue(can_access_group(self.student, self.group))
        self.assertFalse(can_access_group(self.student, self.other))
        groups = get_accessible_groups(self.student)
        self.assertEqual(len(groups), 1)

    def test_teacher_accesses_assigned_group(self):
        self.assertTrue(can_access_group(self.teacher, self.group))

    def test_author_edits_own_post(self):
        post = make_post(self.space, self.student)
        self.assertTrue(can_edit_post(self.student, post))
        self.assertTrue(can_delete_post(self.student, post))

    def test_teacher_can_delete_student_post(self):
        post = make_post(self.space, self.student)
        self.assertTrue(can_delete_post(self.teacher, post))
        self.assertTrue(can_pin_post(self.teacher, post))

    def test_admin_sees_all_groups(self):
        self.assertEqual(len(get_accessible_groups(self.admin)), 2)
