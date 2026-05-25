from datetime import date, timedelta

from django.test import TestCase

from accounts.models import User
from cohorts.models import Cohort, Group, GroupTeacher

from .models import Feedback, Goal, WeeklyReflection
from .selectors import (
    get_students_for_teacher,
    get_visible_goals_for_user,
    get_visible_reflections_for_user,
)
from .services.permissions import (
    can_create_feedback,
    can_view_goal,
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
            specific='s', measurable='m', achievable='a',
            relevant='r', time_bound=today + timedelta(days=30),
            visibility=Goal.Visibility.PRIVATE,
        )
        cls.public_goal = Goal.objects.create(
            student=cls.student,
            title='Public goal',
            specific='s', measurable='m', achievable='a',
            relevant='r', time_bound=today + timedelta(days=30),
            visibility=Goal.Visibility.PUBLIC,
        )

        cls.reflection = WeeklyReflection(
            student=cls.student,
            week_start=today - timedelta(days=today.weekday()),
            week_end=today - timedelta(days=today.weekday()) + timedelta(days=6),
            more_of='Code more',
        )
        cls.reflection.save()


# ── Goal visibility ──────────────────────────────────────────────────

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


# ── Reflection visibility ────────────────────────────────────────────

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


# ── Feedback permissions ─────────────────────────────────────────────

class FeedbackPermissionTests(GrowthTestBase):

    def test_teacher_can_create_feedback_on_public_goal(self):
        self.assertTrue(can_create_feedback(self.teacher, self.public_goal))

    def test_teacher_cannot_create_feedback_on_private_goal(self):
        self.assertFalse(can_create_feedback(self.teacher, self.private_goal))

    def test_teacher_can_create_feedback_on_reflection(self):
        self.assertTrue(can_create_feedback(self.teacher, self.reflection))

    def test_student_cannot_create_feedback(self):
        self.assertFalse(can_create_feedback(self.student, self.public_goal))

    def test_unrelated_teacher_cannot_create_feedback_on_goal(self):
        self.assertFalse(
            can_create_feedback(self.unrelated_teacher, self.public_goal)
        )

    def test_admin_can_create_feedback_on_public_goal(self):
        self.assertTrue(can_create_feedback(self.admin, self.public_goal))

    def test_admin_can_create_feedback_on_reflection(self):
        self.assertTrue(can_create_feedback(self.admin, self.reflection))


# ── Teacher student mapping ──────────────────────────────────────────

class TeacherStudentMappingTests(GrowthTestBase):

    def test_teacher_gets_assigned_students(self):
        students = get_students_for_teacher(self.teacher)
        self.assertIn(self.student, students)
        self.assertNotIn(self.other_student, students)

    def test_unrelated_teacher_does_not_get_student(self):
        students = get_students_for_teacher(self.unrelated_teacher)
        self.assertNotIn(self.student, students)
        self.assertIn(self.other_student, students)
