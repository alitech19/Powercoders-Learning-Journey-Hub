from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from cohorts.models import Cohort, Group
from tracker.models import Task
from tracker.permissions import (
    get_teacher_cohort_ids,
    get_teacher_group_ids,
    get_visible_tasks_for_user,
    user_is_admin,
    user_is_teacher,
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
        visible = get_visible_tasks_for_user(user)
        context.update(
            {
                'task_rows': wrap_tasks_for_display(user, visible),
                'tasks_by_status': _tasks_by_status(visible),
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        cohort_ids = get_teacher_cohort_ids(user)
        assigned_groups = Group.objects.filter(pk__in=group_ids).select_related('cohort')
        assigned_cohorts = Cohort.objects.filter(pk__in=cohort_ids)
        visible = get_visible_tasks_for_user(user)
        context.update(
            {
                'assigned_groups': assigned_groups,
                'assigned_cohorts': assigned_cohorts,
                'task_rows': wrap_tasks_for_display(user, visible),
                'tasks_by_status': _tasks_by_status(visible),
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    # Student (default)
    visible = get_visible_tasks_for_user(user)
    own_tasks = visible.filter(assignee_type=Task.AssigneeType.USER, assignee_user=user)
    group_tasks = visible.filter(assignee_type=Task.AssigneeType.GROUP)
    cohort_tasks = visible.filter(assignee_type=Task.AssigneeType.COHORT)

    context.update(
        {
            'own_task_rows': wrap_tasks_for_display(user, own_tasks),
            'group_task_rows': wrap_tasks_for_display(user, group_tasks),
            'cohort_task_rows': wrap_tasks_for_display(user, cohort_tasks),
            'tasks_by_status': _tasks_by_status(own_tasks),
        }
    )
    return render(request, 'dashboard/dashboard.html', context)
