from django.test import Client, TestCase
from django.urls import reverse

from group_space.models import ProjectSpace, ProjectSpaceMembership
from group_space.permissions import can_access_space, can_post_in_space
from group_space.space import SpaceRef, get_accessible_spaces
from resources.models import ResourceContainer
from resources.services import ensure_system_project_container, sync_from_space_post
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import add_project_member, get_space_for_group, make_post, make_project_space
from test_utils.users import login_as, make_admin, make_student, make_teacher


class ProjectSpaceAccessTests(TestCase):
    def setUp(self):
        self.cohort_a = make_cohort(name='Cohort A')
        self.cohort_b = make_cohort(name='Cohort B')
        self.group_a = make_group(self.cohort_a, name='Group A')
        self.group_b = make_group(self.cohort_b, name='Group B')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group_a, self.teacher)
        self.admin = make_admin('admin@example.com')
        self.student_a = make_student('student-a@example.com', cohort=self.cohort_a, group=self.group_a)
        self.student_b = make_student('student-b@example.com', cohort=self.cohort_b, group=self.group_b)
        self.project = make_project_space(self.admin, title='Cross-cohort project')
        add_project_member(self.project, self.student_a)
        add_project_member(self.project, self.student_b)
        add_project_member(
            self.project,
            self.teacher,
            role=ProjectSpaceMembership.Role.MODERATOR,
            added_by=self.admin,
        )

    def test_students_from_two_cohorts_share_project_chat(self):
        login_as(self.client, self.student_a)
        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'space_kind': 'project',
                'space_pk': self.project.pk,
                'body': 'Hello from cohort A',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.project.posts.count(), 1)

    def test_admin_can_access_without_membership(self):
        ref = SpaceRef(
            kind='project',
            pk=self.project.pk,
            label=self.project.title,
            subtitle='',
            sort_key=(1, self.project.created_at, self.project.pk),
        )
        self.assertTrue(can_access_space(self.admin, ref))
        self.assertTrue(can_post_in_space(self.admin, ref))

    def test_archived_project_hidden_from_chat_picker(self):
        self.project.is_archived = True
        self.project.save(update_fields=['is_archived'])
        spaces = get_accessible_spaces(self.student_a)
        project_refs = [s for s in spaces if s.kind == 'project']
        self.assertEqual(project_refs, [])

    def test_archived_project_hidden_from_admin_group_spaces_list(self):
        from group_space.permissions import get_listable_project_spaces

        self.project.is_archived = True
        self.project.save(update_fields=['is_archived'])
        listed = list(get_listable_project_spaces(self.admin))
        self.assertNotIn(self.project, listed)

    def test_archived_project_is_read_only(self):
        self.project.is_archived = True
        self.project.save(update_fields=['is_archived'])
        ref = SpaceRef(
            kind='project',
            pk=self.project.pk,
            label=self.project.title,
            subtitle='',
            sort_key=(1, self.project.created_at, self.project.pk),
            is_archived=True,
        )
        self.assertFalse(can_post_in_space(self.student_a, ref))

    def test_picker_orders_cohort_group_before_custom_space(self):
        spaces = get_accessible_spaces(self.student_a)
        self.assertGreaterEqual(len(spaces), 2)
        self.assertEqual(spaces[0].kind, 'cohort_group')
        self.assertEqual(spaces[1].kind, 'project')

    def test_admin_post_in_custom_space_not_visible_in_cohort_chat(self):
        cohort = make_cohort(name='Bern cohort')
        bern_group = make_group(cohort, name='Bern')
        bern_space = get_space_for_group(bern_group)
        custom = make_project_space(self.admin, title='Custom collab')
        login_as(self.client, self.admin)
        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'space_kind': 'project',
                'space_pk': custom.pk,
                'body': 'Only in custom space',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(custom.posts.count(), 1)
        self.assertEqual(bern_space.posts.count(), 0)

    def test_post_with_mismatched_space_params_is_rejected(self):
        login_as(self.client, self.admin)
        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'space_kind': 'project',
                'space_pk': 99999,
                'body': 'Should not save',
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.project.posts.count(), 0)

    def test_project_post_syncs_to_resources(self):
        post = make_post(
            project_space=self.project,
            author=self.student_a,
            body='https://example.com/doc',
            resource_label='Shared doc',
        )
        ensure_system_project_container(self.project, created_by=self.admin)
        item = sync_from_space_post(post)
        self.assertIsNotNone(item)
        self.assertEqual(item.container.container_type, ResourceContainer.ContainerType.PROJECT)


class ProjectSpaceCrudTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin('crud-admin@example.com')
        self.teacher = make_teacher('crud-teacher@example.com')

    def test_admin_creates_and_adds_members(self):
        login_as(self.client, self.admin)
        response = self.client.post(
            reverse('group_space:project_create'),
            {'title': 'Sprint team', 'description': 'Two-week collab'},
        )
        self.assertEqual(response.status_code, 302)
        project = ProjectSpace.objects.get(title='Sprint team')
        self.assertEqual(project.title, 'Sprint team')
        self.assertEqual(project.created_by_id, self.admin.pk)

        cohort = make_cohort()
        group = make_group(cohort)
        student = make_student('member@example.com', cohort=cohort, group=group)
        response = self.client.post(
            reverse('group_space:project_member_add', args=[project.pk]),
            {
                'assignee_type': 'group',
                'assignee_target_id': str(group.pk),
                'student_ids': [str(student.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(project.memberships.filter(user=student).exists())

    def test_admin_bulk_adds_students_with_select_all(self):
        login_as(self.client, self.admin)
        project = make_project_space(self.admin, title='Team space')
        cohort = make_cohort()
        group = make_group(cohort)
        first = make_student('first@example.com', cohort=cohort, group=group)
        second = make_student('second@example.com', cohort=cohort, group=group)

        response = self.client.post(
            reverse('group_space:project_member_add', args=[project.pk]),
            {
                'assignee_type': 'group',
                'assignee_target_id': str(group.pk),
                'select_all_students': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        member_ids = set(project.memberships.values_list('user_id', flat=True))
        self.assertEqual(member_ids, {first.pk, second.pk})

    def test_admin_adds_teacher_as_moderator(self):
        login_as(self.client, self.admin)
        project = make_project_space(self.admin, title='Moderated space')
        response = self.client.post(
            reverse('group_space:project_member_add', args=[project.pk]),
            {'user_id': self.teacher.pk},
        )
        self.assertEqual(response.status_code, 302)
        membership = project.memberships.get(user=self.teacher)
        self.assertEqual(membership.role, ProjectSpaceMembership.Role.MODERATOR)

    def test_teacher_cannot_open_group_spaces_admin(self):
        login_as(self.client, self.teacher)
        response = self.client.get(reverse('group_space:project_list'))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_open_group_spaces_admin(self):
        student = make_student('no-admin@example.com')
        login_as(self.client, student)
        response = self.client.get(reverse('group_space:project_list'))
        self.assertEqual(response.status_code, 302)
