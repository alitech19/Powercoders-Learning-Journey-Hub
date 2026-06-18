from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import TestCase

from goals.models import Goal, GoalEnrollment
from goals.services import create_goals_bulk
from resources.entity_links import (
    apply_entity_resource_container,
    can_view_container_via_entity_link,
    resolve_resource_container_for_entity,
)
from resources.models import ResourceContainer
from resources.permissions import can_view_container
from test_utils.cohorts import assign_teacher, make_cohort, make_group
from test_utils.resources import make_thematic_container, system_group_container
from test_utils.users import make_student, make_teacher
from workflows.models import Workflow
from workflows.services import create_workflow


class EntityResourceContainerTests(TestCase):
    def setUp(self):
        self.cohort = make_cohort()
        self.group = make_group(self.cohort)
        self.teacher = make_teacher('teacher@example.com')
        assign_teacher(self.group, self.teacher)
        self.student = make_student('student@example.com', group=self.group)
        other_cohort = make_cohort(name='Other cohort')
        self.other_student = make_student('other@example.com', group=make_group(other_cohort))
        self.existing_theme = make_thematic_container(self.group, self.teacher, title='Week 1 links')

    def test_resolve_create_thematic(self):
        container = resolve_resource_container_for_entity(
            user=self.teacher,
            post={
                'resource_container_mode': 'create',
                'resource_container_new_title': 'Materials: Onboarding',
            },
            default_title='Materials: Onboarding',
            assignee_group=self.group,
        )
        self.assertEqual(container.title, 'Materials: Onboarding')
        self.assertEqual(container.container_type, ResourceContainer.ContainerType.THEMATIC)
        self.assertEqual(container.group_id, self.group.pk)

    def test_resolve_rejects_system_container(self):
        system = system_group_container(self.group, created_by=self.teacher)
        with self.assertRaises(ValidationError):
            resolve_resource_container_for_entity(
                user=self.teacher,
                post={
                    'resource_container_mode': 'existing',
                    'resource_container_id': str(system.pk),
                },
                default_title='Materials: X',
                assignee_group=self.group,
            )

    def test_workflow_create_links_new_theme(self):
        workflow = create_workflow(
            user=self.teacher,
            post={
                'title': 'Onboarding flow',
                'description': '',
                'visibility': 'public',
                'progress_mode': 'shared',
                'assignee_type': 'group',
                'assignee_target_id': str(self.group.pk),
                'step_title_1': 'Step one',
                'resource_container_mode': 'create',
                'resource_container_new_title': 'Materials: Onboarding flow',
            },
        )
        workflow.refresh_from_db()
        self.assertIsNotNone(workflow.resource_container_id)
        self.assertEqual(workflow.resource_container.title, 'Materials: Onboarding flow')

    def test_cohort_assignee_can_view_linked_theme_without_group(self):
        container = ResourceContainer.objects.create(
            container_type=ResourceContainer.ContainerType.THEMATIC,
            title='Cohort materials',
            group=None,
            created_by=self.teacher,
        )
        workflow = Workflow.objects.create(
            title='Cohort flow',
            progress_mode=Workflow.ProgressMode.SHARED,
            assignee_type=Workflow.AssigneeType.COHORT,
            assignee_cohort=self.cohort,
            created_by=self.teacher,
            resource_container=container,
        )
        self.assertTrue(can_view_container_via_entity_link(self.student, container))
        self.assertTrue(can_view_container(self.student, container))
        self.assertFalse(can_view_container(self.other_student, container))

    def test_apply_clears_link_when_none_selected(self):
        goal = Goal.objects.create(
            title='G',
            created_by=self.teacher,
            resource_container=self.existing_theme,
        )
        GoalEnrollment.objects.create(goal=goal, student=self.student)
        apply_entity_resource_container(
            entity=goal,
            user=self.teacher,
            post={'resource_container_mode': 'none'},
            assignee_group=self.group,
        )
        goal.refresh_from_db()
        self.assertIsNone(goal.resource_container_id)

    def test_link_existing_theme_on_goal_create(self):
        post = QueryDict(mutable=True)
        post.update({
            'title': 'Learn Python',
            'assignee_type': 'group',
            'assignee_target_id': str(self.group.pk),
            'visibility': 'shared',
            'resource_container_mode': 'existing',
            'resource_container_id': str(self.existing_theme.pk),
        })
        post.setlist('student_ids', [str(self.student.pk)])
        goal = create_goals_bulk(user=self.teacher, post=post)
        goal.refresh_from_db()
        self.assertEqual(goal.resource_container_id, self.existing_theme.pk)
