import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

User = get_user_model()


def _send(subject, body, recipient_email):
    if not recipient_email:
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception:
        logger.warning(
            'Failed to send email %r to %s — check EMAIL_BACKEND / SMTP settings.',
            subject,
            recipient_email,
            exc_info=True,
        )


def _site_url():
    return getattr(settings, 'SITE_URL', '').rstrip('/')


def notify_report_created(report):
    site = _site_url()
    reporter = report.reporter
    _send(
        subject='We received your bug report',
        body=f"""Hi {reporter.display_name},

Thanks for reporting an issue on PowerHUB. We received your report #{report.pk} and will review it.

Page: {report.page_url}

— PowerHUB Team
""",
        recipient_email=reporter.email,
    )

    admin_url = f'{site}/bugs/inbox/{report.pk}/' if site else f'/bugs/inbox/{report.pk}/'
    admin_body = f"""New bug report #{report.pk}

Reporter: {reporter.display_name} ({reporter.email})
Page: {report.page_url}

Description:
{report.description}

Open in inbox: {admin_url}
"""
    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    for admin in admins:
        _send(
            subject=f'New bug report #{report.pk}',
            body=admin_body,
            recipient_email=admin.email,
        )


def notify_admin_reply(report, message):
    reporter = report.reporter
    if not reporter.email_notifications_enabled:
        return
    site = _site_url()
    _send(
        subject=f'Update on your bug report #{report.pk}',
        body=f"""Hi {reporter.display_name},

An admin replied to your bug report #{report.pk}:

{message.body}

— PowerHUB Team
""",
        recipient_email=reporter.email,
    )
