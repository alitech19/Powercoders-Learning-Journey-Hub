from django.test import TestCase

from feedback.models import FeedbackEntry
from feedback.services import (
    build_section_context,
    can_delete_entry,
    create_entry,
    get_entries_for,
)
from goals.feedback_handlers import can_add_enrollment_feedback, can_view_enrollment_feedback
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.goals import enroll_student, make_staff_goal
from test_utils.users import make_admin, make_student, make_teacher


class FeedbackServicesTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student(
            'student@example.com',
            cohort=self.cohort,
            group=self.group,
        )
        self.goal = make_staff_goal(self.teacher, visibility=self.goal_visibility_shared())
        self.enrollment = enroll_student(self.goal, self.student)

    @staticmethod
    def goal_visibility_shared():
        from goals.models import Goal

        return Goal.Visibility.SHARED

    def test_create_and_get_entries(self):
        entry = create_entry(
            target=self.enrollment,
            author=self.teacher,
            body='Great progress',
        )
        self.assertIsNotNone(entry)
        entries = list(get_entries_for(self.enrollment))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].body, 'Great progress')

    def test_create_entry_rejects_empty_body(self):
        self.assertIsNone(create_entry(target=self.enrollment, author=self.teacher, body='  '))

    def test_can_delete_entry_author_or_admin(self):
        entry = create_entry(
            target=self.enrollment,
            author=self.teacher,
            body='Note',
        )
        other_teacher = make_teacher('other@example.com')
        self.assertFalse(can_delete_entry(other_teacher, entry))
        self.assertTrue(can_delete_entry(self.teacher, entry))
        self.assertTrue(can_delete_entry(make_admin('admin@example.com'), entry))

    def test_build_section_context_for_enrollment(self):
        create_entry(target=self.enrollment, author=self.teacher, body='Hi')
        ctx = build_section_context(target=self.enrollment, viewer=self.student)
        self.assertIsNotNone(ctx)
        self.assertEqual(len(ctx['entries']), 1)
        self.assertFalse(ctx['can_add_feedback'])

        teacher_ctx = build_section_context(target=self.enrollment, viewer=self.teacher)
        self.assertTrue(teacher_ctx['can_add_feedback'])

    def test_build_section_context_none_when_cannot_view(self):
        from goals.models import Goal

        private_goal = make_staff_goal(
            self.teacher,
            visibility=Goal.Visibility.PRIVATE,
        )
        enrollment = enroll_student(private_goal, self.student)
        ctx = build_section_context(target=enrollment, viewer=self.student)
        self.assertIsNone(ctx)

    def test_handlers_registered_for_goal_enrollment(self):
        self.assertTrue(can_view_enrollment_feedback(self.student, self.enrollment))
        self.assertTrue(can_add_enrollment_feedback(self.teacher, self.enrollment))
