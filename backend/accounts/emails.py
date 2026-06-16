import logging

from django.conf import settings
from django.core.mail import send_mail

from .slack import send_slack_message

logger = logging.getLogger(__name__)


def _send(subject, body, recipient_email):
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


def create_notification(recipient, title, body='', url=''):
    """Legacy helper — prefer accounts.notifications.dispatcher.dispatch_event."""
    from .models import Notification

    try:
        Notification.objects.create(recipient=recipient, title=title, body=body, url=url)
    except Exception:
        pass


def send_notification_email(*, recipient, subject, body):
    _send(
        subject=subject,
        body=body,
        recipient_email=recipient.email,
    )


def send_new_user_slack(user):
    role_label = user.get_role_display() if hasattr(user, 'get_role_display') else user.role
    send_slack_message(f'👋 New *{role_label}* account created: *{user.display_name}* ({user.email})')


def send_welcome_email(user, temp_password):
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    login_path = '/account/login/'
    body = f"""Hi {user.display_name},

Your Powercoders Learning Journey Hub account has been created.

Email:    {user.email}
Password: {temp_password}

Log in here: {site}{login_path}

You will be asked to set a new password on first login.

— Powercoders Team
"""
    _send(
        subject='Your PowerHUB account is ready',
        body=body,
        recipient_email=user.email,
    )


def notify_feedback_received(*, entry, recipient, title, relative_url):
    """In-app notification, optional email, and global staff Slack webhook."""
    from accounts.notifications.constants import EventType
    from accounts.notifications.dispatcher import dispatch_event

    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    full_url = f'{site}{relative_url}' if relative_url else site
    email_body = f"""Hi {recipient.display_name},

{title}

---
{entry.body}
---

View it here: {full_url}

— Powercoders Team
"""
    dispatch_event(
        event_type=EventType.FEEDBACK,
        recipients=[recipient],
        title=title,
        body=entry.body,
        url=relative_url,
        dedupe_key=f'feedback:{entry.pk}',
        email_subject=title,
        email_body=email_body,
        slack_text=(
            f'💬 *{entry.author.display_name}* left feedback for you: {title}\n'
            f'{entry.body[:500]}'
        ),
    )
    send_slack_message(
        f'💬 *{entry.author.display_name}* left feedback for *{recipient.display_name}*: {title}'
    )
