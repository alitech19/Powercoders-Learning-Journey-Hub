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

from .models import Goal, GoalEnrollment, Milestone, MilestoneCompletion


class AssigneeType:
    COHORT = 'cohort'
    GROUP = 'group'


def normalize_milestone_title(raw):
    """Unwrap titles corrupted by dict-as-string saves (possibly nested)."""
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


def parse_milestones_from_post(post):
    milestones = []
    order = 0
    for key in sorted(post.keys()):
        if key.startswith('ms_'):
            title = clamp_text(normalize_milestone_title(post[key]), TITLE_MAX_LENGTH)
            if title:
                milestones.append({'title': title, 'order': order})
                order += 1
    return milestones


def sync_milestones(goal, post_data):
    """Update milestone template without wiping per-student completions."""
    new_milestones = parse_milestones_from_post(post_data)
    existing = list(goal.milestones.order_by('order', 'pk'))

    for index, ms in enumerate(new_milestones):
        title = ms['title']
        if index < len(existing):
            milestone = existing[index]
            updates = []
            if milestone.title != title:
                milestone.title = title
                updates.append('title')
            if milestone.order != index:
                milestone.order = index
                updates.append('order')
            if updates:
                milestone.save(update_fields=updates)
        else:
            Milestone.objects.create(goal=goal, title=title, order=index)

    for milestone in existing[len(new_milestones):]:
        milestone.delete()


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
        raise ValidationError('Only staff can assign goals to students.')
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
        raise ValidationError('Only staff can assign goals.')
    group_ids = set(get_teacher_group_ids(user))
    cohort_ids = set(get_teacher_cohort_ids(user))
    if assignee_type == AssigneeType.GROUP and group.pk not in group_ids:
        raise ValidationError('You cannot assign goals to this group.')
    if assignee_type == AssigneeType.COHORT and cohort.pk not in cohort_ids:
        raise ValidationError('You cannot assign goals to this cohort.')


def _parse_initial_status(post):
    status = post.get('status', GoalEnrollment.Status.NOT_STARTED)
    if status not in GoalEnrollment.Status.values:
        return GoalEnrollment.Status.NOT_STARTED
    return status


@transaction.atomic
def create_student_goal(*, user, post):
    title = post.get('title', '').strip()
    if not title:
        raise ValidationError('Title is required.')

    visibility = post.get('visibility', Goal.Visibility.PRIVATE)
    if visibility not in Goal.Visibility.values:
        visibility = Goal.Visibility.PRIVATE

    goal = Goal(
        author=user,
        created_by=user,
        title=title,
        description=post.get('description', '').strip(),
        category=post.get('category', Goal.Category.TECHNICAL),
        target_date=post.get('target_date') or None,
        visibility=visibility,
    )
    goal.full_clean()
    goal.save()

    GoalEnrollment.objects.create(
        goal=goal,
        student=user,
        status=_parse_initial_status(post),
    )

    for ms in parse_milestones_from_post(post):
        Milestone.objects.create(goal=goal, **ms)
    return goal


@transaction.atomic
def create_goals_bulk(*, user, post):
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

    visibility = post.get('visibility', Goal.Visibility.SHARED)
    if visibility not in Goal.Visibility.values:
        visibility = Goal.Visibility.SHARED

    goal = Goal.objects.create(
        author=None,
        created_by=user,
        title=title,
        description=post.get('description', '').strip(),
        category=post.get('category', Goal.Category.TECHNICAL),
        target_date=post.get('target_date') or None,
        visibility=visibility,
    )

    initial_status = _parse_initial_status(post)
    if initial_status == GoalEnrollment.Status.NOT_STARTED:
        initial_status = GoalEnrollment.Status.IN_PROGRESS

    for student in students:
        GoalEnrollment.objects.create(
            goal=goal,
            student=student,
            status=initial_status,
        )

    for ms in parse_milestones_from_post(post):
        Milestone.objects.create(goal=goal, **ms)

    return goal


def sync_enrollment_status_from_milestones(enrollment):
    if enrollment.status == GoalEnrollment.Status.COMPLETED:
        return
    if not enrollment.goal.milestones.exists():
        return
    if enrollment.milestone_completions.exists():
        enrollment.status = GoalEnrollment.Status.IN_PROGRESS
    else:
        enrollment.status = GoalEnrollment.Status.NOT_STARTED
    enrollment.save(update_fields=['status'])


def toggle_milestone_completion(enrollment, milestone):
    completion = MilestoneCompletion.objects.filter(
        enrollment=enrollment,
        milestone=milestone,
    ).first()
    if completion:
        completion.delete()
    else:
        MilestoneCompletion.objects.create(enrollment=enrollment, milestone=milestone)
    sync_enrollment_status_from_milestones(enrollment)


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
