from celery import shared_task


@shared_task
def notify_task_assigned_task(task_id, student_ids, actor_id):
    from accounts.models import User
    from accounts.notifications.entity_events import notify_task_assigned
    from tasks.models import Task

    task = Task.objects.get(pk=task_id)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_task_assigned(task=task, students=students, actor=actor)


@shared_task
def notify_goal_assigned_task(goal_id, student_ids, actor_id):
    from accounts.models import User
    from accounts.notifications.entity_events import notify_goal_assigned
    from goals.models import Goal

    goal = Goal.objects.get(pk=goal_id)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_goal_assigned(goal=goal, students=students, actor=actor)


@shared_task
def notify_workflow_assigned_task(workflow_id, student_ids, actor_id):
    from accounts.models import User
    from accounts.notifications.entity_events import notify_workflow_assigned
    from workflows.models import Workflow

    workflow = Workflow.objects.get(pk=workflow_id)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    notify_workflow_assigned(workflow=workflow, students=students, actor=actor)


@shared_task
def run_deadline_reminders_task():
    from accounts.notifications.deadline_reminders import send_deadline_reminders

    send_deadline_reminders()


@shared_task
def notify_missing_reflections():
    """Slack digest: students without a weekly reflection submitted this week."""
    from django.contrib.auth import get_user_model

    from dashboard.services import students_missing_weekly_reflection

    from .slack import send_slack_message

    User = get_user_model()
    students = list(
        User.objects.filter(role=User.Role.STUDENT, is_active=True).select_related('group')
    )
    missing = students_missing_weekly_reflection(students)
    if not missing:
        send_slack_message("✅ All students have submitted this week's reflection.")
        return

    count = len(missing)
    lines = '\n'.join(
        f'• {s.display_name} ({s.group.name if s.group else "no group"})' for s in missing
    )
    send_slack_message(
        f"⚠️ *{count} student{'s' if count != 1 else ''} missing this week's reflection:*\n{lines}"
    )
