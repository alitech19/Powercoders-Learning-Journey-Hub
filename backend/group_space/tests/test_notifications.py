from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from accounts.models import Notification, UserNotificationSettings
from accounts.notifications.constants import EventType
from accounts.notifications.settings import get_notification_settings
from group_space.notifications import notify_group_chat_post, parse_mentioned_users
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.users import make_student, make_teacher


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class GroupChatNotificationTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.author = make_student('author@example.com', group=self.group, display_name='Alice Author')
        self.mentioned = make_student(
            'mentioned@example.com',
            group=self.group,
            display_name='Bob Mentioned',
        )
        self.watcher = make_student(
            'watcher@example.com',
            group=self.group,
            display_name='Carol Watcher',
        )
        for student in (self.mentioned, self.watcher):
            settings = get_notification_settings(student)
            settings.notify_group_chat_mentions = True
            settings.email_group_chat_mentions = True
            settings.notify_group_chat_all_messages = True
            settings.email_group_chat_all_messages = True
            settings.slack_group_chat_mentions = False
            settings.slack_group_chat_all_messages = False
            settings.save()

    def test_parse_mention_by_display_name_and_email(self):
        participants = [self.mentioned, self.watcher]
        by_name = parse_mentioned_users('Hey @"Bob Mentioned"', participants)
        self.assertEqual(by_name, [self.mentioned])
        by_email = parse_mentioned_users('Ping @mentioned@example.com', participants)
        self.assertEqual(by_email, [self.mentioned])

    def test_notify_mention_creates_in_app_notification(self):
        settings = get_notification_settings(self.watcher)
        settings.notify_group_chat_all_messages = False
        settings.email_group_chat_all_messages = False
        settings.save(update_fields=['notify_group_chat_all_messages', 'email_group_chat_all_messages'])

        post = make_post(
            self.space,
            self.author,
            body='Hello @"Bob Mentioned"',
        )
        notify_group_chat_post(post)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.mentioned,
                title__icontains='mentioned you',
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.mentioned.email)

    def test_notify_all_messages_when_enabled(self):
        settings = get_notification_settings(self.watcher)
        settings.notify_group_chat_all_messages = True
        settings.email_group_chat_all_messages = True
        settings.save(update_fields=['notify_group_chat_all_messages', 'email_group_chat_all_messages'])

        post = make_post(self.space, self.author, body='General update')
        notify_group_chat_post(post)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.watcher,
                title__icontains='New message',
            ).exists()
        )

    def test_skips_author_and_does_not_email_when_all_messages_disabled(self):
        for student in (self.mentioned, self.watcher):
            settings = get_notification_settings(student)
            settings.notify_group_chat_all_messages = False
            settings.email_group_chat_all_messages = False
            settings.save(
                update_fields=['notify_group_chat_all_messages', 'email_group_chat_all_messages'],
            )

        post = make_post(self.space, self.author, body='No mentions here')
        notify_group_chat_post(post)

        self.assertFalse(Notification.objects.filter(recipient=self.author).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.watcher).exists())
        self.assertEqual(len(mail.outbox), 0)

    @patch('group_space.notifications.dispatch_event')
    def test_mention_takes_priority_over_all_messages(self, mock_dispatch):
        settings = get_notification_settings(self.mentioned)
        settings.email_group_chat_all_messages = True
        settings.save(update_fields=['email_group_chat_all_messages'])

        post = make_post(self.space, self.author, body='Hi @"Bob Mentioned"')
        notify_group_chat_post(post)

        mentioned_calls = [
            call
            for call in mock_dispatch.call_args_list
            if call.kwargs['recipients'] == [self.mentioned]
        ]
        self.assertEqual(len(mentioned_calls), 1)
        self.assertEqual(mentioned_calls[0].kwargs['event_type'], EventType.GROUP_CHAT_MENTION)

    def test_teacher_in_group_can_be_mentioned(self):
        teacher = make_teacher('teacher@example.com', display_name='Dana Teacher')
        assign_teacher(self.group, teacher)
        settings = get_notification_settings(teacher)
        settings.notify_group_chat_mentions = True
        settings.email_group_chat_mentions = True
        settings.save(update_fields=['notify_group_chat_mentions', 'email_group_chat_mentions'])

        post = make_post(self.space, self.author, body='Question for @"Dana Teacher"')
        notify_group_chat_post(post)

        self.assertTrue(
            Notification.objects.filter(recipient=teacher).exists()
        )
