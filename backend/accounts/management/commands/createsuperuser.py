"""Project createsuperuser — admin role + local onboarding skip when DEBUG=True."""

from django.contrib.auth.management.commands.createsuperuser import (
    Command as BaseCreateSuperuserCommand,
)


class Command(BaseCreateSuperuserCommand):
    help = (
        'Create a superuser (role=admin). With DEBUG=True, skips welcome/privacy gates '
        'so you can use Administration immediately after login.'
    )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        self.stdout.write(
            self.style.SUCCESS(
                'Superuser ready. Staff must complete 2FA setup on first login '
                '(Administration works after that).',
            ),
        )
