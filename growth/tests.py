from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from cohorts.models import Cohort, Group, GroupTeacher

from .models import (
    DailyJournalEntry,
    Feedback,
    Goal,
    GoalSubgoal,
    Habit,
    HabitLog,
    WellbeingCheckIn,
    WeeklyReflection,
)
from .selectors import (
    get_students_for_teacher,
    get_visible_goals_for_user,
    get_visible_habits_for_user,
    get_visible_journal_entries_for_user,
    get_visible_reflections_for_user,
    get_visible_wellbeing_checkins_for_user,
)
from .services.habits import (
    get_current_weekly_streak,
    get_done_count_for_week,
    get_week_end,
    get_week_start,
    is_habit_week_successful,
)
from .services.permissions import (
    can_complete_habit,
    can_create_feedback,
    can_create_goal_for_student,
    can_delete_habit,
    can_edit_goal,
    can_edit_habit,
    can_edit_journal_entry,
    can_edit_wellbeing_checkin,
    can_log_habit,
    can_manage_goal_subgoals,
    can_reactivate_habit,
    can_view_goal,
    can_view_habit,
    can_view_journal_entry,
    can_view_reflection,
    can_view_wellbeing_checkin,
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
            created_by=cls.student,
            title='Private goal',
            description='My private goal description.',
            target_date=today + timedelta(days=30),
            progress_percent=10,
            visibility=Goal.Visibility.PRIVATE,
        )
        cls.public_goal = Goal.objects.create(
            student=cls.student,
            created_by=cls.student,
            title='Public goal',
            description='My public goal description.',
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
            content='What did I do today?\nStudied forms.',
        )

        cls.habit = Habit.objects.create(
            student=cls.student,
            title='Practice English 20 min',
            description='Daily English practice.',
            target_minutes=20,
            target_days_per_week=3,
        )

        cls.wellbeing = WellbeingCheckIn.objects.create(
            student=cls.student,
            check_date=today,
            energy=7,
            calmness=8,
            engagement=8,
            concentration=6,
            sleep=9,
            physical_activity=5,
            note='Good day overall.',
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


# -- Habit model tests -----------------------------------------------------

class HabitModelTests(GrowthTestBase):

    def test_create_habit(self):
        habit = Habit.objects.create(
            student=self.student,
            title='Read docs 15 min',
            target_minutes=15,
        )
        self.assertEqual(habit.status, Habit.Status.ACTIVE)
        self.assertIsNone(habit.completed_at)
        self.assertEqual(habit.target_days_per_week, 7)
        self.assertEqual(habit.completed_weekly_streak, 0)

    def test_create_habit_with_target_days(self):
        habit = Habit.objects.create(
            student=self.student,
            title='Solve exercises',
            target_days_per_week=5,
        )
        self.assertEqual(habit.target_days_per_week, 5)

    def test_mark_habit_completed(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.completed_at = timezone.now()
        self.habit.save()
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.status, Habit.Status.COMPLETED)
        self.assertIsNotNone(self.habit.completed_at)

    def test_target_days_per_week_cannot_be_zero(self):
        habit = Habit(
            student=self.student,
            title='Bad habit',
            target_days_per_week=0,
        )
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_target_days_per_week_cannot_exceed_7(self):
        habit = Habit(
            student=self.student,
            title='Bad habit',
            target_days_per_week=8,
        )
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_target_minutes_positive_if_provided(self):
        habit = Habit(
            student=self.student,
            title='Bad habit',
            target_minutes=0,
        )
        habit.full_clean()


class HabitLogTests(GrowthTestBase):

    def test_create_habit_log(self):
        log = HabitLog.objects.create(
            habit=self.habit,
            date=date.today(),
            status=HabitLog.Status.DONE,
        )
        self.assertEqual(log.status, HabitLog.Status.DONE)

    def test_duplicate_log_same_day_raises_integrity_error(self):
        HabitLog.objects.create(
            habit=self.habit,
            date=date.today(),
            status=HabitLog.Status.DONE,
        )
        with self.assertRaises(IntegrityError):
            HabitLog.objects.create(
                habit=self.habit,
                date=date.today(),
                status=HabitLog.Status.NOT_DONE,
            )

    def test_update_or_create_updates_existing_log(self):
        HabitLog.objects.create(
            habit=self.habit,
            date=date.today(),
            status=HabitLog.Status.DONE,
        )
        log, created = HabitLog.objects.update_or_create(
            habit=self.habit,
            date=date.today(),
            defaults={'status': HabitLog.Status.NOT_DONE},
        )
        self.assertFalse(created)
        self.assertEqual(log.status, HabitLog.Status.NOT_DONE)


# -- Habit visibility ------------------------------------------------------

class HabitVisibilityTests(GrowthTestBase):

    def test_student_sees_own_habit(self):
        self.assertTrue(can_view_habit(self.student, self.habit))

    def test_teacher_sees_assigned_student_habit(self):
        self.assertTrue(can_view_habit(self.teacher, self.habit))

    def test_other_student_cannot_see_habit(self):
        self.assertFalse(can_view_habit(self.other_student, self.habit))

    def test_unrelated_teacher_cannot_see_habit(self):
        self.assertFalse(can_view_habit(self.unrelated_teacher, self.habit))

    def test_admin_sees_habit(self):
        self.assertTrue(can_view_habit(self.admin, self.habit))


class HabitPermissionTests(GrowthTestBase):

    def test_owner_can_edit_active_habit(self):
        self.assertTrue(can_edit_habit(self.student, self.habit))

    def test_owner_cannot_edit_completed_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_edit_habit(self.student, self.habit))

    def test_teacher_cannot_edit_habit(self):
        self.assertFalse(can_edit_habit(self.teacher, self.habit))

    def test_owner_cannot_delete_active_habit(self):
        self.assertFalse(can_delete_habit(self.student, self.habit))

    def test_owner_can_delete_completed_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertTrue(can_delete_habit(self.student, self.habit))

    def test_teacher_cannot_delete_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_delete_habit(self.teacher, self.habit))

    def test_owner_can_log_active_habit(self):
        self.assertTrue(can_log_habit(self.student, self.habit))

    def test_owner_cannot_log_completed_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_log_habit(self.student, self.habit))

    def test_teacher_cannot_log_habit(self):
        self.assertFalse(can_log_habit(self.teacher, self.habit))

    def test_owner_can_complete_active_habit(self):
        self.assertTrue(can_complete_habit(self.student, self.habit))

    def test_owner_cannot_complete_already_completed_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_complete_habit(self.student, self.habit))

    def test_teacher_cannot_complete_habit(self):
        self.assertFalse(can_complete_habit(self.teacher, self.habit))

    def test_owner_can_reactivate_completed_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertTrue(can_reactivate_habit(self.student, self.habit))

    def test_owner_cannot_reactivate_active_habit(self):
        self.assertTrue(self.habit.is_active)
        self.assertFalse(can_reactivate_habit(self.student, self.habit))

    def test_teacher_cannot_reactivate_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_reactivate_habit(self.teacher, self.habit))

    def test_admin_cannot_reactivate_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_reactivate_habit(self.admin, self.habit))


