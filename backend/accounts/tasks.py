from celery import shared_task


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
