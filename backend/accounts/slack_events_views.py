import json
import logging

from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.slack_events import SlackSignatureError, verify_slack_signature
from accounts.slack_workspace_config import get_slack_workspace_config, resolve_signing_secret

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def slack_events(request):
    config = get_slack_workspace_config()
    signing_secret = resolve_signing_secret(config)
    try:
        verify_slack_signature(
            signing_secret=signing_secret,
            body=request.body,
            timestamp_header=request.headers.get('X-Slack-Request-Timestamp', ''),
            signature_header=request.headers.get('X-Slack-Signature', ''),
        )
    except SlackSignatureError as exc:
        logger.warning('Slack events rejected: %s', exc)
        return HttpResponseForbidden(str(exc))

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return HttpResponseForbidden('Invalid JSON payload.')

    if payload.get('type') == 'url_verification':
        return JsonResponse({'challenge': payload.get('challenge', '')})

    if payload.get('type') != 'event_callback':
        return HttpResponse(status=200)

    from group_space.slack_ingest import (
        ingest_slack_message_changed,
        ingest_slack_message_deleted,
        ingest_slack_message_event,
        should_ignore_slack_message_event,
    )

    event = payload.get('event') or {}
    event_type = event.get('type', '')
    subtype = (event.get('subtype') or '').strip()
    bot_user_id = (config.slack_bot_user_id or '').strip()

    try:
        if event_type == 'message' and subtype == 'message_changed':
            ingest_slack_message_changed(event)
        elif event_type == 'message' and subtype == 'message_deleted':
            ingest_slack_message_deleted(event)
        elif not should_ignore_slack_message_event(event, bot_user_id=bot_user_id):
            ingest_slack_message_event(event)
    except Exception:
        logger.exception('Slack event ingest failed')
    return HttpResponse(status=200)
