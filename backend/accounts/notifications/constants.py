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
        'email': 'email_feedback',
        'slack': 'slack_feedback',
    },
    EventType.NEW_WORKFLOW: {
        'email': 'email_new_workflow',
        'slack': 'slack_new_workflow',
    },
    EventType.NEW_TASK: {
        'email': 'email_new_task',
        'slack': 'slack_new_task',
    },
    EventType.NEW_GOAL: {
        'email': 'email_new_goal',
        'slack': 'slack_new_goal',
    },
    EventType.DEADLINE_REMINDER: {
        'email': 'email_deadline_reminder',
        'slack': 'slack_deadline_reminder',
    },
    EventType.GROUP_CHAT_MENTION: {
        'email': 'email_group_chat_mentions',
        'slack': 'slack_group_chat_mentions',
    },
    EventType.GROUP_CHAT_ALL: {
        'email': 'email_group_chat_all_messages',
        'slack': 'slack_group_chat_all_messages',
    },
}
