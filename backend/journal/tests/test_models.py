from django.test import TestCase

from journal.models import JournalEntry
from test_utils.journal import make_journal_entry
from test_utils.users import make_student


class JournalEntryModelTests(TestCase):
    def setUp(self):
        self.student = make_student('s@example.com')

    def test_str_includes_date(self):
        entry = make_journal_entry(self.student, title='Day 1')
        self.assertIn('Day 1', str(entry))

    def test_get_tags_list(self):
        entry = make_journal_entry(self.student, tags='focus, learning')
        self.assertEqual(entry.get_tags_list(), ['focus', 'learning'])

    def test_word_count_and_excerpt(self):
        entry = make_journal_entry(
            self.student,
            content='one two three four five',
        )
        self.assertEqual(entry.word_count, 5)
        long_text = 'word ' * 50
        entry.content = long_text.strip()
        self.assertTrue(len(entry.excerpt) <= 165)
        self.assertTrue(entry.excerpt.endswith('…') or len(entry.content) <= 160)

    def test_mood_emoji(self):
        entry = make_journal_entry(self.student, mood=JournalEntry.Mood.GOOD)
        self.assertEqual(entry.mood_emoji, '🙂')
