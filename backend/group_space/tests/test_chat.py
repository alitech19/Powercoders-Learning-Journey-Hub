from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from group_space.chat import ChatItem, build_chat_timeline
from test_utils.cohorts import make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_comment, make_post
from test_utils.users import make_student


def _set_created(obj, when):
    type(obj).objects.filter(pk=obj.pk).update(created_at=when)


class ChatItemTests(TestCase):
    def setUp(self):
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.student = make_student('s@example.com', group=self.group)
        self.other = make_student('o@example.com', group=self.group)

    def test_chat_item_post_author_and_pk(self):
        post = make_post(self.space, self.student, body='Hi')
        item = ChatItem(kind='post', created_at=post.created_at, post=post)
        self.assertEqual(item.author, self.student)
        self.assertEqual(item.pk, post.pk)

    def test_chat_item_comment_author_and_pk(self):
        post = make_post(self.space, self.student)
        comment = make_comment(post, self.other, body='Thanks')
        item = ChatItem(
            kind='comment',
            created_at=comment.created_at,
            post=post,
            comment=comment,
        )
        self.assertEqual(item.author, self.other)
        self.assertEqual(item.pk, comment.pk)


class BuildChatTimelineTests(TestCase):
    def setUp(self):
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.student = make_student('s@example.com', group=self.group)

    def test_empty_timeline(self):
        pinned, items = build_chat_timeline(self.space)
        self.assertEqual(pinned, [])
        self.assertEqual(items, [])

    def test_pinned_posts_listed_separately(self):
        pinned_post = make_post(self.space, self.student, body='Pinned', pinned=True)
        regular = make_post(self.space, self.student, body='Normal')
        pinned, items = build_chat_timeline(self.space)
        self.assertEqual([p.pk for p in pinned], [pinned_post.pk])
        post_items = [i for i in items if i.kind == 'post']
        self.assertEqual(len(post_items), 2)
        self.assertEqual({i.post.pk for i in post_items}, {pinned_post.pk, regular.pk})

    def test_timeline_sorted_by_created_at(self):
        base = timezone.now() - timedelta(hours=2)
        post_old = make_post(self.space, self.student, body='First')
        _set_created(post_old, base)
        post_new = make_post(self.space, self.student, body='Second')
        _set_created(post_new, base + timedelta(minutes=10))
        comment = make_comment(post_old, self.student, body='Late reply')
        _set_created(comment, base + timedelta(minutes=20))

        pinned, items = build_chat_timeline(self.space)
        self.assertEqual(pinned, [])
        self.assertEqual(
            [(i.kind, i.pk) for i in items],
            [
                ('post', post_old.pk),
                ('post', post_new.pk),
                ('comment', comment.pk),
            ],
        )
