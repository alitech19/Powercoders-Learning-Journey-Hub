"""
Create or update a development superuser from environment variables.

DEV ONLY — do not use in production.
See docs/PRODUCTION_CHECKLIST.md
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.dev_seed import apply_dev_user_security_bypass


class Command(BaseCommand):
    help = 'Create or update a development superuser from DJANGO_SUPERUSER_* env vars.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR(
                    'Refusing to create dev superuser when DEBUG=False. '
                    'See docs/PRODUCTION_CHECKLIST.md'
                )
            )
            return

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
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )

        user.role = User.Role.ADMIN
        user.display_name = display_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        apply_dev_user_security_bypass(user)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created development superuser "{display_name}" ({email}).')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Updated development superuser "{display_name}" ({email}).')
            )

        self.stdout.write(
            self.style.WARNING(
                'REMINDER: Remove create_dev_superuser from production deploy. '
                'See docs/PRODUCTION_CHECKLIST.md'
            )
        )
