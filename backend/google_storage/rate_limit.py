"""Simple per-user upload rate limiting for chat → Drive."""

from __future__ import annotations

from django.core.cache import cache

from .constants import DRIVE_UPLOAD_RATE_LIMIT, DRIVE_UPLOAD_RATE_WINDOW_SECONDS


class DriveUploadRateLimitError(Exception):
    """Raised when a user exceeds the configured upload rate."""


def check_drive_upload_rate_limit(user_id: int) -> None:
    key = f'google_storage:upload_rl:{user_id}'
    count = cache.get(key, 0)
    if count >= DRIVE_UPLOAD_RATE_LIMIT:
        raise DriveUploadRateLimitError(
            f'Too many uploads. Try again in a minute (limit: {DRIVE_UPLOAD_RATE_LIMIT} per minute).',
        )
    cache.set(key, count + 1, DRIVE_UPLOAD_RATE_WINDOW_SECONDS)
