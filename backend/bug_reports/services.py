from django.db import transaction
from django.utils import timezone

from .emails import notify_admin_reply, notify_report_created
from .models import BugReport, BugReportMessage


def _notify_admins_bug_report_new(report):
    from accounts.notifications.staff_events import notify_bug_report_new

    notify_bug_report_new(report=report)


def _notify_admins_bug_report_reopened(report):
    from accounts.notifications.staff_events import notify_bug_report_reopened

    notify_bug_report_reopened(report=report)


class BugReportWorkflowError(Exception):
    pass


def create_report(*, reporter, page_url, page_path, description, client_context=None):
    with transaction.atomic():
        report = BugReport.objects.create(
            reporter=reporter,
            page_url=page_url,
            page_path=page_path,
            description=description.strip(),
            client_context=client_context or {},
        )
    notify_report_created(report)
    _notify_admins_bug_report_new(report)
    return report


def take_report(*, report: BugReport, admin_user):
    if report.assigned_to_id and report.assigned_to_id != admin_user.pk:
        raise BugReportWorkflowError(
            f'Already handled by {report.assigned_to.display_name}.'
        )
    if report.status not in (
        BugReport.Status.SUBMITTED,
        BugReport.Status.REOPENED,
        BugReport.Status.IN_PROGRESS,
    ):
        raise BugReportWorkflowError('This report cannot be taken in its current status.')
    now = timezone.now()
    report.status = BugReport.Status.IN_PROGRESS
    report.assigned_to = admin_user
    report.assigned_at = now
    report.save(update_fields=['status', 'assigned_to', 'assigned_at', 'updated_at'])
    return report


def close_report(*, report: BugReport):
    now = timezone.now()
    report.status = BugReport.Status.CLOSED
    report.closed_at = now
    report.save(update_fields=['status', 'closed_at', 'updated_at'])
    return report


def reject_report(*, report: BugReport):
    now = timezone.now()
    report.status = BugReport.Status.REJECTED
    report.closed_at = now
    report.save(update_fields=['status', 'closed_at', 'updated_at'])
    return report


def reopen_report(*, report: BugReport):
    if report.status not in (BugReport.Status.CLOSED, BugReport.Status.REJECTED):
        raise BugReportWorkflowError('Only closed or rejected reports can be reopened.')
    report.status = BugReport.Status.REOPENED
    report.assigned_to = None
    report.assigned_at = None
    report.closed_at = None
    report.save(
        update_fields=[
            'status',
            'assigned_to',
            'assigned_at',
            'closed_at',
            'updated_at',
        ]
    )
    _notify_admins_bug_report_reopened(report)
    return report


def add_staff_reply(*, report: BugReport, author, body: str):
    message = BugReportMessage.objects.create(
        report=report,
        author=author,
        body=body.strip(),
        is_staff_reply=True,
    )
    notify_admin_reply(report, message)
    return message


def report_action_flags(report: BugReport, admin_user) -> dict[str, bool]:
    """UI flags for triage buttons (list + detail)."""
    assigned_other = bool(
        report.assigned_to_id and report.assigned_to_id != admin_user.pk
    )
    terminal = report.status in (
        BugReport.Status.CLOSED,
        BugReport.Status.REJECTED,
    )
    return {
        'can_take': not assigned_other
        and report.status
        in (BugReport.Status.SUBMITTED, BugReport.Status.REOPENED),
        'can_close': not terminal,
        'can_reject': not terminal,
        'can_reopen': terminal,
    }
