from config.input_limits import LONG_TEXT_MAX_LENGTH, SEARCH_QUERY_MAX_LENGTH, TITLE_MAX_LENGTH

CONTENT_MAX_LENGTH = LONG_TEXT_MAX_LENGTH
TAGS_MAX_LENGTH = 500
TAG_MAX_ITEM_LENGTH = 40

CONTENT_TEMPLATE = """What did I do today?

What progress did I make?

What blocked me?

What should I do next?
"""

MOOD_OPTIONS = (
    ('great', '😄', 'Great'),
    ('good', '🙂', 'Good'),
    ('okay', '😐', 'Okay'),
    ('struggling', '😟', 'Struggling'),
    ('tough', '😔', 'Tough'),
)

MOOD_CHOICES = [(value, label) for value, _emoji, label in MOOD_OPTIONS]
