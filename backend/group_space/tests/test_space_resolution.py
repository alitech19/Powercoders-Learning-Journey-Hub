from django.test import Client, TestCase
from django.urls import reverse

from group_space.models import Post
from group_space.space import resolve_space_from_request
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post, make_project_space
from test_utils.users import login_as, make_admin, make_student, make_teacher


class ResolveSpaceFromRequestTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort(name='Cohort A')
        self.group_a = make_group(self.cohort, name='Group A')
        self.group_b = make_group(self.cohort, name='Group B')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group_a, self.teacher)
        assign_teacher(self.group_b, self.teacher)

    def test_feed_url_kind_space_params_select_correct_cohort_group(self):
        ref = resolve_space_from_request(
            self.teacher,
            {'kind': 'cohort_group', 'space': str(self.group_b.pk)},
        )
        self.assertIsNotNone(ref)
        self.assertEqual(ref.kind, 'cohort_group')
        self.assertEqual(ref.pk, self.group_b.pk)

    def test_legacy_group_param_still_works(self):
        ref = resolve_space_from_request(self.teacher, {'group': str(self.group_b.pk)})
        self.assertEqual(ref.pk, self.group_b.pk)


class FeedSpaceSwitchingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cohort = make_cohort(name='Bern cohort')
        self.bern = make_group(self.cohort, name='Bern')
        self.other = make_group(self.cohort, name='Zurich')
        self.bern_space = get_space_for_group(self.bern)
        self.other_space = get_space_for_group(self.other)
        self.teacher = make_teacher('switch@example.com')
        assign_teacher(self.bern, self.teacher)
        assign_teacher(self.other, self.teacher)
        make_post(self.bern_space, self.teacher, body='Bern only message')
        make_post(self.other_space, self.teacher, body='Zurich only message')

    def test_teacher_feed_shows_only_selected_cohort_group(self):
        login_as(self.client, self.teacher)
        response = self.client.get(
            reverse('group_space:feed'),
            {'kind': 'cohort_group', 'space': self.other.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zurich only message')
        self.assertNotContains(response, 'Bern only message')

    def test_teacher_post_goes_to_selected_group_not_first_in_list(self):
        login_as(self.client, self.teacher)
        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'space_kind': 'cohort_group',
                'space_pk': self.other.pk,
                'body': 'Posted to Zurich',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.other_space.posts.filter(body='Posted to Zurich').count(), 1)
        self.assertEqual(self.bern_space.posts.filter(body='Posted to Zurich').count(), 0)


class AdminProjectFeedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cohort = make_cohort(name='Bern cohort')
        self.bern = make_group(self.cohort, name='Bern')
        self.bern_space = get_space_for_group(self.bern)
        self.admin = make_admin('admin@example.com')
        self.project = make_project_space(self.admin, title='Custom collab')
        make_post(self.bern_space, self.admin, body='Bern chat line')
        make_post(project_space=self.project, author=self.admin, body='Custom chat line')

    def test_admin_feed_project_url_shows_project_chat_only(self):
        login_as(self.client, self.admin)
        response = self.client.get(
            reverse('group_space:feed'),
            {'kind': 'project', 'space': self.project.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom chat line')
        self.assertNotContains(response, 'Bern chat line')
        self.assertContains(response, 'Custom group space')

    def test_admin_composer_on_project_feed_posts_to_project(self):
        login_as(self.client, self.admin)
        response = self.client.get(
            reverse('group_space:feed'),
            {'kind': 'project', 'space': self.project.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="space_kind" value="project"')
        self.assertContains(response, f'name="space_pk" value="{self.project.pk}"')

        response = self.client.post(
            reverse('group_space:message_create'),
            {
                'space_kind': 'project',
                'space_pk': self.project.pk,
                'body': 'New custom-only post',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(body='New custom-only post', group_space=self.bern_space).exists())
        self.assertTrue(Post.objects.filter(body='New custom-only post', project_space=self.project).exists())
