from django.db import models


class EventType(models.TextChoices):
    FEEDBACK = 'feedback', 'Feedback received'
    NEW_WORKFLOW = 'new_workflow', 'New workflow'
    NEW_TASK = 'new_task', 'New task'
    NEW_GOAL = 'new_goal', 'New goal'
    DEADLINE_REMINDER = 'deadline_reminder', 'Deadline reminder'
    GROUP_CHAT_MENTION = 'group_chat_mention', 'Group chat mention'
    GROUP_CHAT_ALL = 'group_chat_all', 'All group chat messages'
    STUDENT_TASK_COMPLETED = 'student_task_completed', 'Student task completed'
    STUDENT_GOAL_COMPLETED = 'student_goal_completed', 'Student goal completed'
    STUDENT_WORKFLOW_COMPLETED = 'student_workflow_completed', 'Student workflow completed'
    STUDENT_REFLECTION_SUBMITTED = 'student_reflection_submitted', 'Student reflection submitted'
    STUDENT_DEADLINE_OVERDUE = 'student_deadline_overdue', 'Student missed deadline'
    BUG_REPORT_NEW = 'bug_report_new', 'New bug report'
    BUG_REPORT_REOPENED = 'bug_report_reopened', 'Bug report reopened'
    NEW_USER_ACCOUNT = 'new_user_account', 'New user account'


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
    EventType.STUDENT_TASK_COMPLETED: {
        'in_app': 'notify_student_task_completed',
        'email': 'email_student_task_completed',
        'slack': 'slack_student_task_completed',
    },
    EventType.STUDENT_GOAL_COMPLETED: {
        'in_app': 'notify_student_goal_completed',
        'email': 'email_student_goal_completed',
        'slack': 'slack_student_goal_completed',
    },
    EventType.STUDENT_WORKFLOW_COMPLETED: {
        'in_app': 'notify_student_workflow_completed',
        'email': 'email_student_workflow_completed',
        'slack': 'slack_student_workflow_completed',
    },
    EventType.STUDENT_REFLECTION_SUBMITTED: {
        'in_app': 'notify_student_reflection_submitted',
        'email': 'email_student_reflection_submitted',
        'slack': 'slack_student_reflection_submitted',
    },
    EventType.STUDENT_DEADLINE_OVERDUE: {
        'in_app': 'notify_student_deadline_overdue',
        'email': 'email_student_deadline_overdue',
        'slack': 'slack_student_deadline_overdue',
    },
    EventType.BUG_REPORT_NEW: {
        'in_app': 'notify_bug_report_new',
        'email': 'email_bug_report_new',
        'slack': 'slack_bug_report_new',
    },
    EventType.BUG_REPORT_REOPENED: {
        'in_app': 'notify_bug_report_reopened',
        'email': 'email_bug_report_reopened',
        'slack': 'slack_bug_report_reopened',
    },
    EventType.NEW_USER_ACCOUNT: {
        'in_app': 'notify_new_user_account',
        'email': 'email_new_user_account',
        'slack': 'slack_new_user_account',
    },
}
