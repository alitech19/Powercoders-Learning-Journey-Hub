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
    'tasks:subtask_create': ('tasks', 'detail'),
    'tasks:subtask_edit': ('tasks', 'detail'),
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
    'group_space:project_list': ('group_spaces_admin', 'overview'),
    'group_space:project_create': ('group_spaces_admin', 'create'),
    'group_space:project_detail': ('group_spaces_admin', 'members'),
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
    'accounts:notifications': ('accounts', 'notifications'),
    'accounts:notification_settings': ('accounts', 'notification-settings'),
    'accounts:storage_settings': ('google_drive', 'student-oauth-gcp'),
    'accounts:slack_settings': ('slack_integration', 'admin-quick-start'),
    # Administration (in-app staff UI)
    'accounts:cohort_list': ('administration', 'cohorts-groups'),
    'accounts:cohort_create': ('administration', 'cohorts-groups'),
    'accounts:cohort_edit': ('administration', 'cohorts-groups'),
    'accounts:cohort_delete': ('administration', 'cohorts-groups'),
    'accounts:group_create': ('administration', 'cohorts-groups'),
    'accounts:group_edit': ('administration', 'cohorts-groups'),
    'accounts:group_delete': ('administration', 'cohorts-groups'),
    'accounts:group_assign_students': ('administration', 'cohorts-groups'),
    'accounts:student_progress': ('administration', 'student-progress'),
    'accounts:student_detail': ('administration', 'student-detail'),
    'accounts:user_list': ('administration', 'users'),
    'accounts:user_create': ('administration', 'create-user'),
    'accounts:user_deactivate': ('administration', 'users'),
    'accounts:user_reactivate': ('administration', 'users'),
    'accounts:user_delete_account': ('administration', 'users'),
    'accounts:user_import': ('administration', 'import-users'),
}

# Django admin pages linked from Administration menu
ADMIN_HELP_ROUTES: dict[str, tuple[str, str]] = {
    'admin:accounts_auditlog_changelist': ('administration', 'audit-log'),
    'admin:index': ('administration', 'django-admin'),
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
        'subtask_status',
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
    'group_space:feed': 'Group Space',
    'group_space:project_list': 'Group spaces',
    'group_space:project_create': 'New group space',
    'group_space:project_detail': 'Group space',
    'resources:index': 'Resources',
    'accounts:profile': 'Profile',
    'accounts:notifications': 'Notification centre',
    'accounts:notification_settings': 'Notification settings',
    'accounts:storage_settings': 'File storage',
    'accounts:slack_settings': 'Slack integration',
    'accounts:cohort_list': 'Cohorts & Groups',
    'accounts:cohort_create': 'New cohort',
    'accounts:cohort_edit': 'Edit cohort',
    'accounts:cohort_delete': 'Delete cohort',
    'accounts:group_create': 'New group',
    'accounts:group_edit': 'Edit group',
    'accounts:group_delete': 'Delete group',
    'accounts:group_assign_students': 'Assign students',
    'accounts:student_progress': 'Student Progress',
    'accounts:student_detail': 'Student detail',
    'accounts:user_list': 'Users',
    'accounts:user_create': 'Create User',
    'accounts:user_import': 'Import Users',
    'admin:accounts_auditlog_changelist': 'Audit Log',
    'admin:index': 'Django Admin',
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
        'group_spaces_admin',
        'resources',
        'accounts',
        'google_drive',
        'administration',
        'slack_integration',
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

    help_key = view_name.replace(':', '.')

    if match.namespace == 'admin':
        admin_mapped = ADMIN_HELP_ROUTES.get(view_name)
        if admin_mapped:
            app_slug, section = admin_mapped
            return help_key, app_slug, section
        return None

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
