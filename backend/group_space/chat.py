from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .models import Comment, GroupSpace, Post


@dataclass(frozen=True)
class ChatItem:
    """One row in the group chat timeline."""

    kind: Literal['post', 'comment']
    created_at: datetime
    post: Post | None = None
    comment: Comment | None = None

    @property
    def author(self):
        if self.kind == 'comment' and self.comment:
            return self.comment.author
        if self.post:
            return self.post.author
        raise AttributeError('ChatItem has no author')

    @property
    def pk(self):
        if self.kind == 'comment' and self.comment:
            return self.comment.pk
        if self.post:
            return self.post.pk
        raise AttributeError('ChatItem has no pk')


def build_chat_timeline(group_space: GroupSpace):
    """Chronological chat stream (oldest → newest). Pinned posts shown separately."""
    posts = list(
        Post.objects.filter(group_space=group_space)
        .select_related('author')
        .prefetch_related('comments__author')
        .order_by('created_at')
    )
    pinned = [p for p in posts if p.pinned]
    items: list[ChatItem] = []
    for post in posts:
        items.append(ChatItem(kind='post', created_at=post.created_at, post=post))
        for comment in post.comments.all():
            items.append(
                ChatItem(kind='comment', created_at=comment.created_at, post=post, comment=comment),
            )
    items.sort(key=lambda item: item.created_at)
    return pinned, items