class HabitSelectorTests(GrowthTestBase):

    def test_student_selector_returns_own_habits(self):
        habits = get_visible_habits_for_user(self.student)
        self.assertIn(self.habit, habits)

    def test_teacher_selector_returns_assigned_student_habits(self):
        habits = get_visible_habits_for_user(self.teacher)
        self.assertIn(self.habit, habits)

    def test_other_student_selector_returns_nothing(self):
        habits = get_visible_habits_for_user(self.other_student)
        self.assertEqual(habits.count(), 0)

    def test_admin_selector_returns_all(self):
        habits = get_visible_habits_for_user(self.admin)
        self.assertIn(self.habit, habits)


# -- Weekly helpers --------------------------------------------------------

class WeeklyHelperTests(TestCase):

    def test_get_week_start_monday(self):
        self.assertEqual(get_week_start(date(2026, 5, 25)), date(2026, 5, 25))

    def test_get_week_start_wednesday(self):
        self.assertEqual(get_week_start(date(2026, 5, 27)), date(2026, 5, 25))

    def test_get_week_start_sunday(self):
        self.assertEqual(get_week_start(date(2026, 5, 31)), date(2026, 5, 25))

    def test_get_week_end_monday(self):
        self.assertEqual(get_week_end(date(2026, 5, 25)), date(2026, 5, 31))

    def test_get_week_end_sunday(self):
        self.assertEqual(get_week_end(date(2026, 5, 31)), date(2026, 5, 31))


