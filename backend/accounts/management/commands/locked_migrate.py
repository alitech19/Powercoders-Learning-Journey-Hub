"""
Run migrations under a PostgreSQL advisory lock.

Safe when multiple containers (or a manual `migrate` and `docker compose up`)
start at the same time — callers serialize instead of racing on CREATE TABLE.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

# Single app-wide lock id for migrate (PostgreSQL advisory locks are 64-bit ints).
_MIGRATE_LOCK_ID = 8_347_291


class Command(BaseCommand):
    help = 'Apply migrations with a PostgreSQL advisory lock (parallel-safe).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_true',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Exit with a non-zero status if unapplied migrations exist.',
        )

    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_lock(%s)', [_MIGRATE_LOCK_ID])
        try:
            call_command(
                'migrate',
                interactive=not options['noinput'],
                check=options['check'],
                verbosity=verbosity,
            )
        finally:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(%s)', [_MIGRATE_LOCK_ID])
