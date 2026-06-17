"""Role-based notification settings UI metadata."""

from accounts.models import User

STUDENT_NOTIFICATION_ROWS = (
    {
        'label': 'Feedback from teachers',
        'in_app_field': 'notify_feedback',
        'email_field': 'email_feedback',
        'slack_field': 'slack_feedback',
    },
    {
        'label': 'New tasks',
        'in_app_field': 'notify_new_task',
        'email_field': 'email_new_task',
        'slack_field': 'slack_new_task',
    },
    {
        'label': 'New goals',
        'in_app_field': 'notify_new_goal',
        'email_field': 'email_new_goal',
        'slack_field': 'slack_new_goal',
    },
    {
        'label': 'New workflows',
        'in_app_field': 'notify_new_workflow',
        'email_field': 'email_new_workflow',
        'slack_field': 'slack_new_workflow',
    },
    {
        'label': 'Deadline reminders',
        'in_app_field': 'notify_deadline_reminder',
        'email_field': 'email_deadline_reminder',
        'slack_field': 'slack_deadline_reminder',
    },
    {
        'label': 'Mentions in group chat',
        'in_app_field': 'notify_group_chat_mentions',
        'email_field': 'email_group_chat_mentions',
        'slack_field': 'slack_group_chat_mentions',
    },
    {
        'label': 'All group chat messages',
        'in_app_field': 'notify_group_chat_all_messages',
        'email_field': 'email_group_chat_all_messages',
        'slack_field': 'slack_group_chat_all_messages',
    },
)

TEACHER_NOTIFICATION_ROWS = (
    {
        'label': 'Student completed a task',
        'in_app_field': 'notify_student_task_completed',
        'email_field': 'email_student_task_completed',
        'slack_field': 'slack_student_task_completed',
    },
    {
        'label': 'Student completed a goal',
        'in_app_field': 'notify_student_goal_completed',
        'email_field': 'email_student_goal_completed',
        'slack_field': 'slack_student_goal_completed',
    },
    {
        'label': 'Student completed a workflow',
        'in_app_field': 'notify_student_workflow_completed',
        'email_field': 'email_student_workflow_completed',
        'slack_field': 'slack_student_workflow_completed',
    },
    {
        'label': 'Student submitted a reflection',
        'in_app_field': 'notify_student_reflection_submitted',
        'email_field': 'email_student_reflection_submitted',
        'slack_field': 'slack_student_reflection_submitted',
    },
    {
        'label': 'Student missed a deadline',
        'in_app_field': 'notify_student_deadline_overdue',
        'email_field': 'email_student_deadline_overdue',
        'slack_field': 'slack_student_deadline_overdue',
    },
    {
        'label': 'Mentions in group chat',
        'in_app_field': 'notify_group_chat_mentions',
        'email_field': 'email_group_chat_mentions',
        'slack_field': 'slack_group_chat_mentions',
    },
    {
        'label': 'All group chat messages',
        'in_app_field': 'notify_group_chat_all_messages',
        'email_field': 'email_group_chat_all_messages',
        'slack_field': 'slack_group_chat_all_messages',
    },
)

ADMIN_NOTIFICATION_ROWS = (
    {
        'label': 'New bug report submitted',
        'in_app_field': 'notify_bug_report_new',
        'email_field': 'email_bug_report_new',
        'slack_field': 'slack_bug_report_new',
    },
    {
        'label': 'Bug report reopened',
        'in_app_field': 'notify_bug_report_reopened',
        'email_field': 'email_bug_report_reopened',
        'slack_field': 'slack_bug_report_reopened',
    },
    {
        'label': 'New user account created',
        'in_app_field': 'notify_new_user_account',
        'email_field': 'email_new_user_account',
        'slack_field': 'slack_new_user_account',
    },
)

NOTIFICATION_EVENT_ROWS = STUDENT_NOTIFICATION_ROWS

_BASE_FORM_FIELDS = (
    'in_app_enabled',
    'email_enabled',
    'slack_enabled',
    'digest_mode',
    'quiet_hours_start',
    'quiet_hours_end',
    'timezone',
)


def _field_names_from_rows(rows):
    names = []
    for row in rows:
        names.extend((row['in_app_field'], row['email_field'], row['slack_field']))
    return names


STUDENT_EVENT_FIELDS = _field_names_from_rows(STUDENT_NOTIFICATION_ROWS)
TEACHER_EVENT_FIELDS = _field_names_from_rows(TEACHER_NOTIFICATION_ROWS)
ADMIN_EVENT_FIELDS = _field_names_from_rows(ADMIN_NOTIFICATION_ROWS)


def notification_rows_for_user(user):
    if user.role == User.Role.ADMIN:
        return TEACHER_NOTIFICATION_ROWS + ADMIN_NOTIFICATION_ROWS
    if user.role == User.Role.TEACHER:
        return TEACHER_NOTIFICATION_ROWS
    return STUDENT_NOTIFICATION_ROWS


def notification_form_fields_for_user(user):
    if user.role == User.Role.ADMIN:
        event_fields = TEACHER_EVENT_FIELDS + ADMIN_EVENT_FIELDS
    elif user.role == User.Role.TEACHER:
        event_fields = TEACHER_EVENT_FIELDS
    else:
        event_fields = STUDENT_EVENT_FIELDS
    return list(_BASE_FORM_FIELDS) + event_fields


def notification_settings_intro_for_user(user):
    if user.role == User.Role.ADMIN:
        return (
            'Student activity and group chat alerts (same as teachers), plus platform '
            'alerts for bug reports and new accounts. Use the master switches to turn '
            'a whole channel off, then fine-tune each event.'
        )
    if user.role == User.Role.TEACHER:
        return (
            'Alerts about your students: completed activities, missed deadlines, and group chat. '
            'Use the master switches to turn a whole channel off, then fine-tune each event.'
        )
    return (
        'Use the master switches in the table header to turn a whole channel off, '
        'then fine-tune each event below.'
    )
