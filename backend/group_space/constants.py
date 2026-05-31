"""Group Space limits and file policy."""

GROUP_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_GROUP_FILE_EXTENSIONS = frozenset({
    '.pdf', '.doc', '.docx', '.txt',
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
})

SNAPSHOT_KINDS = frozenset({'journal', 'habit', 'goal', 'task'})

# Share panel button order — matches Goals → Tasks → Journal → Habits in config/nav.py
SHARE_KIND_PANEL: tuple[tuple[str, str], ...] = (
    ('goal', 'Goal'),
    ('task', 'Task'),
    ('journal', 'Journal'),
    ('habit', 'Habit'),
)
