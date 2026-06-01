from workflows.models import Workflow, WorkflowEnrollment, WorkflowStep


def make_workflow(
    created_by,
    *,
    title='Test workflow',
    visibility=Workflow.Visibility.PUBLIC,
    progress_mode=Workflow.ProgressMode.SHARED,
    assignee_type=Workflow.AssigneeType.GROUP,
    assignee_group=None,
    assignee_cohort=None,
    **kwargs,
):
    workflow = Workflow(
        title=title,
        visibility=visibility,
        progress_mode=progress_mode,
        assignee_type=assignee_type,
        assignee_group=assignee_group,
        assignee_cohort=assignee_cohort,
        created_by=created_by,
        **kwargs,
    )
    workflow.full_clean()
    workflow.save()
    return workflow


def add_step(workflow, *, title='Step', order=1, requires_previous=True):
    return WorkflowStep.objects.create(
        workflow=workflow,
        title=title,
        order=order,
        requires_previous=requires_previous,
    )


def enroll_student(workflow, student):
    return WorkflowEnrollment.objects.create(workflow=workflow, student=student)
