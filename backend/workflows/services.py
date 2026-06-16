from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from cohorts.models import Cohort, Group
from config.input_limits import STEP_DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH
from config.text_validation import clamp_text
from cohorts.permissions import (
    get_active_students_for_cohort,
    get_active_students_for_group,
    get_teacher_cohort_ids,
    get_teacher_group_ids,
    user_is_admin,
    user_is_teacher,
)

from .models import StepCompletion, Workflow, WorkflowEnrollment, WorkflowStep


def parse_steps_from_post(post):
    steps = []
    index = 1
    while True:
        title = clamp_text(post.get(f'step_title_{index}', '').strip(), TITLE_MAX_LENGTH)
        if not title:
            break
        steps.append({
            'title': title,
            'description': clamp_text(
                post.get(f'step_desc_{index}', '').strip(),
                STEP_DESCRIPTION_MAX_LENGTH,
            ),
            'requires_previous': post.get(f'step_req_{index}') == 'on',
            'order': index,
        })
        index += 1
    return steps


def resolve_assignee_target(assignee_type, target_id):
    if assignee_type == Workflow.AssigneeType.COHORT:
        return Cohort.objects.get(pk=target_id), None
    return None, Group.objects.select_related('cohort').get(pk=target_id)


def resolve_student_ids(post, *, assignee_type, cohort, group, progress_mode):
    if progress_mode != Workflow.ProgressMode.INDIVIDUAL:
        return []

    if post.get('select_all_students') == 'on':
        if assignee_type == Workflow.AssigneeType.COHORT:
            return list(get_active_students_for_cohort(cohort).values_list('pk', flat=True))
        return list(get_active_students_for_group(group).values_list('pk', flat=True))

    raw_ids = post.getlist('student_ids')
    return [int(pk) for pk in raw_ids if pk.isdigit()]


def _validate_staff_assignment_scope(user, *, assignee_type, cohort, group, student_ids):
    if user_is_admin(user):
        return
    if not user_is_teacher(user):
        raise ValidationError('Only staff can manage workflow assignments.')
    group_ids = set(get_teacher_group_ids(user))
    cohort_ids = set(get_teacher_cohort_ids(user))
    if assignee_type == Workflow.AssigneeType.GROUP:
        if group.pk not in group_ids:
            raise ValidationError('You cannot assign workflows to this group.')
    elif assignee_type == Workflow.AssigneeType.COHORT:
        if cohort.pk not in cohort_ids:
            raise ValidationError('You cannot assign workflows to this cohort.')
    if student_ids:
        students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
        if students.count() != len(student_ids):
            raise ValidationError('One or more selected students are invalid.')
        if not all(student.group_id in group_ids for student in students):
            raise ValidationError('One or more students are outside your groups.')


@transaction.atomic
def create_workflow(*, user, post):
    title = post.get('title', '').strip()
    if not title:
        raise ValidationError('Title is required.')

    progress_mode = post.get('progress_mode')
    assignee_type = post.get('assignee_type')
    target_id = post.get('assignee_target_id')

    if progress_mode not in Workflow.ProgressMode.values:
        raise ValidationError('Invalid progress mode.')
    if assignee_type not in Workflow.AssigneeType.values:
        raise ValidationError('Invalid assignee type.')
    if not target_id:
        raise ValidationError('Select a cohort or group.')

    cohort, group = resolve_assignee_target(assignee_type, target_id)
    student_ids = resolve_student_ids(
        post,
        assignee_type=assignee_type,
        cohort=cohort,
        group=group,
        progress_mode=progress_mode,
    )
    if progress_mode == Workflow.ProgressMode.INDIVIDUAL and not student_ids:
        raise ValidationError('Select at least one student for individual workflows.')

    _validate_staff_assignment_scope(
        user,
        assignee_type=assignee_type,
        cohort=cohort,
        group=group,
        student_ids=student_ids,
    )

    steps = parse_steps_from_post(post)
    if not steps:
        raise ValidationError('Add at least one step.')

    visibility = post.get('visibility', Workflow.Visibility.PUBLIC)
    if visibility not in Workflow.Visibility.values:
        visibility = Workflow.Visibility.PUBLIC

    workflow = Workflow(
        title=title,
        description=post.get('description', '').strip(),
        visibility=visibility,
        progress_mode=progress_mode,
        assignee_type=assignee_type,
        assignee_cohort=cohort,
        assignee_group=group,
        created_by=user,
    )
    workflow.full_clean()
    workflow.save()

    for step_data in steps:
        WorkflowStep.objects.create(workflow=workflow, **step_data)

    if progress_mode == Workflow.ProgressMode.INDIVIDUAL:
        students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
        WorkflowEnrollment.objects.bulk_create([
            WorkflowEnrollment(workflow=workflow, student=student)
            for student in students
        ])
        notify_students = students
    else:
        from .permissions import get_workflow_assigned_students

        notify_students = get_workflow_assigned_students(workflow)

    from accounts.notifications.scheduling import schedule_workflow_assigned

    schedule_workflow_assigned(workflow=workflow, students=notify_students, actor=user)
    return workflow


