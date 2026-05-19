from .models import TaskBoard


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
            'title': f'{user.username} personal board',
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
