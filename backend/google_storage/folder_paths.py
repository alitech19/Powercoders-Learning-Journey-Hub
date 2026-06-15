"""Logical Drive folder paths — same layout for Shared drive and My Drive."""

import re

from django.utils.text import slugify

from .constants import GROUPS_FOLDER_NAME, ROOT_FOLDER_NAME


def _segment(value: str, *, fallback: str) -> str:
    slug = slugify(value) or fallback
    return re.sub(r'[^a-z0-9\-]+', '', slug.lower()) or fallback


def group_folder_segment(group) -> str:
    cohort_part = _segment(group.cohort.name, fallback='cohort')
    group_part = _segment(group.name, fallback='group')
    return f'{cohort_part}-{group_part}'


def group_drive_path(group) -> str:
    return f'{ROOT_FOLDER_NAME}/{GROUPS_FOLDER_NAME}/{group_folder_segment(group)}'


def root_drive_path() -> str:
    return ROOT_FOLDER_NAME
