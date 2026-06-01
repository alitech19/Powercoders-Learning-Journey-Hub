from django.test import TestCase

from test_utils.cohorts import make_cohort, make_group
from test_utils.users import make_teacher
from test_utils.workflows import add_step, make_workflow
from workflows.models import StepCompletion, Workflow
from workflows.permissions import build_step_data, shared_progress_pct
from workflows.services import parse_steps_from_post


class WorkflowServicesTests(TestCase):
    def test_parse_steps_from_post(self):
        post = {
            'step_title_1': 'First',
            'step_desc_1': 'Desc',
            'step_req_1': 'on',
            'step_title_2': 'Second',
            'step_req_2': '',
            'step_title_3': '',
        }
        steps = parse_steps_from_post(post)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]['title'], 'First')
        self.assertTrue(steps[0]['requires_previous'])
        self.assertFalse(steps[1]['requires_previous'])

    def test_build_step_data_locks_after_incomplete_previous(self):
        teacher = make_teacher('t@example.com')
        group = make_group(make_cohort())
        wf = make_workflow(teacher, assignee_group=group)
        s1 = add_step(wf, title='S1', order=1, requires_previous=False)
        s2 = add_step(wf, title='S2', order=2, requires_previous=True)

        data = build_step_data(teacher, wf)
        self.assertFalse(data[0]['locked'])
        self.assertTrue(data[1]['locked'])

        StepCompletion.objects.create(workflow=wf, step=s1, student=None)
        data = build_step_data(teacher, wf)
        self.assertTrue(data[0]['done'])
        self.assertFalse(data[1]['locked'])

    def test_shared_progress_pct(self):
        teacher = make_teacher('t@example.com')
        group = make_group(make_cohort())
        wf = make_workflow(teacher, assignee_group=group)
        s1 = add_step(wf, order=1)
        add_step(wf, order=2, title='S2')
        self.assertEqual(shared_progress_pct(wf), 0)
        StepCompletion.objects.create(workflow=wf, step=s1, student=None)
        self.assertEqual(shared_progress_pct(wf), 50)
