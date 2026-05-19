from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from cohorts.models import Group
from tracker.models import Task, TaskBoard
from tracker.permissions import (
    user_is_admin,
    user_is_student,
    user_is_teacher,
    visible_tasks_queryset,
    wrap_tasks_for_display,
    get_teacher_group_ids,
)
from tracker.services import (
    get_or_create_cohort_board,
    get_or_create_group_board,
    get_or_create_personal_board,
)


def _tasks_by_status(qs):
    rows = qs.values('status').annotate(count=Count('id')).order_by('status')
    return {row['status']: row['count'] for row in rows}


@login_required
def dashboard(request):
    user = request.user
    context = {
        'role': user.get_role_display(),
    }

    if user_is_admin(user):
        all_tasks = Task.objects.filter(parent__isnull=True)
        context.update(
            {
                'private_metadata_rows': wrap_tasks_for_display(
                    user,
                    all_tasks.filter(visibility=Task.Visibility.PRIVATE),
                ),
                'public_task_rows': wrap_tasks_for_display(
                    user,
                    all_tasks.filter(visibility=Task.Visibility.PUBLIC),
                ),
                'total_boards': TaskBoard.objects.count(),
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        assigned_groups = Group.objects.filter(pk__in=group_ids).select_related('cohort')
        visible = visible_tasks_queryset(user)
        public_tasks = visible.filter(visibility=Task.Visibility.PUBLIC)
        private_tasks = visible.filter(
            visibility=Task.Visibility.PRIVATE,
            board__scope_type=TaskBoard.ScopeType.USER,
        )
        context.update(
            {
                'assigned_groups': assigned_groups,
                'public_task_rows': wrap_tasks_for_display(user, public_tasks),
                'private_metadata_rows': wrap_tasks_for_display(user, private_tasks),
                'tasks_by_status': _tasks_by_status(public_tasks),
                'group_boards': [
                    get_or_create_group_board(g, created_by=user) for g in assigned_groups
                ],
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    # Student (default)
    personal_board = get_or_create_personal_board(user)
    group_board = (
        get_or_create_group_board(user.group, created_by=user) if user.group_id else None
    )
    cohort_board = (
        get_or_create_cohort_board(user.cohort, created_by=user) if user.cohort_id else None
    )

    own_tasks = visible_tasks_queryset(user).filter(
        board__scope_type=TaskBoard.ScopeType.USER,
        board__user=user,
    )
    group_tasks = visible_tasks_queryset(user).filter(
        board__scope_type=TaskBoard.ScopeType.GROUP,
    )
    cohort_tasks = visible_tasks_queryset(user).filter(
        board__scope_type=TaskBoard.ScopeType.COHORT,
    )

    context.update(
        {
            'personal_board': personal_board,
            'group_board': group_board,
            'cohort_board': cohort_board,
            'own_task_rows': wrap_tasks_for_display(user, own_tasks),
            'group_task_rows': wrap_tasks_for_display(user, group_tasks),
            'cohort_task_rows': wrap_tasks_for_display(user, cohort_tasks),
            'tasks_by_status': _tasks_by_status(own_tasks),
        }
    )
    return render(request, 'dashboard/dashboard.html', context)
