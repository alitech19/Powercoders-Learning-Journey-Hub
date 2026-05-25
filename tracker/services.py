from collections import defaultdict

from .models import TaskComment


def build_comment_tree(task):
    """
    Load all task comments once and attach .tree_replies for nested templates.
    """
    comments = list(
        TaskComment.objects.filter(task=task)
        .select_related('author', 'parent')
        .order_by('created_at')
    )
    children_by_parent = defaultdict(list)
    for comment in comments:
        children_by_parent[comment.parent_id].append(comment)

    def attach_children(comment):
        comment.tree_replies = children_by_parent.get(comment.pk, [])
        for child in comment.tree_replies:
            attach_children(child)

    roots = children_by_parent[None]
    for root in roots:
        attach_children(root)
    return roots
