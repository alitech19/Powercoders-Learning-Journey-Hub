from tasks.models import Task, TaskEnrollment


def make_personal_task(
    student,
    *,
    title='Personal task',
    visibility=Task.Visibility.PRIVATE,
    status=Task.Status.TODO,
    **kwargs,
):
    return Task.objects.create(
        author=student,
        assignee_user=student,
        assignee_type=Task.AssigneeType.USER,
        title=title,
        visibility=visibility,
        status=status,
        **kwargs,
    )


def make_group_shared_task(
    created_by,
    group,
    *,
    title='Group task',
    visibility=Task.Visibility.SHARED,
    status=Task.Status.TODO,
    **kwargs,
):
    task = Task(
        author=None,
        created_by=created_by,
        assignee_type=Task.AssigneeType.GROUP,
        assignee_group=group,
        progress_mode=Task.ProgressMode.SHARED,
        title=title,
        visibility=visibility,
        status=status,
        **kwargs,
    )
    task.full_clean()
    task.save()
    return task


def make_staff_individual_task(
    created_by,
    *,
    title='Staff task',
    visibility=Task.Visibility.SHARED,
    **kwargs,
):
    return Task.objects.create(
        author=None,
        created_by=created_by,
        assignee_type=Task.AssigneeType.USER,
        progress_mode=Task.ProgressMode.INDIVIDUAL,
        title=title,
        visibility=visibility,
        **kwargs,
    )


def enroll_student(task, student, *, status=Task.Status.TODO):
    return TaskEnrollment.objects.create(task=task, student=student, status=status)
