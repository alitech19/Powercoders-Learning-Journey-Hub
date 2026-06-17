import ast
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from accounts.models import User
from cohorts.models import Cohort, Group
from config.input_limits import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH
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

from .models import Subtask, SubtaskEnrollment, Task, TaskComment, TaskEnrollment, TaskUpdate


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


def _parse_subtask_due_date(raw):
    value = (raw or '').strip()
    return value or None


def _parse_subtask_priority(raw):
    priority = (raw or Task.Priority.NORMAL).strip()
    if priority not in Task.Priority.values:
        return Task.Priority.NORMAL
    return priority


def _parse_subtask_description(raw):
    return clamp_text((raw or '').strip(), DESCRIPTION_MAX_LENGTH)


def parse_subtasks_from_post(post):
    """Parse template subtasks from POST (title + optional description, priority, due)."""
    indexed = {}
    legacy = {}

    for key, raw in post.items():
        match = re.fullmatch(r'st_(\d+)_(title|description|priority|due_date)', key)
        if match:
            index = int(match.group(1))
            field = match.group(2)
            indexed.setdefault(index, {})[field] = raw
            continue
        match = re.fullmatch(r'st_(\d+)', key)
        if match:
            legacy[int(match.group(1))] = raw

    if indexed:
        subtasks = []
        for index in sorted(indexed.keys()):
            item = indexed[index]
            title = clamp_text(normalize_subtask_title(item.get('title', '')), TITLE_MAX_LENGTH)
            if not title:
                continue
            subtasks.append({
                'title': title,
                'description': _parse_subtask_description(item.get('description')),
                'priority': _parse_subtask_priority(item.get('priority')),
                'due_date': _parse_subtask_due_date(item.get('due_date')),
                'order': len(subtasks),
            })
        return subtasks

    subtasks = []
    for index in sorted(legacy.keys()):
        title = clamp_text(normalize_subtask_title(legacy[index]), TITLE_MAX_LENGTH)
        if title:
            subtasks.append({
                'title': title,
                'description': '',
                'priority': Task.Priority.NORMAL,
                'due_date': None,
                'order': len(subtasks),
            })
    return subtasks


def subtasks_visible_to_enrollment(enrollment):
    return enrollment.task.subtasks.filter(
        Q(added_by__isnull=True) | Q(added_by_id=enrollment.student_id)
    )


@transaction.atomic
def sync_subtask_enrollments(enrollment):
    """Ensure SubtaskEnrollment rows exist for each visible subtask."""
    for subtask in subtasks_visible_to_enrollment(enrollment).order_by('order', 'pk'):
        SubtaskEnrollment.objects.get_or_create(
            enrollment=enrollment,
            subtask=subtask,
            defaults={'status': Task.Status.TODO},
        )


def ensure_enrollment_for_subtasks(task, student):
    """Lazy enrollment for group-shared subtask progress (per student)."""
    enrollment, created = TaskEnrollment.objects.get_or_create(
        task=task,
        student=student,
        defaults={'status': task.status},
    )
    if created:
        sync_subtask_enrollments(enrollment)
    else:
        sync_subtask_enrollments(enrollment)
    return enrollment


def sync_subtasks(task, post_data):
    """Update template subtasks without resetting student SubtaskEnrollment status."""
    new_subtasks = parse_subtasks_from_post(post_data)
    existing = list(task.subtasks.filter(added_by__isnull=True).order_by('order', 'pk'))

    for index, item in enumerate(new_subtasks):
        title = item['title']
        if index < len(existing):
            subtask = existing[index]
            updates = []
            for field in ('title', 'description', 'priority', 'due_date', 'order'):
                value = item[field] if field != 'order' else index
                if getattr(subtask, field) != value:
                    setattr(subtask, field, value)
                    updates.append(field)
            if updates:
                subtask.save(update_fields=updates)
        else:
            Subtask.objects.create(
                task=task,
                title=title,
                description=item['description'],
                priority=item['priority'],
                due_date=item['due_date'],
                order=index,
            )

    for subtask in existing[len(new_subtasks):]:
        subtask.delete()

    for enrollment in task.enrollments.all():
        sync_subtask_enrollments(enrollment)


def set_subtask_status(enrollment, subtask, status):
    if status not in Task.Status.values:
        raise ValidationError('Invalid subtask status.')
    subtask_enrollment, _ = SubtaskEnrollment.objects.get_or_create(
        enrollment=enrollment,
        subtask=subtask,
        defaults={'status': Task.Status.TODO},
    )
    subtask_enrollment.status = status
    subtask_enrollment.save(update_fields=['status', 'completed_at'])


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


def _create_template_subtasks(task, post):
    for item in parse_subtasks_from_post(post):
        Subtask.objects.create(task=task, **item)


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

    enrollment = TaskEnrollment.objects.create(
        task=task,
        student=user,
        status=task.status,
    )
    _create_template_subtasks(task, post)
    sync_subtask_enrollments(enrollment)
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

    _create_template_subtasks(task, post)

    from resources.entity_links import apply_entity_resource_container

    apply_entity_resource_container(
        entity=task,
        user=user,
        post=post,
        assignee_group=None,
    )

    initial_status = _parse_initial_status(post)
    for student in students:
        enrollment = TaskEnrollment.objects.create(
            task=task,
            student=student,
            status=initial_status,
        )
        sync_subtask_enrollments(enrollment)

    from accounts.notifications.scheduling import schedule_task_assigned

    schedule_task_assigned(task=task, students=students, actor=user)
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

    _create_template_subtasks(task, post)

    from resources.entity_links import apply_entity_resource_container

    apply_entity_resource_container(
        entity=task,
        user=user,
        post=post,
        assignee_group=group,
    )

    enrolled_students = list(get_active_students_for_group(group))
    for student in enrolled_students:
        enrollment = TaskEnrollment.objects.create(
            task=task,
            student=student,
            status=task.status,
        )
        sync_subtask_enrollments(enrollment)

    from accounts.notifications.scheduling import schedule_task_assigned

    schedule_task_assigned(task=task, students=enrolled_students, actor=user)
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
    added_students = []
    for student_id in new_ids:
        enrollment = TaskEnrollment.objects.create(
            task=task,
            student_id=student_id,
            status=initial_status,
        )
        sync_subtask_enrollments(enrollment)
        added_students.append(enrollment.student)

    from accounts.notifications.scheduling import schedule_task_assigned

    schedule_task_assigned(task=task, students=added_students, actor=user)
    return len(new_ids)


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
