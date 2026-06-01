from django.test import TestCase

from resources.models import ResourceContainer, ResourceItem
from resources.services import ensure_system_group_container, sync_from_group_post
from test_utils.cohorts import make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.users import make_student


class ResourcesServicesTests(TestCase):
    def setUp(self):
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.student = make_student(
            's@example.com',
            group=self.group,
        )

    def test_ensure_system_group_container(self):
        container = ensure_system_group_container(self.group, created_by=self.student)
        self.assertTrue(container.is_system)
        self.assertEqual(container.container_type, ResourceContainer.ContainerType.GROUP)
        self.assertEqual(container.title, self.group.name)

    def test_sync_from_group_post_creates_item(self):
        post = make_post(
            self.space,
            self.student,
            body='Read https://example.com/guide',
            resource_label='Guide',
        )
        item = sync_from_group_post(post)
        self.assertIsNotNone(item)
        self.assertEqual(ResourceItem.objects.filter(source_post=post).count(), 1)
        self.assertEqual(item.url, 'https://example.com/guide')
        self.assertEqual(item.title, 'Guide')

    def test_sync_removes_item_when_post_no_longer_qualifies(self):
        post = make_post(
            self.space,
            self.student,
            body='https://example.com/x',
            resource_label='X',
        )
        sync_from_group_post(post)
        post.resource_label = ''
        post.save(update_fields=['resource_label'])
        sync_from_group_post(post)
        self.assertEqual(ResourceItem.objects.filter(source_post=post).count(), 0)

    def test_snapshot_post_does_not_sync(self):
        post = make_post(
            self.space,
            self.student,
            snapshot_html='<p>Goal done</p>',
            resource_label='Nope',
        )
        self.assertIsNone(sync_from_group_post(post))
