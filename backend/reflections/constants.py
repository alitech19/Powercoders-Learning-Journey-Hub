# Input limits — re-export shared config for app-local imports.
from config.input_limits import (  # noqa: F401
    LONG_TEXT_MAX_LENGTH as EXPECTATIONS_MAX_LENGTH,
    LONG_TEXT_MAX_LENGTH as FINAL_REFLECTION_MAX_LENGTH,
    SEARCH_QUERY_MAX_LENGTH,
    SHORT_LABEL_MAX_LENGTH as CUSTOM_LABEL_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)

EXPECTATIONS_TEMPLATE = """What do I expect to learn or achieve?

What is my plan for this period or project?
"""

FINAL_REFLECTION_TEMPLATE = """What went well?

What was challenging?

What will I focus on next?

Anything else?
"""

WELLBEING_DIMENSIONS = (
    ('energy', 'Energy', 'How energetic do you feel?'),
    ('calmness', 'Calmness', 'How calm do you feel?'),
    ('engagement', 'Engagement', 'How engaged do you feel?'),
    ('concentration', 'Concentration', 'How focused do you feel?'),
    ('sleep', 'Sleep', 'How well did you sleep?'),
    ('physical_activity', 'Physical activity', 'How active do you feel?'),
)

MOOD_OPTIONS = (
    ('great', '😄', 'Great'),
    ('good', '🙂', 'Good'),
    ('okay', '😐', 'Okay'),
    ('struggling', '😟', 'Struggling'),
    ('tough', '😔', 'Tough'),
)

TAG_WEEKLY = 'weekly'
TAG_PROJECT = 'project'
TAG_CUSTOM = 'custom'
TAG_CHOICES = (
    (TAG_WEEKLY, 'Weekly'),
    (TAG_PROJECT, 'Project'),
    (TAG_CUSTOM, 'Custom'),
)
