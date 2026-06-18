from unittest.mock import patch

from django.test import TestCase, override_settings

from group_space.models import Post, SpaceSlackChannel
from group_space.slack_mapping import save_space_slack_mapping
from group_space.slack_sync import (
    capture_slack_delete_target,
    deliver_post_delete_from_slack,
    deliver_post_to_slack_channel,
    deliver_post_update_to_slack_channel,
    enqueue_slack_channel_sync,
    enqueue_slack_post_lifecycle_sync,
    should_sync_post_to_slack,
    should_sync_post_update_to_slack,
)
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

    @patch('group_space.slack_sync.post_channel_message', return_value='1234.5679')
    def test_deliver_reply_uses_parent_thread_ts(self, mock_post):
        parent = make_post(self.space, self.student, body='Parent')
        parent.slack_channel_id = 'C123TEST'
        parent.slack_ts = '1000.0000'
        parent.save(update_fields=['slack_channel_id', 'slack_ts'])
        reply = make_post(self.space, self.student, body='Child reply')
        reply.reply_to_post = parent
        reply.save(update_fields=['reply_to_post'])
        self.assertTrue(deliver_post_to_slack_channel(reply.pk))
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs['thread_ts'], '1000.0000')
        reply.refresh_from_db()
        self.assertEqual(reply.slack_thread_ts, '1000.0000')

    @patch('group_space.slack_sync.update_channel_message', return_value='1234.5678')
    def test_deliver_update_syncs_edited_body(self, mock_update):
        post = make_post(self.space, self.student, body='Original')
        post.slack_channel_id = 'C123TEST'
        post.slack_ts = '1234.5678'
        post.save(update_fields=['slack_channel_id', 'slack_ts'])
        post.body = 'Updated'
        post.save(update_fields=['body'])
        self.assertTrue(should_sync_post_update_to_slack(post))
        self.assertTrue(deliver_post_update_to_slack_channel(post.pk))
        mock_update.assert_called_once()

    @patch('group_space.tasks.sync_post_update_to_slack_channel_task.delay')
    def test_enqueue_lifecycle_routes_update_when_slack_ts_set(self, mock_update_delay):
        post = make_post(self.space, self.student, body='Already synced')
        post.slack_channel_id = 'C123TEST'
        post.slack_ts = '99.99'
        post.save(update_fields=['slack_channel_id', 'slack_ts'])
        enqueue_slack_post_lifecycle_sync(post)
        mock_update_delay.assert_called_once_with(post.pk)

    @patch('group_space.slack_sync.delete_channel_message')
    def test_deliver_delete_calls_slack_api(self, mock_delete):
        self.assertTrue(deliver_post_delete_from_slack('C123TEST', '55.55'))
        mock_delete.assert_called_once()

    def test_capture_delete_target_when_synced(self):
        post = make_post(self.space, self.student, body='Gone')
        post.slack_channel_id = 'C123TEST'
        post.slack_ts = '77.77'
        post.save(update_fields=['slack_channel_id', 'slack_ts'])
        target = capture_slack_delete_target(post)
        self.assertIsNotNone(target)
        self.assertEqual(target.channel_id, 'C123TEST')
        self.assertEqual(target.slack_ts, '77.77')

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
