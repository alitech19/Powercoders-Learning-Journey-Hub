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

# Input limits — enforced in forms and list search (abuse prevention).
TITLE_MAX_LENGTH = 100
CUSTOM_LABEL_MAX_LENGTH = 40
EXPECTATIONS_MAX_LENGTH = 4000
FINAL_REFLECTION_MAX_LENGTH = 4000
SEARCH_QUERY_MAX_LENGTH = 100
