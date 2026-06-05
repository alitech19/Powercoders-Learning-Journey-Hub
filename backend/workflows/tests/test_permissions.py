from django.test import TestCase

from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import make_admin, make_student, make_teacher
from test_utils.workflows import enroll_student, make_workflow
from workflows.models import Workflow
from workflows.permissions import (
    can_manage_workflow,
    can_view_workflow,
    get_visible_workflows_for_user,
    is_workflow_owner,
)


class WorkflowPermissionTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.other_group = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.other_student = make_student(
            'other@example.com',
            cohort=self.cohort,
            group=self.other_group,
        )
        self.admin = make_admin('admin@example.com')

    def test_student_sees_public_shared_group_workflow(self):
        wf = make_workflow(
            self.teacher,
            assignee_group=self.group,
            progress_mode=Workflow.ProgressMode.SHARED,
        )
        self.assertTrue(can_view_workflow(self.student, wf))

    def test_student_cannot_see_private_workflow(self):
        wf = make_workflow(
            self.teacher,
            visibility=Workflow.Visibility.PRIVATE,
            assignee_group=self.group,
        )
        self.assertFalse(can_view_workflow(self.student, wf))

    def test_student_not_assigned_to_other_group(self):
        wf = make_workflow(self.teacher, assignee_group=self.other_group)
        self.assertFalse(can_view_workflow(self.student, wf))

    def test_individual_enrollment_required(self):
        wf = make_workflow(
            self.teacher,
            progress_mode=Workflow.ProgressMode.INDIVIDUAL,
            assignee_group=self.group,
        )
        self.assertFalse(can_view_workflow(self.student, wf))
        enroll_student(wf, self.student)
        self.assertTrue(can_view_workflow(self.student, wf))

    def test_admin_can_manage_any(self):
        wf = make_workflow(self.teacher, assignee_group=self.group)
        self.assertTrue(can_manage_workflow(self.admin, wf))

    def test_owner_can_manage_without_group_assignment(self):
        other_teacher = make_teacher('owner-teacher@example.com')
        wf = make_workflow(other_teacher, assignee_group=self.group)
        self.assertTrue(can_manage_workflow(other_teacher, wf))

    def test_owner_flag(self):
        wf = make_workflow(self.teacher, assignee_group=self.group)
        self.assertTrue(is_workflow_owner(self.teacher, wf))
        self.assertFalse(is_workflow_owner(self.student, wf))

    def test_visible_workflows_for_student_filters_correctly(self):
        visible = make_workflow(self.teacher, title='Visible', assignee_group=self.group)
        make_workflow(self.teacher, title='Hidden', assignee_group=self.other_group)
        private = make_workflow(
            self.teacher,
            title='Private',
            visibility=Workflow.Visibility.PRIVATE,
            assignee_group=self.group,
        )
        qs = get_visible_workflows_for_user(self.student)
        titles = set(qs.values_list('title', flat=True))
        self.assertIn(visible.title, titles)
        self.assertNotIn('Hidden', titles)
        self.assertNotIn(private.title, titles)
