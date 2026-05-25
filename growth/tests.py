from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from cohorts.models import Cohort, Group, GroupTeacher

from .models import DailyJournalEntry, Feedback, Goal, WeeklyReflection
from .selectors import (
    get_students_for_teacher,
    get_visible_goals_for_user,
    get_visible_journal_entries_for_user,
    get_visible_reflections_for_user,
)
from .services.permissions import (
    can_create_feedback,
    can_edit_journal_entry,
    can_view_goal,
    can_view_journal_entry,
    can_view_reflection,
)


class GrowthTestBase(TestCase):
    """Shared fixture for all growth tests."""

    @classmethod
    def setUpTestData(cls):
        cls.cohort = Cohort.objects.create(
            name='Cohort 1', start_date=date(2026, 1, 1),
        )
        cls.group = Group.objects.create(cohort=cls.cohort, name='Group A')
        cls.other_group = Group.objects.create(cohort=cls.cohort, name='Group B')

        cls.student = User.objects.create_user(
            email='student@test.com', password='pass',
            display_name='Student', role=User.Role.STUDENT,
            cohort=cls.cohort, group=cls.group,
        )
        cls.other_student = User.objects.create_user(
            email='other@test.com', password='pass',
            display_name='Other', role=User.Role.STUDENT,
            cohort=cls.cohort, group=cls.other_group,
        )

        cls.teacher = User.objects.create_user(
            email='teacher@test.com', password='pass',
            display_name='Teacher', role=User.Role.TEACHER,
        )
        GroupTeacher.objects.create(group=cls.group, teacher=cls.teacher)

        cls.unrelated_teacher = User.objects.create_user(
            email='unrelated@test.com', password='pass',
            display_name='Unrelated', role=User.Role.TEACHER,
        )
        GroupTeacher.objects.create(
            group=cls.other_group, teacher=cls.unrelated_teacher,
        )

        cls.admin = User.objects.create_user(
            email='admin@test.com', password='pass',
            display_name='Admin', role=User.Role.ADMIN,
        )

        today = date.today()
        cls.private_goal = Goal.objects.create(
            student=cls.student,
            title='Private goal',
            description='My private SMART goal description.',
            target_date=today + timedelta(days=30),
            progress_percent=10,
            visibility=Goal.Visibility.PRIVATE,
        )
        cls.public_goal = Goal.objects.create(
            student=cls.student,
            title='Public goal',
            description='My public SMART goal description.',
            target_date=today + timedelta(days=30),
            progress_percent=25,
            visibility=Goal.Visibility.PUBLIC,
        )

        cls.reflection = WeeklyReflection(
            student=cls.student,
            week_start=today - timedelta(days=today.weekday()),
            week_end=today - timedelta(days=today.weekday()) + timedelta(days=6),
            content='More of:\nCoding\n\nLess of:\nProcrastination',
        )
        cls.reflection.save()

        cls.journal_entry = DailyJournalEntry.objects.create(
            student=cls.student,
            entry_date=today,
            content='What did I do today?\nStudied forms.\n\nWhat progress did I make?\nCompleted exercise.',
        )


# -- Goal model tests ------------------------------------------------------

class GoalModelTests(GrowthTestBase):

    def test_create_goal_with_simplified_fields(self):
        goal = Goal.objects.create(
            student=self.student,
            title='Test goal',
            description='A clear SMART description.',
            target_date=date.today() + timedelta(days=14),
            progress_percent=50,
        )
        self.assertEqual(goal.title, 'Test goal')
        self.assertEqual(goal.progress_percent, 50)
        self.assertEqual(goal.status, Goal.Status.ACTIVE)

    def test_progress_percent_capped_at_100(self):
        goal = Goal(
            student=self.student,
            title='Over 100',
            description='Desc',
            target_date=date.today() + timedelta(days=7),
            progress_percent=150,
        )
        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_progress_percent_cannot_be_negative(self):
        goal = Goal(
            student=self.student,
            title='Negative',
            description='Desc',
            target_date=date.today() + timedelta(days=7),
            progress_percent=-5,
        )
        with self.assertRaises(ValidationError):
            goal.full_clean()

    def test_mark_achieved_sets_progress_100(self):
        goal = Goal.objects.create(
            student=self.student,
            title='Progress test',
            description='Desc',
            target_date=date.today() + timedelta(days=7),
            progress_percent=60,
        )
        goal.status = Goal.Status.ACHIEVED
        goal.save()
        goal.refresh_from_db()
        self.assertEqual(goal.progress_percent, 100)
        self.assertIsNotNone(goal.achieved_at)


