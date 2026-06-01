"""
Test settings — use via DJANGO_SETTINGS_MODULE=config.settings_test.

Uses a real PostgreSQL database (same POSTGRES_* env as dev). Does not require Redis:
sessions and cache use in-memory / DB backends so tests run with only Postgres available.
CI still uses config.settings + Redis to match production wiring.
"""

from .settings import *  # noqa: F403

DEBUG = False

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

AXES_ENABLED = False

# Quieter test output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {'class': 'logging.NullHandler'},
    },
    'root': {
        'handlers': ['null'],
    },
}