class WeeklySummaryTests(GrowthTestBase):

    def test_done_this_week_counts_only_done(self):
        ws = get_week_start(date.today())
        HabitLog.objects.create(habit=self.habit, date=ws, status=HabitLog.Status.DONE)
        HabitLog.objects.create(habit=self.habit, date=ws + timedelta(days=1), status=HabitLog.Status.NOT_DONE)
        HabitLog.objects.create(habit=self.habit, date=ws + timedelta(days=2), status=HabitLog.Status.DONE)
        self.assertEqual(get_done_count_for_week(self.habit, ws), 2)

    def test_week_successful_when_target_met(self):
        ws = get_week_start(date.today())
        for i in range(3):
            HabitLog.objects.create(
                habit=self.habit, date=ws + timedelta(days=i),
                status=HabitLog.Status.DONE,
            )
        self.assertTrue(is_habit_week_successful(self.habit, ws))

    def test_week_not_successful_when_target_not_met(self):
        ws = get_week_start(date.today())
        for i in range(2):
            HabitLog.objects.create(
                habit=self.habit, date=ws + timedelta(days=i),
                status=HabitLog.Status.DONE,
            )
        self.assertFalse(is_habit_week_successful(self.habit, ws))

    def test_not_done_logs_do_not_count_as_done(self):
        ws = get_week_start(date.today())
        for i in range(5):
            HabitLog.objects.create(
                habit=self.habit, date=ws + timedelta(days=i),
                status=HabitLog.Status.NOT_DONE,
            )
        self.assertEqual(get_done_count_for_week(self.habit, ws), 0)
        self.assertFalse(is_habit_week_successful(self.habit, ws))


# -- Streak tests ----------------------------------------------------------

class StreakTests(GrowthTestBase):

    def _log_done_days(self, habit, week_start, count):
        for i in range(count):
            HabitLog.objects.update_or_create(
                habit=habit,
                date=week_start + timedelta(days=i),
                defaults={'status': HabitLog.Status.DONE},
            )

    def test_streak_zero_when_no_logs(self):
        self.assertEqual(get_current_weekly_streak(self.habit, date.today()), 0)

    def test_streak_one_when_current_week_successful(self):
        ws = get_week_start(date.today())
        self._log_done_days(self.habit, ws, 3)
        self.assertEqual(get_current_weekly_streak(self.habit, date.today()), 1)

    def test_streak_two_consecutive_weeks(self):
        today = date.today()
        ws = get_week_start(today)
        prev_ws = ws - timedelta(days=7)
        self._log_done_days(self.habit, prev_ws, 3)
        self._log_done_days(self.habit, ws, 3)
        self.assertEqual(get_current_weekly_streak(self.habit, today), 2)

    def test_streak_breaks_on_unsuccessful_week(self):
        today = date.today()
        ws = get_week_start(today)
        prev_ws = ws - timedelta(days=7)
        two_weeks_ago = ws - timedelta(days=14)
        self._log_done_days(self.habit, two_weeks_ago, 3)
        self._log_done_days(self.habit, prev_ws, 2)  # not enough
        self._log_done_days(self.habit, ws, 3)
        self.assertEqual(get_current_weekly_streak(self.habit, today), 1)

    def test_incomplete_current_week_does_not_break_streak(self):
        """If today < Sunday and target not yet met, count from previous week."""
        today = date.today()
        ws = get_week_start(today)
        we = ws + timedelta(days=6)

        if today >= we:
            return

        prev_ws = ws - timedelta(days=7)
        self._log_done_days(self.habit, prev_ws, 3)
        HabitLog.objects.create(
            habit=self.habit, date=ws, status=HabitLog.Status.DONE,
        )
        streak = get_current_weekly_streak(self.habit, today)
        self.assertGreaterEqual(streak, 1)

    def test_streak_three_consecutive_successful_weeks(self):
        today = date.today()
        ws = get_week_start(today)
        for i in range(3):
            week = ws - timedelta(days=7 * i)
            self._log_done_days(self.habit, week, 3)
        self.assertEqual(get_current_weekly_streak(self.habit, today), 3)


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

    def test_teacher_can_create_feedback_on_habit(self):
        self.assertTrue(can_create_feedback(self.teacher, self.habit))

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

    def test_unrelated_teacher_cannot_create_feedback_on_habit(self):
        self.assertFalse(
            can_create_feedback(self.unrelated_teacher, self.habit)
        )

    def test_admin_can_create_feedback_on_public_goal(self):
        self.assertTrue(can_create_feedback(self.admin, self.public_goal))

    def test_admin_can_create_feedback_on_reflection(self):
        self.assertTrue(can_create_feedback(self.admin, self.reflection))

    def test_admin_can_create_feedback_on_journal(self):
        self.assertTrue(can_create_feedback(self.admin, self.journal_entry))

    def test_admin_can_create_feedback_on_habit(self):
        self.assertTrue(can_create_feedback(self.admin, self.habit))


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


# -- Form validation tests ------------------------------------------------

class HabitFormValidationTests(TestCase):

    def test_target_days_per_week_below_1_rejected(self):
        from .forms import HabitForm
        data = {'title': 'Test', 'target_days_per_week': 0}
        form = HabitForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('target_days_per_week', form.errors)

    def test_target_days_per_week_above_7_rejected(self):
        from .forms import HabitForm
        data = {'title': 'Test', 'target_days_per_week': 8}
        form = HabitForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('target_days_per_week', form.errors)

    def test_valid_form(self):
        from .forms import HabitForm
        data = {
            'title': 'Practice English',
            'target_days_per_week': 5,
        }
        form = HabitForm(data=data)
        self.assertTrue(form.is_valid())