# -- Goal visibility -------------------------------------------------------

class GoalVisibilityTests(GrowthTestBase):

    def test_student_sees_own_private_goal(self):
        self.assertTrue(can_view_goal(self.student, self.private_goal))

    def test_teacher_cannot_see_private_goal(self):
        self.assertFalse(can_view_goal(self.teacher, self.private_goal))

    def test_admin_cannot_see_private_goal(self):
        self.assertFalse(can_view_goal(self.admin, self.private_goal))

    def test_other_student_cannot_see_private_goal(self):
        self.assertFalse(can_view_goal(self.other_student, self.private_goal))

    def test_other_student_cannot_see_public_goal(self):
        self.assertFalse(can_view_goal(self.other_student, self.public_goal))

    def test_teacher_can_see_public_goal_of_assigned_student(self):
        self.assertTrue(can_view_goal(self.teacher, self.public_goal))

    def test_unrelated_teacher_cannot_see_public_goal(self):
        self.assertFalse(
            can_view_goal(self.unrelated_teacher, self.public_goal)
        )

    def test_admin_can_see_public_goal(self):
        self.assertTrue(can_view_goal(self.admin, self.public_goal))


class GoalSelectorTests(GrowthTestBase):

    def test_student_selector_returns_own_goals(self):
        goals = get_visible_goals_for_user(self.student)
        self.assertIn(self.private_goal, goals)
        self.assertIn(self.public_goal, goals)

    def test_teacher_selector_returns_only_public(self):
        goals = get_visible_goals_for_user(self.teacher)
        self.assertIn(self.public_goal, goals)
        self.assertNotIn(self.private_goal, goals)

    def test_other_student_selector_returns_nothing(self):
        goals = get_visible_goals_for_user(self.other_student)
        self.assertEqual(goals.count(), 0)


# -- Reflection model tests ------------------------------------------------

class ReflectionModelTests(GrowthTestBase):

    def test_create_reflection_with_content(self):
        ref = WeeklyReflection(
            student=self.other_student,
            week_start=date(2026, 5, 18),
            week_end=date(2026, 5, 24),
            content='More of:\nReading docs\n\nLess of:\nGuessing',
        )
        ref.save()
        self.assertEqual(ref.content, 'More of:\nReading docs\n\nLess of:\nGuessing')

    def test_empty_content_raises_validation_error(self):
        ref = WeeklyReflection(
            student=self.other_student,
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
            content='   ',
        )
        with self.assertRaises(ValidationError):
            ref.full_clean()


# -- Reflection visibility -------------------------------------------------

class ReflectionVisibilityTests(GrowthTestBase):

    def test_student_sees_own_reflection(self):
        self.assertTrue(can_view_reflection(self.student, self.reflection))

    def test_teacher_sees_assigned_student_reflection(self):
        self.assertTrue(can_view_reflection(self.teacher, self.reflection))

    def test_other_student_cannot_see_reflection(self):
        self.assertFalse(
            can_view_reflection(self.other_student, self.reflection)
        )

    def test_unrelated_teacher_cannot_see_reflection(self):
        self.assertFalse(
            can_view_reflection(self.unrelated_teacher, self.reflection)
        )

    def test_admin_sees_reflection(self):
        self.assertTrue(can_view_reflection(self.admin, self.reflection))


class ReflectionSelectorTests(GrowthTestBase):

    def test_student_selector_returns_own_reflections(self):
        reflections = get_visible_reflections_for_user(self.student)
        self.assertIn(self.reflection, reflections)

    def test_teacher_selector_returns_assigned_student_reflections(self):
        reflections = get_visible_reflections_for_user(self.teacher)
        self.assertIn(self.reflection, reflections)

    def test_other_student_selector_returns_nothing(self):
        reflections = get_visible_reflections_for_user(self.other_student)
        self.assertEqual(reflections.count(), 0)


# -- Journal model tests ---------------------------------------------------

