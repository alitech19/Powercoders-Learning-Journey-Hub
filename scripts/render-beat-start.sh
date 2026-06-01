#!/usr/bin/env sh
# Render free tier: migrate before beat (django_celery_beat tables). See docs/DEPLOY.md
set -e
cd "$(dirname "$0")/../backend"
python manage.py migrate --noinput
exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
