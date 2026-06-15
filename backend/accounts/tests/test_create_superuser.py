from django.test import TestCase, override_settings

from accounts.models import User


class CreateSuperuserTests(TestCase):
    @override_settings(DEBUG=True)
    def test_create_superuser_sets_admin_role_and_skips_onboarding_locally(self):
        user = User.objects.create_superuser(
            email='admin-local@example.com',
            password='test-pass-123',
            display_name='Local Admin',
        )
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.privacy_policy_accepted)
        self.assertTrue(user.welcome_seen)

    @override_settings(DEBUG=False)
    def test_create_superuser_prod_does_not_skip_onboarding(self):
        user = User.objects.create_superuser(
            email='admin-prod@example.com',
            password='test-pass-123',
            display_name='Prod Admin',
        )
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertFalse(user.privacy_policy_accepted)
        self.assertFalse(user.welcome_seen)