class JournalModelTests(GrowthTestBase):

    def test_create_journal_entry_with_content(self):
        entry = DailyJournalEntry.objects.create(
            student=self.other_student,
            entry_date=date.today(),
            content='Wrote tests. All pass.',
        )
        self.assertEqual(entry.content, 'Wrote tests. All pass.')

    def test_duplicate_date_raises_integrity_error(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            DailyJournalEntry.objects.create(
                student=self.student,
                entry_date=self.journal_entry.entry_date,
                content='Duplicate.',
            )


# -- Journal visibility ----------------------------------------------------

class JournalVisibilityTests(GrowthTestBase):

    def test_student_sees_own_journal(self):
        self.assertTrue(can_view_journal_entry(self.student, self.journal_entry))

    def test_teacher_sees_assigned_student_journal(self):
        self.assertTrue(can_view_journal_entry(self.teacher, self.journal_entry))

    def test_other_student_cannot_see_journal(self):
        self.assertFalse(
            can_view_journal_entry(self.other_student, self.journal_entry)
        )

    def test_unrelated_teacher_cannot_see_journal(self):
        self.assertFalse(
            can_view_journal_entry(self.unrelated_teacher, self.journal_entry)
        )

    def test_admin_sees_journal(self):
        self.assertTrue(can_view_journal_entry(self.admin, self.journal_entry))

    def test_only_owner_can_edit_journal(self):
        self.assertTrue(can_edit_journal_entry(self.student, self.journal_entry))
        self.assertFalse(can_edit_journal_entry(self.teacher, self.journal_entry))
        self.assertFalse(can_edit_journal_entry(self.admin, self.journal_entry))


class JournalSelectorTests(GrowthTestBase):

    def test_student_selector_returns_own_entries(self):
        entries = get_visible_journal_entries_for_user(self.student)
        self.assertIn(self.journal_entry, entries)

    def test_teacher_selector_returns_assigned_student_entries(self):
        entries = get_visible_journal_entries_for_user(self.teacher)
        self.assertIn(self.journal_entry, entries)

    def test_other_student_selector_returns_nothing(self):
        entries = get_visible_journal_entries_for_user(self.other_student)
        self.assertEqual(entries.count(), 0)

    def test_admin_selector_returns_all(self):
        entries = get_visible_journal_entries_for_user(self.admin)
        self.assertIn(self.journal_entry, entries)


# -- Feedback permissions --------------------------------------------------

class FeedbackPermissionTests(GrowthTestBase):

    def test_teacher_can_create_feedback_on_public_goal(self):
        self.assertTrue(can_create_feedback(self.teacher, self.public_goal))

    def test_teacher_cannot_create_feedback_on_private_goal(self):
        self.assertFalse(can_create_feedback(self.teacher, self.private_goal))

    def test_teacher_can_create_feedback_on_reflection(self):
        self.assertTrue(can_create_feedback(self.teacher, self.reflection))

    def test_teacher_can_create_feedback_on_journal(self):
        self.assertTrue(can_create_feedback(self.teacher, self.journal_entry))

    def test_student_cannot_create_feedback(self):
        self.assertFalse(can_create_feedback(self.student, self.public_goal))

    def test_unrelated_teacher_cannot_create_feedback_on_goal(self):
        self.assertFalse(
            can_create_feedback(self.unrelated_teacher, self.public_goal)
        )

    def test_unrelated_teacher_cannot_create_feedback_on_journal(self):
        self.assertFalse(
            can_create_feedback(self.unrelated_teacher, self.journal_entry)
        )

    def test_admin_can_create_feedback_on_public_goal(self):
        self.assertTrue(can_create_feedback(self.admin, self.public_goal))

    def test_admin_can_create_feedback_on_reflection(self):
        self.assertTrue(can_create_feedback(self.admin, self.reflection))

    def test_admin_can_create_feedback_on_journal(self):
        self.assertTrue(can_create_feedback(self.admin, self.journal_entry))


# -- Teacher student mapping -----------------------------------------------

class TeacherStudentMappingTests(GrowthTestBase):

    def test_teacher_gets_assigned_students(self):
        students = get_students_for_teacher(self.teacher)
        self.assertIn(self.student, students)
        self.assertNotIn(self.other_student, students)

    def test_unrelated_teacher_does_not_get_student(self):
        students = get_students_for_teacher(self.unrelated_teacher)
        self.assertNotIn(self.student, students)
        self.assertIn(self.other_student, students)
