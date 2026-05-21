"""
Create or update a development superuser from environment variables.

DEV ONLY — do not use weak credentials in production.
Set DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_DISPLAY_NAME, and
DJANGO_SUPERUSER_PASSWORD in .env for local Docker development.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create or update a development superuser from DJANGO_SUPERUSER_* env vars.'

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        display_name = os.environ.get('DJANGO_SUPERUSER_DISPLAY_NAME', 'Admin').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    'Skipping dev superuser: set DJANGO_SUPERUSER_EMAIL and '
                    'DJANGO_SUPERUSER_PASSWORD in .env to enable auto-creation.'
                )
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'display_name': display_name,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )

        if hasattr(user, 'role'):
            user.role = User.Role.ADMIN

        user.display_name = display_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created development superuser "{display_name}" ({email}).')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Updated development superuser "{display_name}" ({email}).')
            )
