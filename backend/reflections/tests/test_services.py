from django.test import TestCase

from reflections.constants import TAG_WEEKLY
from reflections.permissions import filter_reflections_queryset, order_reflections_newest_first
from reflections.models import Reflection
from test_utils.reflections import make_reflection
from test_utils.users import make_student


class ReflectionServicesQueryTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com')

    def test_filter_by_tag_and_search(self):
        make_reflection(self.student, title='Weekly one', tags=[TAG_WEEKLY])
        make_reflection(self.student, title='Project x', tags=['project'])
        qs = Reflection.objects.filter(author=self.student)
        filtered = filter_reflections_queryset(qs, tag=TAG_WEEKLY, search='week')
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().title, 'Weekly one')

    def test_order_reflections_newest_first(self):
        older = make_reflection(self.student, title='Older')
        newer = make_reflection(self.student, title='Newer')
        newer.final_reflection_at = newer.created_at
        newer.save(update_fields=['final_reflection_at'])
        ordered = list(
            order_reflections_newest_first(
                Reflection.objects.filter(pk__in=[older.pk, newer.pk])
            ).values_list('pk', flat=True)
        )
        self.assertEqual(ordered[0], newer.pk)
