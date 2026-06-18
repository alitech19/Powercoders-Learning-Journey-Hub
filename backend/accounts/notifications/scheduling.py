"""Schedule entity assignment notifications after DB commit."""

from django.db import transaction


def _student_ids(students):
    if hasattr(students, 'values_list'):
        return list(students.values_list('pk', flat=True))
    return [student.pk for student in students]


def schedule_task_assigned(*, task, students, actor):
    student_ids = _student_ids(students)
    if not student_ids:
        return
    actor_id = actor.pk if actor else None

    def _enqueue():
        from accounts.tasks import notify_task_assigned_task

        notify_task_assigned_task.delay(task.pk, student_ids, actor_id)

    transaction.on_commit(_enqueue)


def schedule_goal_assigned(*, goal, students, actor):
    student_ids = _student_ids(students)
    if not student_ids:
        return
    actor_id = actor.pk if actor else None

    def _enqueue():
        from accounts.tasks import notify_goal_assigned_task

        notify_goal_assigned_task.delay(goal.pk, student_ids, actor_id)

    transaction.on_commit(_enqueue)


def schedule_workflow_assigned(*, workflow, students, actor):
    student_ids = _student_ids(students)
    if not student_ids:
        return
    actor_id = actor.pk if actor else None

    def _enqueue():
        from accounts.tasks import notify_workflow_assigned_task

        notify_workflow_assigned_task.delay(workflow.pk, student_ids, actor_id)

    transaction.on_commit(_enqueue)
