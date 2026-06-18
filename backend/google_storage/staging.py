"""Temporary on-disk staging for chat uploads before Celery pushes to Drive."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings


def staging_root() -> Path:
    root = Path(settings.GOOGLE_UPLOAD_STAGING_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _bin_path(post_id: int) -> Path:
    return staging_root() / f'{post_id}.bin'


def _meta_path(post_id: int) -> Path:
    return staging_root() / f'{post_id}.json'


def save_staged_upload(post_id: int, uploaded_file) -> None:
    meta = {
        'filename': Path(uploaded_file.name).name,
        'content_type': getattr(uploaded_file, 'content_type', '') or 'application/octet-stream',
        'size': uploaded_file.size,
    }
    with _bin_path(post_id).open('wb') as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)
    _meta_path(post_id).write_text(json.dumps(meta), encoding='utf-8')


def load_staged_upload(post_id: int) -> tuple[bytes, dict]:
    bin_path = _bin_path(post_id)
    meta_path = _meta_path(post_id)
    if not bin_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f'No staged upload for post {post_id}')
    content = bin_path.read_bytes()
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    return content, meta


def delete_staged_upload(post_id: int) -> None:
    for path in (_bin_path(post_id), _meta_path(post_id)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def has_staged_upload(post_id: int) -> bool:
    return _bin_path(post_id).exists()
