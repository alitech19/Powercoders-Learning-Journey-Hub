from datetime import time
from zoneinfo import available_timezones

QUIET_HOURS_CHOICES = [('', '— Not set —')] + [
    (f'{hour:02d}:{minute:02d}', f'{hour:02d}:{minute:02d}')
    for hour in range(24)
    for minute in (0, 30)
]

_PRIORITY_TIMEZONES = (
    'Europe/Zurich',
    'UTC',
    'Europe/Berlin',
    'Europe/London',
    'Europe/Paris',
    'America/New_York',
    'America/Los_Angeles',
    'Asia/Tokyo',
)

_all_timezones = sorted(available_timezones())
_priority = [zone for zone in _PRIORITY_TIMEZONES if zone in _all_timezones]
_rest = [zone for zone in _all_timezones if zone not in set(_priority)]
TIMEZONE_CHOICES = [(zone, zone.replace('_', ' ')) for zone in _priority + _rest]


def parse_optional_quiet_hour(value):
    if not value:
        return None
    hour, minute = map(int, value.split(':'))
    return time(hour, minute)


def format_quiet_hour(value):
    if not value:
        return ''
    return value.strftime('%H:%M')
