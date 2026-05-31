import ast

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from cohorts.models import Cohort, Group
from config.input_limits import TITLE_MAX_LENGTH
from config.text_validation import clamp_text
from cohorts.permissions import (
    get_active_students_for_cohort,
    get_active_students_for_group,
    get_teacher_accessible_cohorts,
    get_teacher_accessible_groups,
    get_teacher_cohort_ids,
    get_teacher_group_ids,
    user_is_admin,
    user_is_teacher,
)

from .models import Subtask, SubtaskCompletion, Task, TaskComment, TaskEnrollment, TaskUpdate


class AssigneeType:
    COHORT = 'cohort'
    GROUP = 'group'


def normalize_subtask_title(raw):
    title = (raw or '').strip()
    while title.startswith('{') and 'title' in title:
        try:
            parsed = ast.literal_eval(title)
        except (ValueError, SyntaxError):
            break
        if not isinstance(parsed, dict):
            break
        inner = parsed.get('title')
        if not isinstance(inner, str) or inner == title:
            break
        title = inner.strip()
    return title


def parse_subtasks_from_post(post):
    subtasks = []
    order = 0
    for key in sorted(post.keys()):
        if key.startswith('st_'):
            title = clamp_text(normalize_subtask_title(post[key]), TITLE_MAX_LENGTH)
            if title:
                subtasks.append({'title': title, 'order': order})
                order += 1
    return subtasks


def sync_subtasks(task, post_data):
    """Update template subtasks without wiping completions."""
    new_subtasks = parse_subtasks_from_post(post_data)
    existing = list(task.subtasks.filter(added_by__isnull=True).order_by('order', 'pk'))

    for index, item in enumerate(new_subtasks):
        title = item['title']
        if index < len(existing):
            subtask = existing[index]
            updates = []
            if subtask.title != title:
                subtask.title = title
                updates.append('title')
            if subtask.order != index:
                subtask.order = index
                updates.append('order')
            if updates:
                subtask.save(update_fields=updates)
        else:
            Subtask.objects.create(task=task, title=title, order=index)

    for subtask in existing[len(new_subtasks):]:
        subtask.delete()


def resolve_assignee_target(assignee_type, target_id):
    if assignee_type == AssigneeType.COHORT:
        return Cohort.objects.get(pk=target_id), None
    return None, Group.objects.select_related('cohort').get(pk=target_id)


def resolve_student_ids(post, *, assignee_type, cohort, group):
    if post.get('select_all_students') == 'on':
        if assignee_type == AssigneeType.COHORT:
            return list(get_active_students_for_cohort(cohort).values_list('pk', flat=True))
        return list(get_active_students_for_group(group).values_list('pk', flat=True))
    return [int(pk) for pk in post.getlist('student_ids') if pk.isdigit()]


def _validate_staff_student_scope(user, student_ids):
    if user_is_admin(user):
        return
    if not user_is_teacher(user):
        raise ValidationError('Only staff can assign tasks to students.')
    group_ids = set(get_teacher_group_ids(user))
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
    if students.count() != len(student_ids):
        raise ValidationError('One or more selected students are invalid.')
    if not all(student.group_id in group_ids for student in students):
        raise ValidationError('One or more students are outside your groups.')


def _validate_staff_target(user, *, assignee_type, cohort, group):
    if user_is_admin(user):
        return
    if not user_is_teacher(user):
        raise ValidationError('Only staff can assign tasks.')
    group_ids = set(get_teacher_group_ids(user))
    cohort_ids = set(get_teacher_cohort_ids(user))
    if assignee_type == AssigneeType.GROUP and group.pk not in group_ids:
        raise ValidationError('You cannot assign tasks to this group.')
    if assignee_type == AssigneeType.COHORT and cohort.pk not in cohort_ids:
        raise ValidationError('You cannot assign tasks to this cohort.')


