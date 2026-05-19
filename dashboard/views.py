from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from tracker.models import Task, TaskBoard


@login_required
def dashboard(request):
    tasks_by_status = (
        Task.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    context = {
        'total_boards': TaskBoard.objects.count(),
        'total_tasks': Task.objects.count(),
        'tasks_by_status': {row['status']: row['count'] for row in tasks_by_status},
    }
    return render(request, 'dashboard/dashboard.html', context)
