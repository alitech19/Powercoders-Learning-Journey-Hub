"""
Django settings for PowerHUB (integration branch — infrastructure skeleton).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / '.env')

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dev-only-change-me-before-production',
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    # OTP / 2FA (login wired in Phase B)
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    # Brute-force protection
    'axes',
    'accounts',
    'cohorts',
    'workflows',
    'feedback',
    'goals',
    'tasks',
    'reflections',
    'journal',
    'habits',
    'group_space.apps.GroupSpaceConfig',
    'resources.apps.ResourcesConfig',
    'dashboard.apps.DashboardConfig',
    'info.apps.InfoConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'axes.middleware.AxesMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.AuditLoggingMiddleware',
    'accounts.middleware.PrivacyPolicyMiddleware',
    'accounts.middleware.ForcePasswordChangeMiddleware',
    'accounts.middleware.Require2FAMiddleware',
    'accounts.middleware.WelcomeMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [PROJECT_ROOT / 'frontend' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.dev_login_panel',
                'accounts.context_processors.unread_notifications',
                'config.context_processors.integrated_nav',
                'config.context_processors.page_meta',
                'info.context_processors.page_help',
                'config.context_processors.input_limits',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


def _database_config() -> dict:
    """POSTGRES_* for Docker; DATABASE_URL for Render/Heroku (Internal URL)."""
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': (parsed.path or '/').lstrip('/'),
            'USER': parsed.username or '',
            'PASSWORD': parsed.password or '',
            'HOST': parsed.hostname or 'localhost',
            'PORT': str(parsed.port or 5432),
        }
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'powerhub'),
        'USER': os.environ.get('POSTGRES_USER', 'powerhub'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'powerhub'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }


DATABASES = {'default': _database_config()}

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Zurich'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [PROJECT_ROOT / 'frontend' / 'static']
STATIC_ROOT = PROJECT_ROOT / 'frontend' / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = 'dashboard:dashboard'
LOGOUT_REDIRECT_URL = 'two_factor:login'

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
# Render free/small instances OOM with default prefork (~CPU count). Override via env.
CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', '4'))

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'weekly-db-backup': {
        'task': 'config.tasks.backup_database',
        # Every Sunday at 02:00 Europe/Zurich
        'schedule': crontab(hour=2, minute=0, day_of_week='sunday'),
    },
}

# --- Database backups ---
# S3-compatible storage (AWS S3 or Backblaze B2).
# Leave all blank to disable — the task will log a warning and skip safely.
BACKUP_S3_BUCKET = os.environ.get('BACKUP_S3_BUCKET', '')
BACKUP_S3_ACCESS_KEY = os.environ.get('BACKUP_S3_ACCESS_KEY', '')
BACKUP_S3_SECRET_KEY = os.environ.get('BACKUP_S3_SECRET_KEY', '')
BACKUP_S3_ENDPOINT_URL = os.environ.get('BACKUP_S3_ENDPOINT_URL', '')  # Backblaze B2: https://s3.us-west-004.backblazeb2.com
BACKUP_S3_REGION = os.environ.get('BACKUP_S3_REGION', 'us-east-1')
BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@powercoders.org')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000').rstrip('/')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '').strip()

# SMTP credentials — used when EMAIL_BACKEND is set to smtp (production)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --- Security (auth Phase A–E) ---

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'
AXES_USERNAME_FORM_FIELD = 'auth-username'
AXES_USERNAME_CALLABLE = 'accounts.axes_utils.get_axes_username'
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "https://cdn.tailwindcss.com",
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "https://fonts.googleapis.com",
)
CSP_IMG_SRC = ("'self'", "data:", "blob:")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

# Production hardening (auto-enabled when DEBUG=False — staging/Render).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in (
        'true',
        '1',
        'yes',
    )
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = False  # readable by JS for HTMX CSRF tokens
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    if SECRET_KEY.startswith('django-insecure-'):
        raise RuntimeError(
            'SECRET_KEY is still set to the insecure development default. '
            'Set a strong, random SECRET_KEY environment variable before '
            'running with DEBUG=False.'
        )

# --- Observability (auth Phase G) ---

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'axes': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}

# --- Error monitoring ---

_SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if _SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        environment='development' if DEBUG else 'production',
        traces_sample_rate=0.2,
        send_default_pii=False,
    )

# --- Development seed (local only) ---
# WARNING: Remove this entire block from the codebase before production deploy.
# See docs/PRODUCTION_CHECKLIST.md
ENABLE_DEV_SEED = DEBUG and os.environ.get('ENABLE_DEV_SEED', 'False').lower() in (
    'true',
    '1',
    'yes',
)
DEV_SEED_FILE = BASE_DIR / 'dev' / 'seed.yaml'
DEV_SUPERUSER_EMAIL = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