def _parse_bool(post, key, default=True):
    value = post.get(key)
    if value is None:
        return default
    return value in ('on', 'true', '1', True)


def _parse_initial_status(post):
    status = post.get('status', Task.Status.TODO)
    if status not in Task.Status.values:
        return Task.Status.TODO
    return status


def _parse_visibility(post, *, default):
    visibility = post.get('visibility', default)
    if visibility not in Task.Visibility.values:
        return default
    return visibility


def _parse_priority(post):
    priority = post.get('priority', Task.Priority.NORMAL)
    if priority not in Task.Priority.values:
        return Task.Priority.NORMAL
    return priority


@transaction.atomic
def create_student_task(*, user, post):
    title = post.get('title', '').strip()
    if not title:
        raise ValidationError('Title is required.')

    task = Task(
        author=user,
        created_by=user,
        assignee_type=Task.AssigneeType.USER,
        assignee_user=user,
        progress_mode=Task.ProgressMode.INDIVIDUAL,
        title=title,
        description=post.get('description', '').strip(),
        visibility=_parse_visibility(post, default=Task.Visibility.PRIVATE),
        priority=_parse_priority(post),
        due_date=post.get('due_date') or None,
        status=_parse_initial_status(post),
        allow_updates=_parse_bool(post, 'allow_updates', True),
        allow_comments=_parse_bool(post, 'allow_comments', True),
        allow_subtasks=_parse_bool(post, 'allow_subtasks', True),
    )
    task.full_clean()
    task.save()

    TaskEnrollment.objects.create(
        task=task,
        student=user,
        status=task.status,
    )

    for item in parse_subtasks_from_post(post):
        Subtask.objects.create(task=task, **item)
    return task


@transaction.atomic
def create_tasks_bulk(*, user, post):
    title = post.get('title', '').strip()
    if not title:
        raise ValidationError('Title is required.')

    assignee_type = post.get('assignee_type')
    target_id = post.get('assignee_target_id')
    if assignee_type not in (AssigneeType.COHORT, AssigneeType.GROUP):
        raise ValidationError('Select cohort or group.')
    if not target_id:
        raise ValidationError('Select a cohort or group.')

    cohort, group = resolve_assignee_target(assignee_type, target_id)
    _validate_staff_target(user, assignee_type=assignee_type, cohort=cohort, group=group)

    student_ids = resolve_student_ids(post, assignee_type=assignee_type, cohort=cohort, group=group)
    if not student_ids:
        raise ValidationError('Select at least one student.')

    _validate_staff_student_scope(user, student_ids)
    students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)

    task = Task.objects.create(
        author=None,
        created_by=user,
        assignee_type=Task.AssigneeType.USER,
        assignee_cohort=cohort if assignee_type == AssigneeType.COHORT else None,
        progress_mode=Task.ProgressMode.INDIVIDUAL,
        title=title,
        description=post.get('description', '').strip(),
        visibility=_parse_visibility(post, default=Task.Visibility.SHARED),
        priority=_parse_priority(post),
        due_date=post.get('due_date') or None,
        allow_updates=_parse_bool(post, 'allow_updates', True),
        allow_comments=_parse_bool(post, 'allow_comments', True),
        allow_subtasks=_parse_bool(post, 'allow_subtasks', True),
    )

    initial_status = _parse_initial_status(post)
    for student in students:
        TaskEnrollment.objects.create(task=task, student=student, status=initial_status)

    for item in parse_subtasks_from_post(post):
        Subtask.objects.create(task=task, **item)
    return task


