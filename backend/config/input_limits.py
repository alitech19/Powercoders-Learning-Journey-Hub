"""Shared max lengths for user-editable text (abuse prevention).

Used by goals, tasks, workflows, reflections, journal, habits, and feedback.
"""

# Titles — goal, task, workflow, step, milestone, subtask, reflection name
TITLE_MAX_LENGTH = 100

# Main description fields on goals, tasks, workflows
DESCRIPTION_MAX_LENGTH = 2000

# Workflow step blurb (shorter than workflow description)
STEP_DESCRIPTION_MAX_LENGTH = 1000

# Comments, progress updates, staff feedback
BODY_TEXT_MAX_LENGTH = 2000

# Reflection expectations / final reflection (long-form)
LONG_TEXT_MAX_LENGTH = 4000

# Reflection custom tag label
SHORT_LABEL_MAX_LENGTH = 40

# List/search query strings (?q=)
SEARCH_QUERY_MAX_LENGTH = 100

# Group Space resource label (shown on Resources tiles when post has link/file)
RESOURCE_LABEL_MAX_LENGTH = 100
