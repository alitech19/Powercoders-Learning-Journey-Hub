from django.test import RequestFactory, TestCase

from accounts.axes_utils import get_axes_username


class GetAxesUsernameTests(TestCase):
    def test_reads_username_from_credentials(self):
        value = get_axes_username(None, {'username': 'a@b.com'})
        self.assertEqual(value, 'a@b.com')

    def test_reads_auth_username_from_credentials(self):
        value = get_axes_username(None, {'auth-username': 'a@b.com'})
        self.assertEqual(value, 'a@b.com')

    def test_reads_post_auth_username(self):
        request = RequestFactory().post('/login/', {'auth-username': 'post@example.com'})
        self.assertEqual(get_axes_username(request), 'post@example.com')

    def test_reads_post_username_fallback(self):
        request = RequestFactory().post('/login/', {'username': 'plain@example.com'})
        self.assertEqual(get_axes_username(request), 'plain@example.com')
