from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.decorators import admin_required, student_required, teacher_or_admin_required
from test_utils.users import make_admin, make_student, make_teacher


class RoleDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_admin_required_allows_admin(self):
        @admin_required
        def view(request):
            return HttpResponse('ok')

        request = self.factory.get('/')
        request.user = make_admin('admin@example.com')
        self.assertEqual(view(request).content, b'ok')

    def test_admin_required_allows_superuser_with_student_role(self):
        @admin_required
        def view(request):
            return HttpResponse('ok')

        request = self.factory.get('/')
        request.user = make_student('su@example.com', is_superuser=True, is_staff=True)
        self.assertEqual(view(request).content, b'ok')

    def test_admin_required_redirects_student(self):
        @admin_required
        def view(request):
            return HttpResponse('ok')

        request = self.factory.get('/')
        request.user = make_student('s@example.com')
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:dashboard'))

    def test_teacher_or_admin_allows_teacher(self):
        @teacher_or_admin_required
        def view(request):
            return HttpResponse('ok')

        request = self.factory.get('/')
        request.user = make_teacher('t@example.com')
        self.assertEqual(view(request).content, b'ok')

    def test_student_required_redirects_teacher(self):
        @student_required
        def view(request):
            return HttpResponse('ok')

        request = self.factory.get('/')
        request.user = make_teacher('t@example.com')
        response = view(request)
        self.assertEqual(response.status_code, 302)
