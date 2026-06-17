"""Notifications for teachers and admins about student activity and platform ops."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import User

from .constants import EventType
from .dispatcher import dispatch_event

UserModel = get_user_model()


def get_teachers_for_student(student):
    if not student.group_id:
        return []
    return list(
        UserModel.objects.filter(
            is_active=True,
            role=User.Role.TEACHER,
            group_teacher_assignments__group_id=student.group_id,
        ).distinct()
    )


def get_student_oversight_recipients(student):
    """Teachers assigned to the student's group plus all active admins."""
    recipients = {user.pk: user for user in get_teachers_for_student(student)}
    for admin in get_active_admins():
        recipients[admin.pk] = admin
    return list(recipients.values())


def get_active_admins(*, exclude_user=None):
    qs = UserModel.objects.filter(is_active=True, role=User.Role.ADMIN)
    if exclude_user is not None:
        qs = qs.exclude(pk=exclude_user.pk)
    return list(qs)


def _student_group_label(student):
    if student.group_id:
        return student.group.name
    if student.cohort_id:
        return student.cohort.name
    return 'your cohort'


def _dispatch_staff_event(
    *,
    event_type,
    recipients,
    title,
    body,
    url,
    dedupe_key,
    email_subject,
    slack_text,
):
    if not recipients:
        return
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    for recipient in recipients:
        full_url = f'{site}{url}' if url and site else url
        email_body = '\n'.join(
            [
                f'Hi {recipient.display_name},',
                '',
                body,
                '',
                f'Open in PowerHUB: {full_url}' if full_url else '',
                '',
                '— Powercoders Team',
            ]
        ).strip()
        dispatch_event(
            event_type=event_type,
            recipients=[recipient],
            title=title,
            body=body,
            url=url,
            dedupe_key=f'{dedupe_key}:{recipient.pk}',
            email_subject=email_subject,
            email_body=email_body,
            slack_text=slack_text,
        )


def notify_student_task_completed(*, student, task):
    recipients = get_student_oversight_recipients(student)
    if not recipients:
        return
    title = f'{student.display_name} completed a task'
    body = (
        f'{student.display_name} ({_student_group_label(student)}) marked '
        f'"{task.title}" as done.'
    )
    url = reverse('tasks:task_detail', args=[task.pk])
    _dispatch_staff_event(
        event_type=EventType.STUDENT_TASK_COMPLETED,
        recipients=recipients,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'student-task-done:{student.pk}:{task.pk}',
        email_subject=title,
        slack_text=f'✅ {body}',
    )


def notify_student_goal_completed(*, student, goal):
    recipients = get_student_oversight_recipients(student)
    if not recipients:
        return
    title = f'{student.display_name} completed a goal'
    body = (
        f'{student.display_name} ({_student_group_label(student)}) achieved '
        f'the goal "{goal.title}".'
    )
    url = reverse('goals:detail', args=[goal.pk])
    _dispatch_staff_event(
        event_type=EventType.STUDENT_GOAL_COMPLETED,
        recipients=recipients,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'student-goal-done:{student.pk}:{goal.pk}',
        email_subject=title,
        slack_text=f'🎯 {body}',
    )


def notify_student_workflow_completed(*, student, workflow):
    recipients = get_student_oversight_recipients(student)
    if not recipients:
        return
    title = f'{student.display_name} completed a workflow'
    body = (
        f'{student.display_name} ({_student_group_label(student)}) finished '
        f'the workflow "{workflow.title}".'
    )
    url = reverse('workflows:detail', args=[workflow.pk])
    _dispatch_staff_event(
        event_type=EventType.STUDENT_WORKFLOW_COMPLETED,
        recipients=recipients,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'student-workflow-done:{student.pk}:{workflow.pk}',
        email_subject=title,
        slack_text=f'🧭 {body}',
    )


