from django.test import Client, TestCase
from django.urls import reverse

from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.users import login_as, make_teacher
from test_utils.workflows import add_step, make_workflow
from workflows.models import WorkflowStep


class WorkflowAccessViewTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.other_group = make_group(self.cohort, name='G2')
        self.teacher = make_teacher('teacher@example.com')
        self.other_teacher = make_teacher('other@example.com')
        assign_teacher(self.group, self.teacher)
        assign_teacher(self.other_group, self.other_teacher)
        self.workflow = make_workflow(
            self.other_teacher,
            title='Other group flow',
            assignee_group=self.other_group,
            visibility='public',
        )

    def test_teacher_out_of_scope_gets_access_denied_not_not_found(self):
        login_as(self.client, self.teacher)
        response = self.client.get(reverse('workflows:detail', args=[self.workflow.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Access denied', status_code=403)


class WorkflowStepAddTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        login_as(self.client, self.teacher)
        self.workflow = make_workflow(self.teacher, assignee_group=self.group)
        add_step(self.workflow, title='First step', order=1)

    def test_step_add_creates_new_step_with_incremented_order(self):
        url = reverse('workflows:step_add', kwargs={'workflow_pk': self.workflow.pk})
        response = self.client.post(url, {
            'title': 'Second step',
            'description': 'Details',
            'requires_previous': 'on',
        })
        self.assertEqual(response.status_code, 302)
        steps = list(WorkflowStep.objects.filter(workflow=self.workflow).order_by('order', 'pk'))
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].title, 'First step')
        self.assertEqual(steps[1].title, 'Second step')
        self.assertEqual(steps[1].order, 2)

    def test_step_add_appends_after_multiple_existing_steps(self):
        add_step(self.workflow, title='Middle step', order=2)
        url = reverse('workflows:step_add', kwargs={'workflow_pk': self.workflow.pk})
        self.client.post(url, {'title': 'Third step', 'requires_previous': 'on'})
        titles = list(
            WorkflowStep.objects.filter(workflow=self.workflow)
            .order_by('order', 'pk')
            .values_list('title', flat=True)
        )
        self.assertEqual(titles, ['First step', 'Middle step', 'Third step'])
