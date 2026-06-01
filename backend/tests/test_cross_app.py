"""Flows that span multiple Django apps."""

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from group_space.services import after_post_saved
from journal.models import JournalEntry
from resources.models import ResourceItem
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.goals import make_student_goal
from test_utils.users import login_as, make_admin, make_student, make_teacher


class GroupPostToResourcesTests(TestCase):
    def test_after_post_saved_creates_resource_item_for_link_post(self):
        group = make_group(make_cohort())
        space = get_space_for_group(group)
        student = make_student('gs@example.com', group=group)
        post = make_post(
            space,
            student,
            body='See https://docs.example.com/readme',
            resource_label='Docs',
        )
        after_post_saved(post)
        item = ResourceItem.objects.get(source_post=post)
        self.assertEqual(item.title, 'Docs')
        self.assertEqual(item.url, 'https://docs.example.com/readme')
        self.assertEqual(item.created_by_id, student.pk)

    def test_message_create_view_syncs_resources(self):
        group = make_group(make_cohort())
        student = make_student('chat@example.com', group=group)
        client = Client()
        login_as(client, student)
        response = client.post(
            reverse('group_space:message_create'),
            {
                'group_pk': group.pk,
                'body': 'Link https://example.com/tutorial',
                'resource_label': 'Tutorial',
            },
        )
        self.assertEqual(response.status_code, 200)
        item = ResourceItem.objects.filter(
            url='https://example.com/tutorial',
            created_by=student,
        )
        self.assertEqual(item.count(), 1)


class DashboardCrossAppTests(TestCase):
    def test_teacher_dashboard_shows_student_from_group_with_journal_activity(self):
        cohort = make_cohort()
        group = make_group(cohort)
        teacher = make_teacher('dash-t@example.com')
        assign_teacher(group, teacher)
        student = make_student(
            'dash-s@example.com',
            display_name='Dash Student',
            cohort=cohort,
            group=group,
        )
        JournalEntry.objects.create(
            author=student,
            title='Week log',
            content='Learning Django',
            entry_date=timezone.now().date(),
        )
        make_student_goal(student, title='Ship project')

        client = Client()
        login_as(client, teacher)
        response = client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dash Student')
        self.assertContains(response, 'Student overview')

    def test_admin_dashboard_includes_journal_week_metric(self):
        admin = make_admin('metrics-admin@example.com')
        student = make_student('metrics@example.com')
        JournalEntry.objects.create(
            author=student,
            title='Recent',
            content='x',
            entry_date=timezone.now().date(),
            created_at=timezone.now(),
        )

        client = Client()
        login_as(client, admin)
        response = client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Journal Entries')
        self.assertContains(response, 'Admin Dashboard')