def notify_student_reflection_submitted(*, student, reflection):
    recipients = get_student_oversight_recipients(student)
    if not recipients:
        return
    title = f'{student.display_name} submitted a reflection'
    body = (
        f'{student.display_name} ({_student_group_label(student)}) submitted '
        f'their weekly reflection.'
    )
    url = reverse('reflections:detail', args=[reflection.pk])
    _dispatch_staff_event(
        event_type=EventType.STUDENT_REFLECTION_SUBMITTED,
        recipients=recipients,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'student-reflection:{student.pk}:{reflection.pk}',
        email_subject=title,
        slack_text=f'📝 {body}',
    )


def notify_student_deadline_overdue(*, student, kind, item_id, title, detail_url, dedupe_day):
    recipients = get_student_oversight_recipients(student)
    if not recipients:
        return
    kind_label = 'task' if kind == 'task' else 'goal'
    notif_title = f'{student.display_name} missed a {kind_label} deadline'
    body = (
        f'{student.display_name} ({_student_group_label(student)}) is overdue on '
        f'{kind_label} "{title}".'
    )
    _dispatch_staff_event(
        event_type=EventType.STUDENT_DEADLINE_OVERDUE,
        recipients=recipients,
        title=notif_title,
        body=body,
        url=detail_url,
        dedupe_key=f'student-overdue:{kind}:{item_id}:{student.pk}:{dedupe_day}',
        email_subject=notif_title,
        slack_text=f'⏰ {body}',
    )


def notify_bug_report_new(*, report):
    admins = get_active_admins()
    if not admins:
        return
    reporter = report.reporter
    title = f'New bug report #{report.pk}'
    body = (
        f'{reporter.display_name} ({reporter.email}) reported an issue.\n\n'
        f'Page: {report.page_url}\n\n'
        f'{report.description}'
    )
    url = reverse('bug_reports:report_detail', args=[report.pk])
    _dispatch_staff_event(
        event_type=EventType.BUG_REPORT_NEW,
        recipients=admins,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'bug-report-new:{report.pk}',
        email_subject=title,
        slack_text=f'🐛 {title} from {reporter.display_name}',
    )


def notify_bug_report_reopened(*, report):
    admins = get_active_admins()
    if not admins:
        return
    reporter = report.reporter
    title = f'Bug report #{report.pk} reopened'
    body = f'Bug report #{report.pk} from {reporter.display_name} was reopened for review.'
    url = reverse('bug_reports:report_detail', args=[report.pk])
    _dispatch_staff_event(
        event_type=EventType.BUG_REPORT_REOPENED,
        recipients=admins,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'bug-report-reopened:{report.pk}',
        email_subject=title,
        slack_text=f'🔄 {title}',
    )


def notify_new_user_account(*, created_user, created_by=None):
    admins = get_active_admins(exclude_user=created_by)
    if not admins:
        return
    title = f'New {created_user.get_role_display().lower()} account: {created_user.display_name}'
    group_part = ''
    if created_user.group_id:
        group_part = f' · {created_user.group.name}'
    elif created_user.cohort_id:
        group_part = f' · {created_user.cohort.name}'
    body = (
        f'Account created for {created_user.display_name} ({created_user.email})'
        f'{group_part}.'
    )
    if created_by is not None:
        body += f'\n\nCreated by {created_by.display_name}.'
    url = reverse('accounts:user_list')
    _dispatch_staff_event(
        event_type=EventType.NEW_USER_ACCOUNT,
        recipients=admins,
        title=title,
        body=body,
        url=url,
        dedupe_key=f'new-user:{created_user.pk}',
        email_subject=title,
        slack_text=f'👤 {title}',
    )


def maybe_notify_workflow_completed(*, workflow, student):
    if workflow.is_shared or student.role != User.Role.STUDENT:
        return
    from workflows.models import WorkflowEnrollment

    enrollment = WorkflowEnrollment.objects.filter(
        workflow=workflow,
        student=student,
    ).first()
    if not enrollment or enrollment.progress_pct() < 100:
        return
    notify_student_workflow_completed(student=student, workflow=workflow)
