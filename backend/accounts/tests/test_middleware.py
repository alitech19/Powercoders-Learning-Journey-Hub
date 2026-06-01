from django.http import HttpResponse
from django.test import RequestFactory, TestCase

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
