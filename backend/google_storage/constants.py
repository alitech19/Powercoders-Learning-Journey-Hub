"""Shared constants for Google Drive storage."""

from group_space.constants import GROUP_FILE_MAX_BYTES

ROOT_FOLDER_NAME = 'PowerHUB'
GROUPS_FOLDER_NAME = 'Groups'

# Align chat uploads with group_space file limit (10 MB).
DRIVE_UPLOAD_MAX_BYTES = GROUP_FILE_MAX_BYTES

# Celery auto-retry (see tasks.upload_post_file_to_drive).
DRIVE_UPLOAD_MAX_RETRIES = 2
DRIVE_UPLOAD_RETRY_DELAY_SECONDS = 60

# Per-user chat upload rate limit (rolling window).
DRIVE_UPLOAD_RATE_LIMIT = 10
DRIVE_UPLOAD_RATE_WINDOW_SECONDS = 60
