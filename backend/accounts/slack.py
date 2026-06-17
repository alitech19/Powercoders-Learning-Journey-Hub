import json
import urllib.request

from .slack_workspace_config import resolve_webhook_url, staff_webhook_configured


def send_slack_message(text) -> bool:
    if not staff_webhook_configured():
        return False
    url = resolve_webhook_url()
    if not url:
        return False
    payload = json.dumps({'text': text}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False
