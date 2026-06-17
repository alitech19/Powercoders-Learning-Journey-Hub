from unittest.mock import patch

from django.test import TestCase, override_settings

from group_space.models import Post, SpaceSlackChannel
from group_space.slack_mapping import save_space_slack_mapping
from group_space.slack_sync import deliver_post_to_slack_channel, enqueue_slack_channel_sync, should_sync_post_to_slack
from test_utils.cohorts import make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.slack import clear_slack_workspace_config, configure_slack_bot
from test_utils.users import make_student


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class SlackChannelSyncTests(TestCase):
    def setUp(self):
        clear_slack_workspace_config()
        configure_slack_bot()
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.student = make_student('sync@example.com', group=self.group)
        save_space_slack_mapping(
            group_space=self.space,
            channel_id='C123TEST',
            enabled=True,
        )

    def test_should_sync_when_mapped_and_configured(self):
        post = make_post(self.space, self.student, body='Hello Slack')
        self.assertTrue(should_sync_post_to_slack(post))

    def test_skips_without_mapping(self):
        SpaceSlackChannel.objects.all().delete()
        post = make_post(self.space, self.student, body='No mapping')
        self.assertFalse(should_sync_post_to_slack(post))

    @patch('group_space.slack_sync.post_channel_message', return_value='1234.5678')
    def test_deliver_post_sets_slack_ts(self, mock_post):
        post = make_post(self.space, self.student, body='Sync me')
        self.assertTrue(deliver_post_to_slack_channel(post.pk))
        post.refresh_from_db()
        self.assertEqual(post.slack_ts, '1234.5678')
        self.assertEqual(post.slack_channel_id, 'C123TEST')
        mock_post.assert_called_once()

    @patch('group_space.tasks.sync_post_to_slack_channel_task.delay')
    def test_enqueue_from_after_post_saved(self, mock_delay):
        from group_space.services import after_post_saved

        post = make_post(self.space, self.student, body='Queued')
        after_post_saved(post)
        mock_delay.assert_called_once_with(post.pk)

    def test_skips_slack_origin_posts(self):
        post = make_post(self.space, self.student, body='From slack')
        post.source_system = Post.SourceSystem.SLACK
        post.save(update_fields=['source_system'])
        self.assertFalse(should_sync_post_to_slack(post))
