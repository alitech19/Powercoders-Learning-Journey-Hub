import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import SlackIntegration
from accounts.slack_events import verify_slack_signature
from group_space.models import Post, SlackPendingReply
from group_space.slack_ingest import (
    ingest_slack_message_changed,
    ingest_slack_message_deleted,
    ingest_slack_message_event,
    should_ignore_slack_message_event,
)
from group_space.slack_sync import reconcile_pending_slack_replies
from test_utils.cohorts import make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.slack import clear_slack_workspace_config, configure_slack_bot
from test_utils.users import make_student


def _sign_payload(*, secret: str, payload: dict) -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    sig_basestring = f'v0:{timestamp}:{body.decode()}'
    digest = hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    headers = {
        'HTTP_X_SLACK_REQUEST_TIMESTAMP': timestamp,
        'HTTP_X_SLACK_SIGNATURE': f'v0={digest}',
        'CONTENT_TYPE': 'application/json',
    }
    return body, headers


class SlackSignatureTests(TestCase):
    def test_valid_signature(self):
        body = b'{"hello": "world"}'
        ts = str(int(time.time()))
        digest = hmac.new(
            b'secret',
            f'v0:{ts}:{body.decode()}'.encode(),
            hashlib.sha256,
        ).hexdigest()
        verify_slack_signature(
            signing_secret='secret',
            body=body,
            timestamp_header=ts,
            signature_header=f'v0={digest}',
        )


class SlackIngestTests(TestCase):
    def setUp(self):
        clear_slack_workspace_config()
        configure_slack_bot()
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.student = make_student('slack-in@example.com', group=self.group)
        from group_space.slack_mapping import save_space_slack_mapping

        save_space_slack_mapping(group_space=self.space, channel_id='CINGEST', enabled=True)
        SlackIntegration.objects.create(
            user=self.student,
            slack_user_id='USLACKUSER',
            slack_team_id='TTEAM',
            is_active=True,
        )
        integration = self.student.slack_integration
        integration.set_access_token('xoxp-user')
        integration.save()

    def test_ingest_creates_post_from_slack(self):
        post = ingest_slack_message_event({
            'type': 'message',
            'channel': 'CINGEST',
            'user': 'USLACKUSER',
            'text': 'From Slack',
            'ts': '111.222',
        })
        self.assertIsNotNone(post)
        self.assertEqual(post.body, 'From Slack')
        self.assertEqual(post.source_system, Post.SourceSystem.SLACK)

    def test_thread_reply_links_parent(self):
        parent = make_post(self.space, self.student, body='Parent')
        parent.slack_channel_id = 'CINGEST'
        parent.slack_ts = '100.000'
        parent.save(update_fields=['slack_channel_id', 'slack_ts'])
        reply = ingest_slack_message_event({
            'type': 'message',
            'channel': 'CINGEST',
            'user': 'USLACKUSER',
            'text': 'Reply text',
            'ts': '100.001',
            'thread_ts': '100.000',
        })
        self.assertEqual(reply.reply_to_post_id, parent.pk)

    def test_pending_reply_reconciled_when_parent_gets_slack_ts(self):
        SlackPendingReply.objects.create(
            slack_channel_id='CINGEST',
            slack_ts='200.001',
            slack_thread_ts='200.000',
            slack_user_id='USLACKUSER',
            text='Late reply',
        )
        parent = make_post(self.space, self.student, body='Later parent')
        parent.slack_channel_id = 'CINGEST'
        parent.slack_ts = '200.000'
        parent.save(update_fields=['slack_channel_id', 'slack_ts'])
        created = reconcile_pending_slack_replies('CINGEST', '200.000')
        self.assertEqual(created, 1)
        self.assertTrue(Post.objects.filter(body='Late reply').exists())

    def test_ignore_bot_messages(self):
        self.assertTrue(should_ignore_slack_message_event({'type': 'message', 'bot_id': 'B1', 'text': 'x'}))

    def test_ingest_message_changed_updates_slack_origin_post(self):
        post = make_post(self.space, self.student, body='Old text')
        post.source_system = Post.SourceSystem.SLACK
        post.slack_channel_id = 'CINGEST'
        post.slack_ts = '300.300'
        post.save(update_fields=['source_system', 'slack_channel_id', 'slack_ts'])
        updated = ingest_slack_message_changed({
            'type': 'message',
            'subtype': 'message_changed',
            'channel': 'CINGEST',
            'message': {'ts': '300.300', 'text': 'New text'},
        })
        self.assertIsNotNone(updated)
        post.refresh_from_db()
        self.assertEqual(post.body, 'New text')

    def test_ingest_message_changed_ignores_powerhub_origin(self):
        post = make_post(self.space, self.student, body='PH text')
        post.slack_channel_id = 'CINGEST'
        post.slack_ts = '301.301'
        post.save(update_fields=['slack_channel_id', 'slack_ts'])
        self.assertIsNone(ingest_slack_message_changed({
            'type': 'message',
            'subtype': 'message_changed',
            'channel': 'CINGEST',
            'message': {'ts': '301.301', 'text': 'Echo from bot'},
        }))
        post.refresh_from_db()
        self.assertEqual(post.body, 'PH text')

    def test_ingest_message_deleted_removes_post(self):
        post = make_post(self.space, self.student, body='Delete me')
        post.slack_channel_id = 'CINGEST'
        post.slack_ts = '400.400'
        post.save(update_fields=['slack_channel_id', 'slack_ts'])
        self.assertTrue(ingest_slack_message_deleted({
            'type': 'message',
            'subtype': 'message_deleted',
            'channel': 'CINGEST',
            'deleted_ts': '400.400',
        }))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())


class SlackEventsEndpointTests(TestCase):
    def setUp(self):
        clear_slack_workspace_config()
        configure_slack_bot(signing_secret='endpoint-secret')
        self.client = Client()

    def test_url_verification_challenge(self):
        payload = {'type': 'url_verification', 'challenge': 'challenge-token'}
        body, headers = _sign_payload(secret='endpoint-secret', payload=payload)
        response = self.client.post(
            reverse('accounts:slack_events'),
            data=body,
            content_type='application/json',
            **headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['challenge'], 'challenge-token')

    @patch('group_space.slack_ingest.ingest_slack_message_event')
    def test_event_callback_invokes_ingest(self, mock_ingest):
        payload = {
            'type': 'event_callback',
            'event': {
                'type': 'message',
                'channel': 'C1',
                'user': 'U1',
                'text': 'hi',
                'ts': '1.2',
            },
        }
        body, headers = _sign_payload(secret='endpoint-secret', payload=payload)
        response = self.client.post(
            reverse('accounts:slack_events'),
            data=body,
            content_type='application/json',
            **headers,
        )
        self.assertEqual(response.status_code, 200)
        mock_ingest.assert_called_once()
