import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import User
from test_utils.users import DEFAULT_PASSWORD, login_as, make_student


class ProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('profile@example.com', display_name='Before')
        login_as(self.client, self.user)

    def test_get_profile(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_post_updates_display_name(self):
        response = self.client.post(
            reverse('accounts:profile'),
            {
                'display_name': 'After',
                'email_notifications_enabled': 'on',
            },
        )
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, 'After')
        self.assertTrue(self.user.email_notifications_enabled)

    def test_post_remove_avatar(self):
        tmp_media = tempfile.mkdtemp()
        try:
            with self.settings(MEDIA_ROOT=tmp_media):
                image = Image.new('RGB', (8, 8), color='red')
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                buffer.seek(0)
                self.user.avatar = SimpleUploadedFile(
                    'avatar.png',
                    buffer.read(),
                    content_type='image/png',
                )
                self.user.save(update_fields=['avatar'])
                self.assertTrue(self.user.avatar)

                response = self.client.post(
                    reverse('accounts:profile'),
                    {
                        'display_name': self.user.display_name,
                        'email_notifications_enabled': 'on',
                        'remove_avatar': '1',
                    },
                )
                self.assertRedirects(response, reverse('accounts:profile'))
                self.user.refresh_from_db()
                self.assertFalse(self.user.avatar)
        finally:
            shutil.rmtree(tmp_media, ignore_errors=True)


class OnboardingViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student(
            'onboard@example.com',
            bypass_onboarding=False,
        )
        self.user.privacy_policy_accepted = True
        self.user.must_change_password = False
        self.user.save(
            update_fields=['privacy_policy_accepted', 'must_change_password'],
        )
        login_as(self.client, self.user)

    def test_welcome_post_marks_seen(self):
        response = self.client.post(reverse('accounts:welcome'))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.welcome_seen)

    def test_privacy_policy_post_accepts(self):
        self.user.privacy_policy_accepted = False
        self.user.save(update_fields=['privacy_policy_accepted'])
        response = self.client.post(reverse('accounts:privacy_policy'))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.privacy_policy_accepted)
        self.assertIsNotNone(self.user.privacy_policy_accepted_at)


class PasswordChangeRequiredViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('pwd@example.com', bypass_onboarding=False)
        self.user.privacy_policy_accepted = True
        self.user.welcome_seen = True
        self.user.must_change_password = True
        self.user.save(
            update_fields=[
                'privacy_policy_accepted',
                'welcome_seen',
                'must_change_password',
            ],
        )
        login_as(self.client, self.user)

    def test_get_shows_form(self):
        response = self.client.get(reverse('accounts:password_change_required'))
        self.assertEqual(response.status_code, 200)

    def test_post_clears_must_change_password(self):
        response = self.client.post(
            reverse('accounts:password_change_required'),
            {
                'old_password': DEFAULT_PASSWORD,
                'new_password1': 'new-pass-456',
                'new_password2': 'new-pass-456',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)


class LoginRequiredTests(TestCase):
    def test_profile_redirects_anonymous(self):
        response = Client().get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
