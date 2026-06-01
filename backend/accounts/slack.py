import json
import urllib.request

from django.conf import settings


def send_slack_message(text):
    url = getattr(settings, 'SLACK_WEBHOOK_URL', '') or ''
    if not url:
        return
    payload = json.dumps({'text': text}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
