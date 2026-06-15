"""Google Workspace native file types creatable from group chat."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleDocType:
    key: str
    label: str
    mime_type: str


GOOGLE_DOC_TYPES: tuple[GoogleDocType, ...] = (
    GoogleDocType('document', 'Google Doc', 'application/vnd.google-apps.document'),
    GoogleDocType('spreadsheet', 'Google Sheet', 'application/vnd.google-apps.spreadsheet'),
    GoogleDocType('presentation', 'Google Slides', 'application/vnd.google-apps.presentation'),
    GoogleDocType('form', 'Google Form', 'application/vnd.google-apps.form'),
)

GOOGLE_DOC_TYPE_BY_KEY: dict[str, GoogleDocType] = {item.key: item for item in GOOGLE_DOC_TYPES}

GOOGLE_DOC_TYPE_CHOICES: tuple[tuple[str, str], ...] = tuple(
    (item.key, item.label) for item in GOOGLE_DOC_TYPES
)
