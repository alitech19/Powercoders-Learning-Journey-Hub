from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from accounts.middleware import (
    AuditLoggingMiddleware,
    ForcePasswordChangeMiddleware,
    PrivacyPolicyMiddleware,
    WelcomeMiddleware,
)
from accounts.models import AuditLog
from test_utils.users import make_student


class PrivacyPolicyMiddlewareTests(TestCase):
    def test_redirects_when_not_accepted(self):
        user = make_student('s@example.com', bypass_onboarding=False)
        user.privacy_policy_accepted = False
        user.save(update_fields=['privacy_policy_accepted'])

        request = RequestFactory().get('/workflows/')
        request.user = user
        response = PrivacyPolicyMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('privacy-policy', response.url)

    def test_exempt_path_allows_through(self):
        user = make_student('s@example.com', bypass_onboarding=False)
        user.privacy_policy_accepted = False
        user.save(update_fields=['privacy_policy_accepted'])

        request = RequestFactory().get('/accounts/privacy-policy/')
        request.user = user
        response = PrivacyPolicyMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(response.status_code, 200)


class ForcePasswordChangeMiddlewareTests(TestCase):
    def test_redirects_when_must_change_password(self):
        user = make_student('s@example.com', bypass_onboarding=False)
        user.privacy_policy_accepted = True
        user.must_change_password = True
        user.save(update_fields=['privacy_policy_accepted', 'must_change_password'])

        request = RequestFactory().get('/')
        request.user = user
        response = ForcePasswordChangeMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('password-change', response.url)


class WelcomeMiddlewareTests(TestCase):
    def test_redirects_when_welcome_not_seen(self):
        user = make_student('s@example.com', bypass_onboarding=False)
        user.privacy_policy_accepted = True
        user.welcome_seen = False
        user.save(update_fields=['privacy_policy_accepted', 'welcome_seen'])

        request = RequestFactory().get('/')
        request.user = user
        response = WelcomeMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('welcome', response.url)

    def test_dashboard_path_redirects_when_welcome_not_seen(self):
        user = make_student('s@example.com', bypass_onboarding=False)
        user.privacy_policy_accepted = True
        user.must_change_password = False
        user.welcome_seen = False
        user.save(
            update_fields=[
                'privacy_policy_accepted',
                'must_change_password',
                'welcome_seen',
            ],
        )

        request = RequestFactory().get(reverse('dashboard:dashboard'))
        request.user = user
        response = WelcomeMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('welcome', response.url)

    def test_onboarding_checklist_links_are_exempt(self):
        """Step 3 of welcome.html links to these mid-onboarding; they must not
        bounce back to welcome step 1 (regression test for that bug)."""
        user = make_student('s@example.com', bypass_onboarding=False)
        user.privacy_policy_accepted = True
        user.welcome_seen = False
        user.save(update_fields=['privacy_policy_accepted', 'welcome_seen'])

        checklist_paths = [
            reverse('accounts:profile'),
            reverse('journal:list'),
            reverse('goals:list'),
            reverse('reflections:list'),
            reverse('tasks:task_list'),
            reverse('group_space:feed'),
        ]
        for path in checklist_paths:
            request = RequestFactory().get(path)
            request.user = user
            response = WelcomeMiddleware(lambda r: HttpResponse('ok'))(request)
            self.assertEqual(response.status_code, 200, f'{path} unexpectedly redirected')


class WelcomeDashboardIntegrationTests(TestCase):
    """Dashboard view must not duplicate WelcomeMiddleware redirect."""

    def setUp(self):
        self.client = Client()
        self.user = make_student('ready@example.com', bypass_onboarding=False)
        self.user.privacy_policy_accepted = True
        self.user.must_change_password = False
        self.user.welcome_seen = True
        self.user.save(
            update_fields=[
                'privacy_policy_accepted',
                'must_change_password',
                'welcome_seen',
            ],
        )
        self.client.force_login(self.user)

    def test_dashboard_ok_when_welcome_seen(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)


class AuditLoggingMiddlewareTests(TestCase):
    def test_post_creates_audit_log(self):
        user = make_student('s@example.com')
        request = RequestFactory().post('/accounts/profile/')
        request.user = user
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        AuditLoggingMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.get()
        self.assertEqual(log.user_id, user.pk)
        self.assertEqual(log.method, 'POST')

    def test_skips_static_paths(self):
        user = make_student('s@example.com')
        request = RequestFactory().post('/static/app.js')
        request.user = user

        AuditLoggingMiddleware(lambda r: HttpResponse('ok'))(request)
        self.assertEqual(AuditLog.objects.count(), 0)