@transaction.atomic
def create_group_task(*, user, post):
    title = post.get('title', '').strip()
    if not title:
        raise ValidationError('Title is required.')

    group_id = post.get('group_id')
    if not group_id:
        raise ValidationError('Select a group.')

    group = Group.objects.select_related('cohort').get(pk=group_id)
    _validate_staff_target(user, assignee_type=AssigneeType.GROUP, cohort=None, group=group)

    task = Task.objects.create(
        author=None,
        created_by=user,
        assignee_type=Task.AssigneeType.GROUP,
        assignee_group=group,
        progress_mode=Task.ProgressMode.SHARED,
        title=title,
        description=post.get('description', '').strip(),
        visibility=_parse_visibility(post, default=Task.Visibility.SHARED),
        priority=_parse_priority(post),
        due_date=post.get('due_date') or None,
        status=_parse_initial_status(post),
        allow_updates=_parse_bool(post, 'allow_updates', True),
        allow_comments=_parse_bool(post, 'allow_comments', True),
        allow_subtasks=_parse_bool(post, 'allow_subtasks', True),
    )

    for item in parse_subtasks_from_post(post):
        Subtask.objects.create(task=task, **item)
    return task


@transaction.atomic
def add_task_enrollments(*, user, task, post):
    from .permissions import can_add_enrollment

    if not can_add_enrollment(user, task):
        raise ValidationError('You cannot add enrollments to this task.')

    assignee_type = post.get('assignee_type', AssigneeType.GROUP)
    target_id = post.get('assignee_target_id')
    if not target_id:
        raise ValidationError('Select a cohort or group.')

    cohort, group = resolve_assignee_target(assignee_type, target_id)
    _validate_staff_target(user, assignee_type=assignee_type, cohort=cohort, group=group)

    student_ids = resolve_student_ids(post, assignee_type=assignee_type, cohort=cohort, group=group)
    if not student_ids:
        raise ValidationError('Select at least one student.')

    _validate_staff_student_scope(user, student_ids)
    existing = set(task.enrollments.values_list('student_id', flat=True))
    new_ids = [pk for pk in student_ids if pk not in existing]
    if not new_ids:
        raise ValidationError('All selected students are already enrolled.')

    initial_status = _parse_initial_status(post)
    for student_id in new_ids:
        TaskEnrollment.objects.create(
            task=task,
            student_id=student_id,
            status=initial_status,
        )
    return len(new_ids)


def toggle_subtask_completion(enrollment, subtask):
    completion = SubtaskCompletion.objects.filter(
        enrollment=enrollment,
        subtask=subtask,
    ).first()
    if completion:
        completion.delete()
    else:
        SubtaskCompletion.objects.create(enrollment=enrollment, subtask=subtask)


def build_comment_tree(enrollment):
    comments = list(
        enrollment.comments.select_related('author').order_by('created_at')
    )
    by_parent = {}
    for comment in comments:
        by_parent.setdefault(comment.parent_id, []).append(comment)

    def attach_replies(comment):
        comment.tree_replies = by_parent.get(comment.pk, [])
        for reply in comment.tree_replies:
            attach_replies(reply)

    roots = by_parent.get(None, [])
    for root in roots:
        attach_replies(root)
    return roots


def get_assignment_form_context(user):
    cohorts = Cohort.objects.filter(status=Cohort.Status.ACTIVE).order_by('-start_date', 'name')
    groups = Group.objects.select_related('cohort').filter(
        cohort__status=Cohort.Status.ACTIVE,
    ).order_by('cohort__name', 'name')

    if not user_is_admin(user):
        cohorts = get_teacher_accessible_cohorts(user).filter(status=Cohort.Status.ACTIVE)
        groups = get_teacher_accessible_groups(user).filter(cohort__status=Cohort.Status.ACTIVE)

    cohort_students = {
        str(cohort.pk): [
            {'id': s.pk, 'name': s.display_name}
            for s in get_active_students_for_cohort(cohort)
        ]
        for cohort in cohorts
    }
    group_students = {
        str(group.pk): [
            {'id': s.pk, 'name': s.display_name}
            for s in get_active_students_for_group(group)
        ]
        for group in groups
    }

    return {
        'cohorts': cohorts,
        'groups': groups,
        'cohort_students_json': cohort_students,
        'group_students_json': group_students,
    }
