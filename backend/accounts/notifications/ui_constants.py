"""Shared notification settings UI metadata."""

NOTIFICATION_EVENT_ROWS = (
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
