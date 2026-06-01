"""Load and parse per-app markdown help topics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import bleach
import markdown

from cohorts.permissions import user_is_admin

TOPICS_DIR = Path(__file__).resolve().parent / 'topics'

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS | frozenset(
    [
        'h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre', 'a', 'hr', 'br',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
    ]
)
ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    'a': ['href', 'title', 'rel'],
    'th': ['scope'],
    'td': ['colspan', 'rowspan'],
}

HEADER_RE = re.compile(
    r'^##\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$',
    re.MULTILINE,
)
ROLE_ADMIN_RE = re.compile(r'^<!--\s*role:\s*admin\s*-->\s*$', re.MULTILINE | re.IGNORECASE)


@dataclass(frozen=True)
class HelpSection:
    section_id: str
    title: str
    html: str
    admin_only: bool


@dataclass(frozen=True)
class HelpTopic:
    app_slug: str
    title: str
    sections: tuple[HelpSection, ...]


def _slugify(title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return slug or 'section'


def _render_markdown(text: str) -> str:
    raw = markdown.markdown(text.strip(), extensions=['extra', 'nl2br'])
    return bleach.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)


def parse_topic_markdown(app_slug: str, source: str) -> HelpTopic:
    intro = ''
    first_header = HEADER_RE.search(source)
    if first_header:
        intro = source[: first_header.start()].strip()
    else:
        intro = source.strip()

    sections: list[HelpSection] = []
    headers = list(HEADER_RE.finditer(source))

    for index, match in enumerate(headers):
        title = match.group(1).strip()
        section_id = match.group(2) or _slugify(title)
        start = match.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(source)
        body = source[start:end].strip()
        admin_only = False
        lines = body.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and ROLE_ADMIN_RE.match(lines[0].strip()):
            admin_only = True
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines.pop(0)
            body = '\n'.join(lines).strip()
        sections.append(
            HelpSection(
                section_id=section_id,
                title=title,
                html=_render_markdown(body),
                admin_only=admin_only,
            )
        )

    if intro:
        sections.insert(
            0,
            HelpSection(
                section_id='overview',
                title='Overview',
                html=_render_markdown(intro),
                admin_only=False,
            ),
        )

    doc_title = app_slug.replace('_', ' ').title()
    if sections and sections[0].section_id == 'overview':
        doc_title = sections[0].title if intro else doc_title

    return HelpTopic(app_slug=app_slug, title=doc_title, sections=tuple(sections))


@lru_cache(maxsize=32)
def _load_topic_cached(app_slug: str, mtime_ns: int) -> HelpTopic:
    path = TOPICS_DIR / f'{app_slug}.md'
    if not path.is_file():
        return HelpTopic(app_slug=app_slug, title=app_slug.title(), sections=())
    return parse_topic_markdown(app_slug, path.read_text(encoding='utf-8'))


def load_topic(app_slug: str) -> HelpTopic:
    path = TOPICS_DIR / f'{app_slug}.md'
    mtime_ns = path.stat().st_mtime_ns if path.is_file() else 0
    return _load_topic_cached(app_slug, mtime_ns)


def visible_sections(topic: HelpTopic, user) -> list[HelpSection]:
    show_admin = user_is_admin(user)
    return [s for s in topic.sections if not s.admin_only or show_admin]
