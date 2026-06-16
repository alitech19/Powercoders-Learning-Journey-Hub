from django.db import models


class EventType(models.TextChoices):
    FEEDBACK = 'feedback', 'Feedback received'
    NEW_WORKFLOW = 'new_workflow', 'New workflow'
    NEW_TASK = 'new_task', 'New task'
    NEW_GOAL = 'new_goal', 'New goal'
    DEADLINE_REMINDER = 'deadline_reminder', 'Deadline reminder'
    GROUP_CHAT_MENTION = 'group_chat_mention', 'Group chat mention'
    GROUP_CHAT_ALL = 'group_chat_all', 'All group chat messages'


EVENT_SETTING_FIELD = {
    EventType.FEEDBACK: 'notify_feedback',
    EventType.NEW_WORKFLOW: 'notify_new_workflow',
    EventType.NEW_TASK: 'notify_new_task',
    EventType.NEW_GOAL: 'notify_new_goal',
    EventType.DEADLINE_REMINDER: 'notify_deadline_reminder',
    EventType.GROUP_CHAT_MENTION: 'notify_group_chat_mentions',
    EventType.GROUP_CHAT_ALL: 'notify_group_chat_all_messages',
}