@transaction.atomic
def update_workflow_metadata(*, workflow, post):
    title = post.get('title', '').strip()
    if not title:
        raise ValidationError('Title is required.')

    visibility = post.get('visibility', workflow.visibility)
    if visibility not in Workflow.Visibility.values:
        raise ValidationError('Invalid visibility.')

    workflow.title = title
    workflow.description = post.get('description', '').strip()
    workflow.visibility = visibility
    workflow.save(update_fields=['title', 'description', 'visibility', 'updated_at'])
    return workflow


@transaction.atomic
def update_workflow_assignment(*, workflow, user, post):
    progress_mode = post.get('progress_mode')
    assignee_type = post.get('assignee_type')
    target_id = post.get('assignee_target_id')

    if progress_mode not in Workflow.ProgressMode.values:
        raise ValidationError('Invalid progress mode.')
    if assignee_type not in Workflow.AssigneeType.values:
        raise ValidationError('Invalid assignee type.')
    if not target_id:
        raise ValidationError('Select a cohort or group.')

    cohort, group = resolve_assignee_target(assignee_type, target_id)
    old_mode = workflow.progress_mode
    student_ids = resolve_student_ids(
        post,
        assignee_type=assignee_type,
        cohort=cohort,
        group=group,
        progress_mode=progress_mode,
    )
    if progress_mode == Workflow.ProgressMode.INDIVIDUAL and not student_ids:
        raise ValidationError('Select at least one student for individual workflows.')

    _validate_staff_assignment_scope(
        user,
        assignee_type=assignee_type,
        cohort=cohort,
        group=group,
        student_ids=student_ids,
    )

    workflow.progress_mode = progress_mode
    workflow.assignee_type = assignee_type
    workflow.assignee_cohort = cohort
    workflow.assignee_group = group
    workflow.full_clean()
    workflow.save()

    if progress_mode == Workflow.ProgressMode.SHARED:
        workflow.enrollments.all().delete()
        StepCompletion.objects.filter(workflow=workflow, student__isnull=False).delete()
    else:
        StepCompletion.objects.filter(workflow=workflow, student__isnull=True).delete()
        students = User.objects.filter(pk__in=student_ids, role=User.Role.STUDENT, is_active=True)
        new_ids = set(students.values_list('pk', flat=True))
        existing_ids = set(workflow.enrollments.values_list('student_id', flat=True))

        removed_ids = existing_ids - new_ids
        if removed_ids:
            StepCompletion.objects.filter(workflow=workflow, student_id__in=removed_ids).delete()
            WorkflowEnrollment.objects.filter(workflow=workflow, student_id__in=removed_ids).delete()

        for student_id in new_ids - existing_ids:
            WorkflowEnrollment.objects.create(workflow=workflow, student_id=student_id)

        if new_ids - existing_ids:
            from accounts.notifications.scheduling import schedule_workflow_assigned

            added_students = User.objects.filter(
                pk__in=new_ids - existing_ids,
                role=User.Role.STUDENT,
                is_active=True,
            )
            schedule_workflow_assigned(workflow=workflow, students=added_students, actor=user)

    if old_mode != progress_mode:
        StepCompletion.objects.filter(workflow=workflow).delete()

    return workflow


def get_assignment_form_context(user):
    cohorts = Cohort.objects.filter(status=Cohort.Status.ACTIVE).order_by('-start_date', 'name')
    groups = Group.objects.select_related('cohort').filter(
        cohort__status=Cohort.Status.ACTIVE,
    ).order_by('cohort__name', 'name')

    if not user_is_admin(user):
        from cohorts.permissions import get_teacher_accessible_cohorts, get_teacher_accessible_groups

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
