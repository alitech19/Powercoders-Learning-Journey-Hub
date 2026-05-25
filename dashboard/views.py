from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from cohorts.models import Group
from tracker.models import Task
from tracker.permissions import (
    get_teacher_group_ids,
    user_is_admin,
    user_is_teacher,
    visible_tasks_queryset,
    wrap_tasks_for_display,
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
            scope_type=Task.ScopeType.USER,
        )
        context.update(
            {
                'assigned_groups': assigned_groups,
                'public_task_rows': wrap_tasks_for_display(user, public_tasks),
                'private_metadata_rows': wrap_tasks_for_display(user, private_tasks),
                'tasks_by_status': _tasks_by_status(public_tasks),
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    # Student (default)
    own_tasks = visible_tasks_queryset(user).filter(
        scope_type=Task.ScopeType.USER,
        user=user,
    )
    group_tasks = visible_tasks_queryset(user).filter(
        scope_type=Task.ScopeType.GROUP,
    )
    cohort_tasks = visible_tasks_queryset(user).filter(
        scope_type=Task.ScopeType.COHORT,
    )

    context.update(
        {
            'own_task_rows': wrap_tasks_for_display(user, own_tasks),
            'group_task_rows': wrap_tasks_for_display(user, group_tasks),
            'cohort_task_rows': wrap_tasks_for_display(user, cohort_tasks),
            'tasks_by_status': _tasks_by_status(own_tasks),
        }
    )
    return render(request, 'dashboard/dashboard.html', context)
