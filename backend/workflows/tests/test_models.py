from django.core.exceptions import ValidationError
from django.test import TestCase

from test_utils.cohorts import make_cohort, make_group
from test_utils.users import make_teacher
from test_utils.workflows import add_step, make_workflow
from workflows.models import Workflow


class WorkflowModelTests(TestCase):
    def setUp(self):
        self.teacher = make_teacher('wf@example.com')
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)

    def test_str(self):
        wf = make_workflow(self.teacher, title='My WF', assignee_group=self.group)
        self.assertEqual(str(wf), 'My WF')

    def test_is_private_and_is_shared(self):
        wf = make_workflow(
            self.teacher,
            visibility=Workflow.Visibility.PRIVATE,
            progress_mode=Workflow.ProgressMode.INDIVIDUAL,
            assignee_group=self.group,
        )
        self.assertTrue(wf.is_private)
        self.assertFalse(wf.is_shared)

    def test_group_assignee_requires_group_not_cohort(self):
        wf = Workflow(
            title='Bad',
            progress_mode=Workflow.ProgressMode.SHARED,
            assignee_type=Workflow.AssigneeType.GROUP,
            assignee_cohort=self.cohort,
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            wf.full_clean()

    def test_step_count_and_enrolled_count(self):
        wf = make_workflow(
            self.teacher,
            progress_mode=Workflow.ProgressMode.INDIVIDUAL,
            assignee_group=self.group,
        )
        add_step(wf, title='S1', order=1)
        self.assertEqual(wf.step_count, 1)
        self.assertEqual(wf.enrolled_count, 0)

    def test_get_assignee_label_group(self):
        wf = make_workflow(self.teacher, assignee_group=self.group)
        self.assertIn(self.group.name, wf.get_assignee_label())
