"""Map product screens to info topics (app doc + anchor section)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from django.urls import NoReverseMatch, reverse

# view_name → (app_slug, section anchor)
ROUTE_MAP: dict[str, tuple[str, str]] = {
    # Dashboard (help_key resolved separately; keys listed for labels)
    'dashboard:dashboard': ('dashboard', 'overview'),
    # Workflows
    'workflows:list': ('workflows', 'list'),
    'workflows:create': ('workflows', 'form-create'),
    'workflows:detail': ('workflows', 'detail'),
    'workflows:edit': ('workflows', 'form-edit'),
    'workflows:delete': ('workflows', 'form-delete'),
    'workflows:step_add': ('workflows', 'form-edit'),
    'workflows:enroll': ('workflows', 'detail'),
    # Goals
    'goals:list': ('goals', 'list'),
    'goals:create': ('goals', 'form-create'),
    'goals:detail': ('goals', 'detail'),
    'goals:edit': ('goals', 'form-edit'),
    'goals:delete': ('goals', 'form-delete'),
    # Tasks
    'tasks:task_list': ('tasks', 'list'),
    'tasks:task_create': ('tasks', 'form-create'),
    'tasks:task_detail': ('tasks', 'detail'),
    'tasks:task_edit': ('tasks', 'form-edit'),
    'tasks:task_delete': ('tasks', 'form-delete'),
    'tasks:update_create': ('tasks', 'detail'),
    'tasks:comment_create': ('tasks', 'detail'),
    'tasks:participant_subtask_create': ('tasks', 'detail'),
    # Reflections
    'reflections:list': ('reflections', 'list'),
    'reflections:create': ('reflections', 'form-create'),
    'reflections:detail': ('reflections', 'detail'),
    'reflections:edit': ('reflections', 'form-edit'),
    'reflections:delete': ('reflections', 'form-delete'),
    # Journal
    'journal:list': ('journal', 'list'),
    'journal:create': ('journal', 'form-create'),
    'journal:detail': ('journal', 'detail'),
    'journal:edit': ('journal', 'form-edit'),
    'journal:delete': ('journal', 'form-delete'),
    # Habits
    'habits:list': ('habits', 'list'),
    'habits:create': ('habits', 'form-create'),
    'habits:detail': ('habits', 'detail'),
    'habits:edit': ('habits', 'form-edit'),
    'habits:delete': ('habits', 'form-delete'),
    'habits:complete': ('habits', 'form-delete'),
    'habits:reactivate': ('habits', 'detail'),
    # Group space
    'group_space:feed': ('group_space', 'list'),
    'group_space:post_create': ('group_space', 'form-create'),
    'group_space:post_edit': ('group_space', 'form-edit'),
    'group_space:post_delete': ('group_space', 'form-delete'),
    # Resources
    'resources:index': ('resources', 'list'),
    'resources:container_create': ('resources', 'form-create'),
    'resources:container_detail': ('resources', 'detail'),
    'resources:container_edit': ('resources', 'form-edit'),
    'resources:container_delete': ('resources', 'form-delete'),
    'resources:item_create': ('resources', 'form-create'),
    'resources:item_edit': ('resources', 'form-edit'),
    'resources:item_delete': ('resources', 'form-delete'),
    # Accounts
    'accounts:profile': ('accounts', 'profile'),
}

DASHBOARD_SECTION_BY_ROLE = {
    'student': 'overview',
    'teacher': 'overview-teacher',
    'admin': 'overview-admin',
}

DISABLED_VIEW_NAMES = frozenset(
    {
        'accounts:welcome',
        'accounts:privacy_policy',
        'accounts:password_change_required',
        'accounts:logout',
        'accounts:dev_quick_login',
        'info:topic',
        'health:health',
        'health',
        'home:home',
        'two_factor:login',
        'two_factor:setup',
        'two_factor:qr',
        'two_factor:setup_complete',
        'two_factor:backup_tokens',
        'two_factor:profile',
        'two_factor:disable',
    }
)

# HTMX / API-style routes — no page-level help button
DISABLED_URL_NAMES = frozenset(
    {
        'message_create',
        'share_create',
        'share_start',
        'task_quick_status',
        'task_add_enrollment',
        'subtask_toggle',
        'comment_reply_create',
        'milestone_toggle',
        'mark_achieved',
        'reactivate',
        'enrollment_reactivate',
        'step_delete',
        'step_toggle',
        'unenroll',
        'log_done',
        'log_not_done',
        'item_move',
        'feedback:add',
        'feedback:delete',
    }
)

HELP_LABELS: dict[str, str] = {
    'dashboard:dashboard': 'Dashboard',
    'workflows:list': 'Workflows',
    'goals:list': 'Goals',
    'tasks:task_list': 'Tasks',
    'tasks:task_create': 'New task',
    'tasks:task_detail': 'Task detail',
    'tasks:task_edit': 'Edit task',
    'reflections:list': 'Reflections',
    'reflections:create': 'New reflection',
    'journal:list': 'Journal',
    'habits:list': 'Habits',
    'group_space:feed': 'Group chat',
    'resources:index': 'Resources',
    'accounts:profile': 'Profile',
}

ALLOWED_APP_SLUGS = frozenset(
    {
        'dashboard',
        'workflows',
        'goals',
        'tasks',
        'reflections',
        'journal',
        'habits',
        'group_space',
        'resources',
        'accounts',
    }
)


@dataclass(frozen=True)
class PageHelp:
    enabled: bool
    url: str = ''
    aria_label: str = 'Page help'


def _dashboard_section(user) -> str:
    role = getattr(user, 'role', 'student')
    return DASHBOARD_SECTION_BY_ROLE.get(role, 'overview')


def resolve_help_target(request) -> tuple[str, str, str] | None:
    """
    Return (help_key, app_slug, section) or None when help is disabled.
    help_key is stable string e.g. tasks.task_list (namespace.url_name with dot).
    """
    match = getattr(request, 'resolver_match', None)
    if not match or not getattr(request.user, 'is_authenticated', False):
        return None
    if request.method != 'GET':
        return None

    view_name = match.view_name
    url_name = match.url_name

    if view_name in DISABLED_VIEW_NAMES:
        return None
    if url_name in DISABLED_URL_NAMES:
        return None
    if match.namespace == 'admin':
        return None

    help_key = view_name.replace(':', '.')

    if view_name == 'dashboard:dashboard':
        section = _dashboard_section(request.user)
        return help_key, 'dashboard', section

    mapped = ROUTE_MAP.get(view_name)
    if not mapped:
        return None

    app_slug, section = mapped
    return help_key, app_slug, section


def build_info_url(*, app_slug: str, section: str, help_key: str) -> str:
    base = reverse('info:topic', kwargs={'app_slug': app_slug})
    query = urlencode({'section': section, 'from': help_key})
    return f'{base}?{query}'


def resolve_page_help(request) -> PageHelp:
    target = resolve_help_target(request)
    if not target:
        return PageHelp(enabled=False)

    help_key, app_slug, section = target
    try:
        url = build_info_url(app_slug=app_slug, section=section, help_key=help_key)
    except NoReverseMatch:
        return PageHelp(enabled=False)

    label = HELP_LABELS.get(help_key.replace('.', ':'), 'this page')
    return PageHelp(
        enabled=True,
        url=url,
        aria_label=f'Help for {label}',
    )
