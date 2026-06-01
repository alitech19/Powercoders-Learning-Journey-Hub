from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta

from cohorts.models import Cohort, Group
from cohorts.permissions import get_teacher_group_ids, user_is_admin, user_is_teacher
from group_space.models import Post
from journal.models import JournalEntry
from reflections.constants import TAG_WEEKLY
from reflections.models import Reflection
from tasks.models import Task

from accounts.student_oversight import build_student_progress_rows

from . import services

User = get_user_model()


@login_required
def dashboard(request):
    user = request.user
    if not user.welcome_seen:
        return redirect('accounts:welcome')

    context = {'role': user.get_role_display()}

    if user_is_admin(user):
        one_week_ago = timezone.now() - timedelta(days=7)
        context.update(
            {
                'total_students': User.objects.filter(role=User.Role.STUDENT).count(),
                'total_teachers': User.objects.filter(role=User.Role.TEACHER).count(),
                'total_cohorts': Cohort.objects.count(),
                'active_cohorts': Cohort.objects.filter(status=Cohort.Status.ACTIVE).count(),
                'total_groups': Group.objects.count(),
                'journal_week': JournalEntry.objects.filter(created_at__gte=one_week_ago).count(),
                **services.admin_extra_stats(),
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    if user_is_teacher(user):
        group_ids = get_teacher_group_ids(user)
        assigned_groups = Group.objects.filter(pk__in=group_ids).select_related('cohort')
        students_in_groups = User.objects.filter(
            role=User.Role.STUDENT,
            group_id__in=group_ids,
        ).select_related('group', 'cohort')
        missing_students = services.students_missing_weekly_reflection(students_in_groups)
        student_preview_rows = build_student_progress_rows(students_in_groups)[:10]

        one_week_ago = timezone.now() - timedelta(days=7)
        context.update(
            {
                'assigned_groups': assigned_groups,
                'missing_students': missing_students,
                'missing_count': len(missing_students),
                'student_count': students_in_groups.count(),
                'student_preview_rows': student_preview_rows,
                'group_posts_week': Post.objects.filter(
                    group_space__group_id__in=group_ids,
                    created_at__gte=one_week_ago,
                ).count()
                if group_ids
                else 0,
            }
        )
        return render(request, 'dashboard/dashboard.html', context)

    individual_tasks = services.tasks_for_kind(user, Task.ListKind.INDIVIDUAL)
    own_tasks = [
        task
        for task in individual_tasks
        if task.author_id == user.pk
        or task.enrollments.filter(student=user).exists()
    ]

    reflection_due = not services.user_has_weekly_reflection_this_week(user)
    last_reflection = (
        Reflection.objects.filter(author=user, tags__contains=[TAG_WEEKLY])
        .order_by('-final_reflection_at', '-updated_at')
        .values_list('final_reflection_at', flat=True)
        .first()
    )

    context.update(
        {
            'tasks_by_status': services.tasks_by_status_for_student(user, own_tasks),
            'journal_count': JournalEntry.objects.filter(author=user).count(),
            'recent_journal_entries': JournalEntry.objects.filter(author=user)
            .order_by('-entry_date')
            .values('pk', 'title', 'entry_date', 'mood')[:3],
            'reflections_count': Reflection.objects.filter(author=user).count(),
            'last_reflection': last_reflection,
            'reflection_due': reflection_due,
            **services.student_goal_stats(user),
            **services.student_habit_stats(user),
            **services.student_workflow_stats(user),
            **services.student_group_stats(user),
            **services.student_resource_stats(user),
        }
    )
    return render(request, 'dashboard/dashboard.html', context)
