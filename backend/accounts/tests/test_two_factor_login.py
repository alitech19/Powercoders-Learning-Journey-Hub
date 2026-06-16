"""Login wizard: email/password and TOTP (django-two-factor)."""

from django.test import Client, TestCase
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from test_utils.users import DEFAULT_PASSWORD, make_student, make_teacher


def _totp_token(device):
    return f'{totp(device.bin_key):06d}'


def _post_auth_step(client, *, email, password):
    return client.post(
        reverse('two_factor:login'),
        {
            'email_login_view-current_step': 'auth',
            'auth-username': email,
            'auth-password': password,
        },
    )


def _post_token_step(client, device):
    return client.post(
        reverse('two_factor:login'),
        {
            'email_login_view-current_step': 'token',
            'token-otp_token': _totp_token(device),
        },
    )


class TwoFactorLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.get(reverse('two_factor:login'))

    def test_student_login_without_totp_reaches_dashboard(self):
        user = make_student('student-login@example.com')
        response = _post_auth_step(
            self.client,
            email=user.email,
            password=DEFAULT_PASSWORD,
        )
        self.assertEqual(response.status_code, 302)
        self.client.get(response.url)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_wrong_password_stays_on_login(self):
        user = make_student('bad-pass@example.com')
        response = _post_auth_step(
            self.client,
            email=user.email,
            password='not-the-password',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_teacher_with_totp_completes_both_steps(self):
        teacher = make_teacher('teacher-2fa@example.com')
        device = TOTPDevice.objects.create(user=teacher, name='default', confirmed=True)

        response = _post_auth_step(
            self.client,
            email=teacher.email,
            password=DEFAULT_PASSWORD,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Two-Factor Authentication')

        response = _post_token_step(self.client, device)
        self.assertEqual(response.status_code, 302)
        self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), teacher.pk)

    def test_teacher_invalid_totp_stays_on_token_step(self):
        teacher = make_teacher('teacher-bad-totp@example.com')
        TOTPDevice.objects.create(user=teacher, name='default', confirmed=True)

        _post_auth_step(
            self.client,
            email=teacher.email,
            password=DEFAULT_PASSWORD,
        )
        response = self.client.post(
            reverse('two_factor:login'),
            {
                'email_login_view-current_step': 'token',
                'token-otp_token': '000000',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid token')
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfilePageTests(TestCase):
    """The branded 'Account Security' page (frontend/templates/two_factor/profile/profile.html)."""

    def setUp(self):
        self.client = Client()

    def test_shows_backup_tokens_for_user_with_device(self):
        teacher = make_teacher('profile-with-device@example.com')
        TOTPDevice.objects.create(user=teacher, name='default', confirmed=True)
        self.client.force_login(teacher)

        response = self.client.get(reverse('two_factor:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account Security')
        self.assertContains(response, 'Backup Tokens')
        self.assertContains(response, 'Show Codes')

    def test_shows_enable_cta_for_user_without_device(self):
        student = make_student('profile-no-device@example.com')
        self.client.force_login(student)

        response = self.client.get(reverse('two_factor:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enable Two-Factor Authentication')
        self.assertNotContains(response, 'Backup Tokens')
