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
    from .models import Notification

    try:
        Notification.objects.create(recipient=recipient, title=title, body=body, url=url)
    except Exception:
        pass


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
    """In-app notification, optional email, and Slack when staff leaves feedback."""
    site = getattr(settings, 'SITE_URL', '').rstrip('/')
    full_url = f'{site}{relative_url}' if relative_url else site
    create_notification(recipient, title, body=entry.body, url=relative_url)
    send_slack_message(
        f'💬 *{entry.author.display_name}* left feedback for *{recipient.display_name}*: {title}'
    )
    if not recipient.email_notifications_enabled:
        return
    email_body = f"""Hi {recipient.display_name},

{title}

---
{entry.body}
---

View it here: {full_url}

— Powercoders Team
"""
    _send(
        subject=title,
        body=email_body,
        recipient_email=recipient.email,
    )
