from django.http import Http404
from django.test import TestCase

from resources.models import ResourceContainer
from resources.permissions import (
    can_create_personal_container,
    can_create_thematic_container,
    can_delete_container,
    can_edit_container_items,
    can_view_container,
    get_container_or_404,
    get_item_or_404,
    resolve_selected_group,
)
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.resources import make_item, make_personal_container, make_thematic_container, system_group_container
from test_utils.users import make_admin, make_student, make_teacher


class ResourcesPermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.other_group = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.other_student = make_student(
            'other@example.com',
            cohort=self.cohort,
            group=self.other_group,
        )
        self.admin = make_admin('admin@example.com')

    def test_personal_container_only_owner_views_and_edits(self):
        personal = make_personal_container(self.student, title='Private')
        self.assertTrue(can_view_container(self.student, personal))
        self.assertTrue(can_edit_container_items(self.student, personal))
        self.assertFalse(can_view_container(self.other_student, personal))
        self.assertFalse(can_edit_container_items(self.teacher, personal))

    def test_group_system_container_visible_to_group_student(self):
        system = system_group_container(self.group, created_by=self.teacher)
        self.assertTrue(system.is_system)
        self.assertTrue(can_view_container(self.student, system))
        self.assertTrue(can_edit_container_items(self.student, system))
        self.assertFalse(can_view_container(self.other_student, system))

    def test_thematic_container_teacher_in_scope(self):
        thematic = make_thematic_container(self.group, self.teacher, title='Week 1')
        self.assertTrue(can_view_container(self.student, thematic))
        self.assertTrue(can_edit_container_items(self.teacher, thematic))
        self.assertTrue(can_delete_container(self.teacher, thematic))

    def test_student_creator_can_delete_own_thematic(self):
        thematic = make_thematic_container(self.group, self.student, title='Student theme')
        self.assertTrue(can_delete_container(self.student, thematic))

    def test_system_container_cannot_be_deleted(self):
        system = system_group_container(self.group, created_by=self.teacher)
        self.assertFalse(can_delete_container(self.teacher, system))

    def test_can_create_personal_any_authenticated(self):
        self.assertTrue(can_create_personal_container(self.student))

    def test_can_create_thematic_requires_staff_in_group(self):
        self.assertTrue(can_create_thematic_container(self.teacher, self.group))
        self.assertFalse(can_create_thematic_container(self.student, self.group))
        self.assertFalse(can_create_thematic_container(self.teacher, self.other_group))

    def test_get_container_or_404_denies_wrong_user(self):
        personal = make_personal_container(self.student)
        with self.assertRaises(Http404):
            get_container_or_404(self.other_student, personal.pk)

    def test_get_item_or_404_follows_container_access(self):
        personal = make_personal_container(self.student)
        item = make_item(personal, self.student, title='X', url='https://x.test')
        found = get_item_or_404(self.student, item.pk)
        self.assertEqual(found.pk, item.pk)
        with self.assertRaises(Http404):
            get_item_or_404(self.other_student, item.pk)

    def test_resolve_selected_group_student_defaults_to_own_group(self):
        selected, groups = resolve_selected_group(self.student, None)
        self.assertEqual(selected.pk, self.group.pk)
        self.assertEqual(len(groups), 1)

    def test_admin_cannot_view_others_personal_container(self):
        personal = make_personal_container(self.student)
        self.assertFalse(can_view_container(self.admin, personal))
        self.assertFalse(can_edit_container_items(self.admin, personal))