# -- Habit lifecycle tests -------------------------------------------------

class HabitLifecycleTests(GrowthTestBase):

    def test_reactivation_clears_completed_at_and_streak(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.completed_at = timezone.now()
        self.habit.completed_weekly_streak = 5
        self.habit.save()

        self.habit.status = Habit.Status.ACTIVE
        self.habit.completed_at = None
        self.habit.completed_weekly_streak = 0
        self.habit.save()
        self.habit.refresh_from_db()

        self.assertEqual(self.habit.status, Habit.Status.ACTIVE)
        self.assertIsNone(self.habit.completed_at)
        self.assertEqual(self.habit.completed_weekly_streak, 0)

    def test_completed_habit_cannot_be_logged(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_log_habit(self.student, self.habit))

    def test_completed_habit_cannot_be_edited(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_edit_habit(self.student, self.habit))

    def test_active_habit_cannot_be_deleted(self):
        self.assertTrue(self.habit.is_active)
        self.assertFalse(can_delete_habit(self.student, self.habit))

    def test_completed_habit_can_be_deleted_by_owner(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertTrue(can_delete_habit(self.student, self.habit))

    def test_other_student_cannot_reactivate(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_reactivate_habit(self.other_student, self.habit))

    def test_other_student_cannot_delete_completed_habit(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.assertFalse(can_delete_habit(self.other_student, self.habit))

    def test_completion_stores_weekly_streak(self):
        ws = get_week_start(date.today())
        for i in range(3):
            HabitLog.objects.create(
                habit=self.habit, date=ws + timedelta(days=i),
                status=HabitLog.Status.DONE,
            )
        streak = get_current_weekly_streak(self.habit, date.today())
        self.habit.completed_weekly_streak = streak
        self.habit.status = Habit.Status.COMPLETED
        self.habit.completed_at = timezone.now()
        self.habit.save()
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.completed_weekly_streak, streak)
        self.assertGreaterEqual(self.habit.completed_weekly_streak, 1)


# -- Habit logging view tests ---------------------------------------------

class HabitLoggingViewTests(GrowthTestBase):

    def test_log_done_redirects_to_habit_list(self):
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/growth/habits/')

    def test_log_done_creates_today_log(self):
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        self.client.post(url)
        log = HabitLog.objects.get(habit=self.habit, date=timezone.localdate())
        self.assertEqual(log.status, HabitLog.Status.DONE)

    def test_log_not_done_updates_existing(self):
        HabitLog.objects.create(
            habit=self.habit, date=timezone.localdate(),
            status=HabitLog.Status.DONE,
        )
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/not-done/'
        self.client.post(url)
        log = HabitLog.objects.get(habit=self.habit, date=timezone.localdate())
        self.assertEqual(log.status, HabitLog.Status.NOT_DONE)

    def test_log_done_toggle_back(self):
        HabitLog.objects.create(
            habit=self.habit, date=timezone.localdate(),
            status=HabitLog.Status.NOT_DONE,
        )
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        self.client.post(url)
        log = HabitLog.objects.get(habit=self.habit, date=timezone.localdate())
        self.assertEqual(log.status, HabitLog.Status.DONE)

    def test_repeated_post_does_not_create_duplicates(self):
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        self.client.post(url)
        self.client.post(url)
        count = HabitLog.objects.filter(
            habit=self.habit, date=timezone.localdate(),
        ).count()
        self.assertEqual(count, 1)

    def test_get_request_redirects_without_logging(self):
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            HabitLog.objects.filter(
                habit=self.habit, date=timezone.localdate(),
            ).exists()
        )

    def test_teacher_cannot_log(self):
        self.client.login(email='teacher@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_completed_habit_cannot_be_logged(self):
        self.habit.status = Habit.Status.COMPLETED
        self.habit.save()
        self.client.login(email='student@test.com', password='pass')
        url = f'/growth/habits/{self.habit.pk}/log-today/done/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)


# -- Wellbeing model tests -------------------------------------------------

class WellbeingModelTests(GrowthTestBase):

    def test_create_wellbeing_checkin(self):
        checkin = WellbeingCheckIn.objects.create(
            student=self.other_student,
            check_date=date.today(),
            energy=5, calmness=5, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        self.assertEqual(checkin.energy, 5)

    def test_scale_below_1_raises_validation_error(self):
        checkin = WellbeingCheckIn(
            student=self.other_student,
            check_date=date.today(),
            energy=0, calmness=5, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        with self.assertRaises(ValidationError):
            checkin.full_clean()

    def test_calmness_below_1_raises_validation_error(self):
        checkin = WellbeingCheckIn(
            student=self.other_student,
            check_date=date.today(),
            energy=5, calmness=0, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        with self.assertRaises(ValidationError):
            checkin.full_clean()

    def test_calmness_above_10_raises_validation_error(self):
        checkin = WellbeingCheckIn(
            student=self.other_student,
            check_date=date.today(),
            energy=5, calmness=11, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        with self.assertRaises(ValidationError):
            checkin.full_clean()

    def test_scale_above_10_raises_validation_error(self):
        checkin = WellbeingCheckIn(
            student=self.other_student,
            check_date=date.today(),
            energy=11, calmness=5, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        with self.assertRaises(ValidationError):
            checkin.full_clean()

    def test_duplicate_checkin_same_student_date(self):
        with self.assertRaises(IntegrityError):
            WellbeingCheckIn.objects.create(
                student=self.student,
                check_date=self.wellbeing.check_date,
                energy=5, calmness=5, engagement=5,
                concentration=5, sleep=5, physical_activity=5,
            )

    def test_wellbeing_average_uses_calmness_directly(self):
        checkin = WellbeingCheckIn(
            student=self.other_student,
            check_date=date.today(),
            energy=8, calmness=7, engagement=6,
            concentration=8, sleep=7, physical_activity=6,
        )
        expected = round((8 + 7 + 6 + 8 + 7 + 6) / 6, 1)
        self.assertEqual(checkin.wellbeing_average, expected)
        self.assertEqual(checkin.wellbeing_average, 7.0)

    def test_wellbeing_average_does_not_invert_calmness(self):
        checkin = WellbeingCheckIn(
            student=self.other_student,
            check_date=date.today(),
            energy=5, calmness=5, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        self.assertEqual(checkin.wellbeing_average, 5.0)

    def test_higher_calmness_raises_average(self):
        low_calm = WellbeingCheckIn(
            student=self.other_student,
            check_date=date(2026, 1, 1),
            energy=5, calmness=1, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        high_calm = WellbeingCheckIn(
            student=self.other_student,
            check_date=date(2026, 1, 2),
            energy=5, calmness=10, engagement=5,
            concentration=5, sleep=5, physical_activity=5,
        )
        self.assertGreater(high_calm.wellbeing_average, low_calm.wellbeing_average)


# -- Wellbeing visibility --------------------------------------------------

class WellbeingVisibilityTests(GrowthTestBase):

    def test_student_sees_own_checkin(self):
        self.assertTrue(can_view_wellbeing_checkin(self.student, self.wellbeing))

    def test_teacher_sees_assigned_student_checkin(self):
        self.assertTrue(can_view_wellbeing_checkin(self.teacher, self.wellbeing))

    def test_other_student_cannot_see_checkin(self):
        self.assertFalse(can_view_wellbeing_checkin(self.other_student, self.wellbeing))

    def test_unrelated_teacher_cannot_see_checkin(self):
        self.assertFalse(can_view_wellbeing_checkin(self.unrelated_teacher, self.wellbeing))

    def test_admin_sees_checkin(self):
        self.assertTrue(can_view_wellbeing_checkin(self.admin, self.wellbeing))

    def test_only_owner_can_edit_checkin(self):
        self.assertTrue(can_edit_wellbeing_checkin(self.student, self.wellbeing))
        self.assertFalse(can_edit_wellbeing_checkin(self.teacher, self.wellbeing))
        self.assertFalse(can_edit_wellbeing_checkin(self.admin, self.wellbeing))


class WellbeingSelectorTests(GrowthTestBase):

    def test_student_selector_returns_own_checkins(self):
        checkins = get_visible_wellbeing_checkins_for_user(self.student)
        self.assertIn(self.wellbeing, checkins)

    def test_teacher_selector_returns_assigned_student_checkins(self):
        checkins = get_visible_wellbeing_checkins_for_user(self.teacher)
        self.assertIn(self.wellbeing, checkins)

    def test_other_student_selector_returns_nothing(self):
        checkins = get_visible_wellbeing_checkins_for_user(self.other_student)
        self.assertEqual(checkins.count(), 0)

    def test_admin_selector_returns_all(self):
        checkins = get_visible_wellbeing_checkins_for_user(self.admin)
        self.assertIn(self.wellbeing, checkins)


# -- Wellbeing feedback permissions ----------------------------------------

class WellbeingFeedbackPermissionTests(GrowthTestBase):

    def test_teacher_can_create_feedback_on_wellbeing(self):
        self.assertTrue(can_create_feedback(self.teacher, self.wellbeing))

    def test_student_cannot_create_feedback_on_wellbeing(self):
        self.assertFalse(can_create_feedback(self.student, self.wellbeing))

    def test_unrelated_teacher_cannot_create_feedback_on_wellbeing(self):
        self.assertFalse(can_create_feedback(self.unrelated_teacher, self.wellbeing))

    def test_admin_can_create_feedback_on_wellbeing(self):
        self.assertTrue(can_create_feedback(self.admin, self.wellbeing))


# -- Wellbeing form validation tests ---------------------------------------

class WellbeingFormValidationTests(TestCase):

    def test_valid_form(self):
        from .forms import WellbeingCheckInForm
        data = {
            'check_date': '2026-05-26',
            'energy': 7, 'calmness': 8, 'engagement': 8,
            'concentration': 6, 'sleep': 9, 'physical_activity': 5,
        }
        form = WellbeingCheckInForm(data=data)
        self.assertTrue(form.is_valid())

    def test_missing_required_field_rejected(self):
        from .forms import WellbeingCheckInForm
        data = {
            'check_date': '2026-05-26',
            'energy': 7, 'calmness': 8, 'engagement': 8,
            'concentration': 6, 'sleep': 9,
        }
        form = WellbeingCheckInForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('physical_activity', form.errors)


# -- Wellbeing view tests --------------------------------------------------

class WellbeingViewTests(GrowthTestBase):

    def test_student_can_create_checkin(self):
        self.client.login(email='student@test.com', password='pass')
        data = {
            'check_date': '2026-06-01',
            'energy': 7, 'calmness': 8, 'engagement': 8,
            'concentration': 6, 'sleep': 9, 'physical_activity': 5,
        }
        response = self.client.post('/growth/wellbeing/new/', data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            WellbeingCheckIn.objects.filter(
                student=self.student, check_date=date(2026, 6, 1),
            ).exists()
        )

    def test_student_can_view_own_list(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/wellbeing/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wellbeing')

    def test_student_can_view_own_detail(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get(f'/growth/wellbeing/{self.wellbeing.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_student_can_edit_own_checkin(self):
        self.client.login(email='student@test.com', password='pass')
        data = {
            'check_date': self.wellbeing.check_date.isoformat(),
            'energy': 8, 'calmness': 9, 'engagement': 9,
            'concentration': 7, 'sleep': 10, 'physical_activity': 6,
        }
        response = self.client.post(
            f'/growth/wellbeing/{self.wellbeing.pk}/edit/', data,
        )
        self.assertEqual(response.status_code, 302)
        self.wellbeing.refresh_from_db()
        self.assertEqual(self.wellbeing.energy, 8)

    def test_other_student_cannot_view_checkin(self):
        self.client.login(email='other@test.com', password='pass')
        response = self.client.get(f'/growth/wellbeing/{self.wellbeing.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_teacher_can_view_assigned_checkin(self):
        self.client.login(email='teacher@test.com', password='pass')
        response = self.client.get(f'/growth/wellbeing/{self.wellbeing.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_unrelated_teacher_cannot_view_checkin(self):
        self.client.login(email='unrelated@test.com', password='pass')
        response = self.client.get(f'/growth/wellbeing/{self.wellbeing.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_admin_can_view_checkin(self):
        self.client.login(email='admin@test.com', password='pass')
        response = self.client.get(f'/growth/wellbeing/{self.wellbeing.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_wellbeing_list_shows_results(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/wellbeing/')
        self.assertContains(response, self.wellbeing.energy)

    def test_form_shows_scale_explanations(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/wellbeing/new/')
        self.assertContains(response, '1 = exhausted, 10 = energetic')
        self.assertContains(response, '1 = very stressed, 10 = very calm')
        self.assertContains(response, '1 = disengaged, 10 = highly engaged')
        self.assertContains(response, '1 = very distracted, 10 = highly focused')
        self.assertContains(response, '1 = very poor sleep, 10 = excellent sleep')
        self.assertContains(response, '1 = no movement, 10 = very active')

    def test_form_shows_calmness_not_stress(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/wellbeing/new/')
        self.assertContains(response, 'Calmness')
        self.assertNotContains(response, 'Stress')

    def test_list_shows_calmness_column(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/wellbeing/')
        self.assertContains(response, 'Calmness')
        self.assertNotContains(response, 'Stress')

    def test_detail_shows_calmness_scale(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get(f'/growth/wellbeing/{self.wellbeing.pk}/')
        self.assertContains(response, 'Calmness')
        self.assertContains(response, '1 = very stressed, 10 = very calm')

    def test_navigation_includes_wellbeing(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/wellbeing/')
        content = response.content.decode()
        habits_pos = content.find('Habits')
        wellbeing_pos = content.find('<strong>Wellbeing</strong>')
        goals_pos = content.find('Goals')
        self.assertGreater(wellbeing_pos, habits_pos)
        self.assertGreater(goals_pos, wellbeing_pos)


# -- Goals naming tests ----------------------------------------------------

class GoalNamingTests(GrowthTestBase):

    def test_navigation_shows_goals_not_smart_goals(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/goals/')
        self.assertContains(response, '<strong>Goals</strong>')
        self.assertNotContains(response, 'SMART Goals')

    def test_goal_list_heading_says_goals(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/goals/')
        self.assertContains(response, '<h2>Goals</h2>')
        self.assertNotContains(response, 'SMART')

    def test_goal_form_heading_says_new_goal(self):
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get('/growth/goals/new/')
        self.assertContains(response, 'New goal')
        self.assertNotContains(response, 'SMART goal')


# -- Teacher goal creation tests -------------------------------------------

class TeacherGoalCreationTests(GrowthTestBase):

    def test_teacher_can_create_goal_for_assigned_student(self):
        self.client.login(email='teacher@test.com', password='pass')
        data = {
            'student': self.student.pk,
            'title': 'Teacher-created goal',
            'description': 'Learn Django forms.',
            'target_date': (date.today() + timedelta(days=14)).isoformat(),
            'progress_percent': 0,
        }
        response = self.client.post('/growth/goals/new/', data)
        self.assertEqual(response.status_code, 302)
        goal = Goal.objects.get(title='Teacher-created goal')
        self.assertEqual(goal.student, self.student)
        self.assertEqual(goal.created_by, self.teacher)
        self.assertEqual(goal.visibility, Goal.Visibility.PUBLIC)

    def test_teacher_cannot_create_goal_for_unrelated_student(self):
        self.client.login(email='teacher@test.com', password='pass')
        data = {
            'student': self.other_student.pk,
            'title': 'Should not work',
            'description': 'Desc.',
            'target_date': (date.today() + timedelta(days=14)).isoformat(),
            'progress_percent': 0,
        }
        response = self.client.post('/growth/goals/new/', data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Goal.objects.filter(title='Should not work').exists())

    def test_teacher_created_goal_visible_to_student(self):
        goal = Goal.objects.create(
            student=self.student,
            created_by=self.teacher,
            title='Teacher goal',
            description='Desc.',
            target_date=date.today() + timedelta(days=14),
            visibility=Goal.Visibility.PUBLIC,
        )
        self.assertTrue(can_view_goal(self.student, goal))

    def test_teacher_created_goal_defaults_to_public(self):
        self.client.login(email='teacher@test.com', password='pass')
        data = {
            'student': self.student.pk,
            'title': 'Public by default',
            'description': 'Desc.',
            'target_date': (date.today() + timedelta(days=14)).isoformat(),
            'progress_percent': 0,
        }
        self.client.post('/growth/goals/new/', data)
        goal = Goal.objects.get(title='Public by default')
        self.assertEqual(goal.visibility, Goal.Visibility.PUBLIC)

    def test_other_student_cannot_see_teacher_created_goal(self):
        goal = Goal.objects.create(
            student=self.student,
            created_by=self.teacher,
            title='Teacher goal',
            description='Desc.',
            target_date=date.today() + timedelta(days=14),
            visibility=Goal.Visibility.PUBLIC,
        )
        self.assertFalse(can_view_goal(self.other_student, goal))

    def test_can_create_goal_for_student_permission(self):
        self.assertTrue(can_create_goal_for_student(self.teacher, self.student))
        self.assertFalse(can_create_goal_for_student(self.teacher, self.other_student))
        self.assertTrue(can_create_goal_for_student(self.student, self.student))
        self.assertFalse(can_create_goal_for_student(self.student, self.other_student))

    def test_teacher_can_edit_goal_they_created(self):
        goal = Goal.objects.create(
            student=self.student,
            created_by=self.teacher,
            title='Teacher goal',
            description='Desc.',
            target_date=date.today() + timedelta(days=14),
            visibility=Goal.Visibility.PUBLIC,
        )
        self.assertTrue(can_edit_goal(self.teacher, goal))

    def test_teacher_cannot_edit_student_created_goal(self):
        self.assertFalse(can_edit_goal(self.teacher, self.public_goal))

    def test_unrelated_teacher_cannot_see_goal(self):
        goal = Goal.objects.create(
            student=self.student,
            created_by=self.teacher,
            title='Teacher goal',
            description='Desc.',
            target_date=date.today() + timedelta(days=14),
            visibility=Goal.Visibility.PUBLIC,
        )
        self.assertFalse(can_view_goal(self.unrelated_teacher, goal))


# -- Subgoal tests ---------------------------------------------------------

class SubgoalModelTests(GrowthTestBase):

    def test_create_subgoal(self):
        sg = GoalSubgoal.objects.create(
            goal=self.public_goal,
            title='Step 1',
            created_by=self.student,
        )
        self.assertEqual(sg.status, GoalSubgoal.Status.PENDING)
        self.assertIsNone(sg.completed_at)

    def test_subgoal_progress_no_subgoals(self):
        self.assertEqual(
            self.public_goal.subgoal_progress_percent,
            self.public_goal.progress_percent,
        )

    def test_subgoal_progress_half_done(self):
        for i in range(4):
            GoalSubgoal.objects.create(
                goal=self.public_goal,
                title=f'Step {i+1}',
                status=GoalSubgoal.Status.DONE if i < 2 else GoalSubgoal.Status.PENDING,
                created_by=self.student,
            )
        self.assertEqual(self.public_goal.subgoal_progress_percent, 50)

    def test_subgoal_progress_all_done(self):
        for i in range(3):
            GoalSubgoal.objects.create(
                goal=self.public_goal,
                title=f'Step {i+1}',
                status=GoalSubgoal.Status.DONE,
                created_by=self.student,
            )
        self.assertEqual(self.public_goal.subgoal_progress_percent, 100)


class SubgoalPermissionTests(GrowthTestBase):

    def test_student_can_manage_subgoals_of_own_goal(self):
        self.assertTrue(can_manage_goal_subgoals(self.student, self.public_goal))

    def test_teacher_can_manage_subgoals_of_goal_they_created(self):
        goal = Goal.objects.create(
            student=self.student,
            created_by=self.teacher,
            title='Teacher goal',
            description='Desc.',
            target_date=date.today() + timedelta(days=14),
            visibility=Goal.Visibility.PUBLIC,
        )
        self.assertTrue(can_manage_goal_subgoals(self.teacher, goal))

    def test_teacher_cannot_manage_subgoals_of_student_goal(self):
        self.assertFalse(can_manage_goal_subgoals(self.teacher, self.public_goal))

    def test_teacher_cannot_manage_subgoals_of_private_goal(self):
        self.assertFalse(can_manage_goal_subgoals(self.teacher, self.private_goal))

    def test_other_student_cannot_manage_subgoals(self):
        self.assertFalse(can_manage_goal_subgoals(self.other_student, self.public_goal))

    def test_unrelated_teacher_cannot_manage_subgoals(self):
        self.assertFalse(can_manage_goal_subgoals(self.unrelated_teacher, self.public_goal))


class SubgoalViewTests(GrowthTestBase):

    def test_student_can_add_subgoal(self):
        self.client.login(email='student@test.com', password='pass')
        data = {'title': 'My subgoal', 'description': '', 'order': 0}
        response = self.client.post(
            f'/growth/goals/{self.public_goal.pk}/subgoals/new/', data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            GoalSubgoal.objects.filter(
                goal=self.public_goal, title='My subgoal',
            ).exists()
        )

    def test_toggle_subgoal_done(self):
        sg = GoalSubgoal.objects.create(
            goal=self.public_goal, title='Toggle me',
            created_by=self.student,
        )
        self.client.login(email='student@test.com', password='pass')
        response = self.client.post(
            f'/growth/goals/{self.public_goal.pk}/subgoals/{sg.pk}/toggle/',
        )
        self.assertEqual(response.status_code, 302)
        sg.refresh_from_db()
        self.assertEqual(sg.status, GoalSubgoal.Status.DONE)
        self.assertIsNotNone(sg.completed_at)

    def test_toggle_done_subgoal_back_to_pending(self):
        sg = GoalSubgoal.objects.create(
            goal=self.public_goal, title='Toggle back',
            status=GoalSubgoal.Status.DONE,
            completed_at=timezone.now(),
            created_by=self.student,
        )
        self.client.login(email='student@test.com', password='pass')
        self.client.post(
            f'/growth/goals/{self.public_goal.pk}/subgoals/{sg.pk}/toggle/',
        )
        sg.refresh_from_db()
        self.assertEqual(sg.status, GoalSubgoal.Status.PENDING)
        self.assertIsNone(sg.completed_at)

    def test_unauthorized_user_cannot_add_subgoal(self):
        self.client.login(email='other@test.com', password='pass')
        data = {'title': 'Blocked', 'description': '', 'order': 0}
        response = self.client.post(
            f'/growth/goals/{self.public_goal.pk}/subgoals/new/', data,
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(GoalSubgoal.objects.filter(title='Blocked').exists())

    def test_goal_detail_shows_subgoals(self):
        GoalSubgoal.objects.create(
            goal=self.public_goal, title='Visible subgoal',
            created_by=self.student,
        )
        self.client.login(email='student@test.com', password='pass')
        response = self.client.get(f'/growth/goals/{self.public_goal.pk}/')
        self.assertContains(response, 'Visible subgoal')
        self.assertContains(response, 'Add subgoal')
