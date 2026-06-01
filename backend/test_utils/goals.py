from goals.models import Goal, GoalEnrollment, Milestone


def make_goal(
    *,
    author=None,
    created_by=None,
    title='Test goal',
    visibility=Goal.Visibility.PRIVATE,
    category=Goal.Category.TECHNICAL,
    **kwargs,
):
    return Goal.objects.create(
        author=author,
        created_by=created_by,
        title=title,
        visibility=visibility,
        category=category,
        **kwargs,
    )


def make_student_goal(student, **kwargs):
    kwargs.setdefault('author', student)
    kwargs.setdefault('visibility', Goal.Visibility.PRIVATE)
    goal = make_goal(**kwargs)
    enroll_student(goal, student)
    return goal


def make_staff_goal(created_by, *, visibility=Goal.Visibility.SHARED, **kwargs):
    return make_goal(
        author=None,
        created_by=created_by,
        visibility=visibility,
        **kwargs,
    )


def enroll_student(goal, student, *, status=GoalEnrollment.Status.NOT_STARTED):
    return GoalEnrollment.objects.create(goal=goal, student=student, status=status)


def add_milestone(goal, *, title='Milestone', order=1):
    return Milestone.objects.create(goal=goal, title=title, order=order)
