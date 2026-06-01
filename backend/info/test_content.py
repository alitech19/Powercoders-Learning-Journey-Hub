from django.test import TestCase

from info.content import load_topic, parse_topic_markdown, visible_sections
from test_utils.users import make_admin, make_student


SAMPLE_MD = """# Intro line

## First {#first}

Content one.

## Admin only

<!-- role: admin -->

Secret admin text.

## Tables

| A | B |
|---|---|
| 1 | 2 |
"""


class InfoContentTests(TestCase):
    def test_parse_sections_and_admin_gate(self):
        topic = parse_topic_markdown('tasks', SAMPLE_MD)
        self.assertGreaterEqual(len(topic.sections), 3)
        first = next(s for s in topic.sections if s.section_id == 'first')
        self.assertIn('Content one', first.html)
        admin_section = next(s for s in topic.sections if s.section_id == 'admin-only')
        self.assertTrue(admin_section.admin_only)
        tables = next(s for s in topic.sections if s.section_id == 'tables')
        self.assertIn('<table', tables.html.lower())

    def test_visible_sections_hides_admin_from_student(self):
        topic = parse_topic_markdown('tasks', SAMPLE_MD)
        student = make_student('s@example.com')
        admin = make_admin('a@example.com')
        student_sections = visible_sections(topic, student)
        admin_sections = visible_sections(topic, admin)
        self.assertLess(len(student_sections), len(admin_sections))

    def test_load_topic_tasks_file_exists(self):
        topic = load_topic('tasks')
        self.assertEqual(topic.app_slug, 'tasks')
        self.assertTrue(len(topic.sections) > 0)
