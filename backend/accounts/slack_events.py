"""Verify Slack Events API request signatures."""

from __future__ import annotations

import hashlib
import hmac
import time


class SlackSignatureError(Exception):
    pass


def verify_slack_signature(
    *,
    signing_secret: str,
    body: bytes,
    timestamp_header: str,
    signature_header: str,
    max_age_seconds: int = 60 * 5,
) -> None:
    secret = (signing_secret or '').strip()
    if not secret:
        raise SlackSignatureError('Slack signing secret is not configured.')

    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError) as exc:
        raise SlackSignatureError('Invalid Slack timestamp.') from exc

    if abs(time.time() - timestamp) > max_age_seconds:
        raise SlackSignatureError('Slack request timestamp is too old.')

    sig_basestring = f'v0:{timestamp_header}:{body.decode("utf-8")}'
    digest = hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    expected = f'v0={digest}'
    if not hmac.compare_digest(expected, signature_header or ''):
        raise SlackSignatureError('Invalid Slack signature.')
