from datetime import date

from django.test import TestCase
from django.urls import reverse

from test_utils.cohorts import make_cohort, make_group
from test_utils.goals import make_student_goal
from test_utils.users import login_as, make_student


class GoalEditFormPrefillTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort, name='G1')
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )

    def test_goal_edit_prefills_target_date(self):
        goal = make_student_goal(self.student)
        goal.target_date = date(2026, 7, 4)
        goal.save(update_fields=['target_date'])

        login_as(self.client, self.student)
        response = self.client.get(reverse('goals:edit', args=[goal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-07-04"')
        self.assertContains(response, 'name="target_date"')

    def test_goal_create_preserves_target_date_on_validation_error(self):
        login_as(self.client, self.student)
        response = self.client.post(reverse('goals:create'), {
            'title': '',
            'description': 'desc',
            'category': 'technical',
            'target_date': '2026-09-15',
            'visibility': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-09-15"')

    def test_goal_edit_retains_target_date_after_validation_error(self):
        goal = make_student_goal(self.student)
        goal.target_date = date(2026, 7, 4)
        goal.save(update_fields=['target_date'])

        login_as(self.client, self.student)
        response = self.client.post(reverse('goals:edit', args=[goal.pk]), {
            'title': '',
            'description': '',
            'category': 'technical',
            'target_date': '2026-07-04',
            'visibility': 'private',
            'status': 'in_progress',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-07-04"')
