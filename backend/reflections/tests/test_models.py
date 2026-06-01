from django.test import TestCase
from django.utils import timezone

from reflections.constants import EXPECTATIONS_TEMPLATE, FINAL_REFLECTION_TEMPLATE, TAG_CUSTOM, TAG_WEEKLY
from reflections.models import Reflection, expectations_is_started, final_reflection_is_started
from test_utils.reflections import make_reflection
from test_utils.users import make_student


class ReflectionModelTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com', display_name='Sam')

    def test_str(self):
        r = make_reflection(self.student, title='Week 1')
        self.assertIn('Sam', str(r))
        self.assertIn('Week 1', str(r))

    def test_expectations_not_started_with_template_only(self):
        self.assertFalse(expectations_is_started(EXPECTATIONS_TEMPLATE))
        r = make_reflection(self.student, expectations=EXPECTATIONS_TEMPLATE)
        self.assertFalse(r.has_expectations)

    def test_expectations_started_with_real_content(self):
        text = 'I plan to finish the project.\n'
        self.assertTrue(expectations_is_started(text))
        r = make_reflection(self.student, expectations=text)
        self.assertTrue(r.has_expectations)

    def test_final_reflection_and_wellbeing_visibility(self):
        r = make_reflection(self.student, final_reflection=FINAL_REFLECTION_TEMPLATE)
        self.assertFalse(r.has_final_reflection)
        self.assertFalse(r.show_wellbeing)

        r.final_reflection = 'Done well this week.'
        r.save(update_fields=['final_reflection'])
        self.assertTrue(final_reflection_is_started(r.final_reflection))
        self.assertTrue(r.has_final_reflection)
        self.assertTrue(r.show_wellbeing)

    def test_tag_labels(self):
        r = make_reflection(
            self.student,
            tags=[TAG_WEEKLY, TAG_CUSTOM],
            custom_label='Sprint 1',
        )
        self.assertEqual(r.tag_labels, ['Weekly', 'Sprint 1'])

    def test_wellbeing_filled_count(self):
        r = make_reflection(
            self.student,
            energy=Reflection.WellbeingLevel.GOOD,
            sleep=Reflection.WellbeingLevel.OKAY,
        )
        self.assertEqual(r.wellbeing_filled_count, 2)

    def test_display_date_prefers_final_then_expectations(self):
        r = make_reflection(self.student)
        self.assertEqual(r.display_date, r.created_at)
        now = timezone.now()
        r.expectations_at = now
        r.save(update_fields=['expectations_at'])
        self.assertEqual(r.display_date, now)
