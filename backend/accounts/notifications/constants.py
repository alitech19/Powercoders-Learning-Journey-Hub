from django.db import models


class EventType(models.TextChoices):
    FEEDBACK = 'feedback', 'Feedback received'
    NEW_WORKFLOW = 'new_workflow', 'New workflow'
    NEW_TASK = 'new_task', 'New task'
    NEW_GOAL = 'new_goal', 'New goal'
    DEADLINE_REMINDER = 'deadline_reminder', 'Deadline reminder'
    GROUP_CHAT_MENTION = 'group_chat_mention', 'Group chat mention'
    GROUP_CHAT_ALL = 'group_chat_all', 'All group chat messages'


EVENT_SETTING_FIELDS = {
    EventType.FEEDBACK: {
        'in_app': 'notify_feedback',
        'email': 'email_feedback',
        'slack': 'slack_feedback',
    },
    EventType.NEW_WORKFLOW: {
        'in_app': 'notify_new_workflow',
        'email': 'email_new_workflow',
        'slack': 'slack_new_workflow',
    },
    EventType.NEW_TASK: {
        'in_app': 'notify_new_task',
        'email': 'email_new_task',
        'slack': 'slack_new_task',
    },
    EventType.NEW_GOAL: {
        'in_app': 'notify_new_goal',
        'email': 'email_new_goal',
        'slack': 'slack_new_goal',
    },
    EventType.DEADLINE_REMINDER: {
        'in_app': 'notify_deadline_reminder',
        'email': 'email_deadline_reminder',
        'slack': 'slack_deadline_reminder',
    },
    EventType.GROUP_CHAT_MENTION: {
        'in_app': 'notify_group_chat_mentions',
        'email': 'email_group_chat_mentions',
        'slack': 'slack_group_chat_mentions',
    },
    EventType.GROUP_CHAT_ALL: {
        'in_app': 'notify_group_chat_all_messages',
        'email': 'email_group_chat_all_messages',
        'slack': 'slack_group_chat_all_messages',
    },
}
