"""Page purpose copy — short subtitles for hub/list screens."""

from __future__ import annotations

from dataclasses import dataclass

from cohorts.permissions import user_is_student


@dataclass(frozen=True)
class PageMeta:
    purpose: str
    purpose_staff: str | None = None


PAGE_PURPOSE: dict[str, PageMeta] = {
    'workflows:list': PageMeta(
        purpose=(
            'Follow step-by-step learning paths from your teachers — complete steps '
            'in order and track shared or individual progress.'
        ),
        purpose_staff=(
            'Manage and monitor step-by-step programmes for your groups — see who has '
            'completed each stage.'
        ),
    ),
    'tasks:task_list': PageMeta(
        purpose=(
            "Plan how you'll get work done — break tasks into subtasks, update status, "
            'log progress, and share updates with your teachers.'
        ),
        purpose_staff=(
            'See how students organize work — subtasks, status, progress updates, and '
            "tasks they've chosen to share."
        ),
    ),
    'goals:list': PageMeta(
        purpose=(
            "Set learning targets, break them into milestones, and track how far you've come."
        ),
        purpose_staff=(
            'View shared goals and milestone progress from your students, or assign goal '
            'templates to groups.'
        ),
    ),
    'habits:list': PageMeta(
        purpose=(
            'Build weekly routines — set a target, mark the days you showed up, and keep '
            'your streak going.'
        ),
        purpose_staff=(
            'See shared habits and weekly consistency from students in your groups.'
        ),
    ),
    'reflections:list': PageMeta(
        purpose=(
            'Structured check-ins for expectations, wellbeing, and wrap-up thoughts — save '
            "once and return when you're ready."
        ),
        purpose_staff=(
            "Read shared reflections from your students to understand how they're doing "
            'and support their learning.'
        ),
    ),
    'journal:list': PageMeta(
        purpose=(
            'Write about your learning day by day — keep entries private or share selected '
            'ones with your teachers.'
        ),
        purpose_staff='Browse shared journal entries from students in your groups.',
    ),
    'group_space:feed': PageMeta(
        purpose=(
            "Your study group's chat — discuss together, share progress snapshots from your "
            "apps, and save links to the group's resource list."
        ),
    ),
    'resources:index': PageMeta(
        purpose=(
            'Curated link collections — personal bookmarks, resources saved from group chat, '
            'and themed lists for your groups.'
        ),
    ),
}


def resolve_page_meta(request) -> dict[str, str | bool]:
    resolver = getattr(request, 'resolver_match', None)
    view_name = resolver.view_name if resolver else None
    if not view_name:
        return {'purpose': '', 'has_purpose': False}

    meta = PAGE_PURPOSE.get(view_name)
    if not meta:
        return {'purpose': '', 'has_purpose': False}

    user = request.user
    if (
        meta.purpose_staff
        and user.is_authenticated
        and not user_is_student(user)
    ):
        purpose = meta.purpose_staff
    else:
        purpose = meta.purpose

    return {'purpose': purpose, 'has_purpose': True}
