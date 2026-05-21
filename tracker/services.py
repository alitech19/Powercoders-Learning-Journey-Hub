from collections import defaultdict

from .models import TaskBoard, TaskComment


def get_or_create_personal_board(user):
    """
    User-scoped board for a student's personal tasks.

    Cohort/group membership lives on the User model; user-scoped boards
  only set scope_type=user and user=<student> (per TaskBoard validation).
    """
    board, _ = TaskBoard.objects.get_or_create(
        scope_type=TaskBoard.ScopeType.USER,
        user=user,
        defaults={
            'title': f'{user.display_name} personal board',
            'created_by': user,
        },
    )
    return board


def get_or_create_group_board(group, created_by=None):
    board, _ = TaskBoard.objects.get_or_create(
        scope_type=TaskBoard.ScopeType.GROUP,
        group=group,
        defaults={
            'title': f'{group.name} board',
            'created_by': created_by,
        },
    )
    return board


def get_or_create_cohort_board(cohort, created_by=None):
    board, _ = TaskBoard.objects.get_or_create(
        scope_type=TaskBoard.ScopeType.COHORT,
        cohort=cohort,
        defaults={
            'title': f'{cohort.name} board',
            'created_by': created_by,
        },
    )
    return board


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
