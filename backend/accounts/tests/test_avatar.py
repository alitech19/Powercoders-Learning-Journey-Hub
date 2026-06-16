import base64
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.avatar_storage import MAX_AVATAR_BYTES, AvatarUploadError, encode_upload
from accounts.models import User
from test_utils.users import login_as, make_student


class AvatarStorageTests(TestCase):
    def _png_upload(self, size=(8, 8)):
        image = Image.new('RGB', size, color='red')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile('avatar.png', buffer.read(), content_type='image/png')

    def test_encode_upload_returns_base64(self):
        data, content_type = encode_upload(self._png_upload())
        self.assertEqual(content_type, 'image/png')
        self.assertTrue(base64.b64decode(data))

    def test_encode_upload_rejects_oversized_file(self):
        upload = SimpleUploadedFile('big.bin', b'x' * (MAX_AVATAR_BYTES + 1))
        with self.assertRaises(AvatarUploadError):
            encode_upload(upload)

    def test_encode_upload_rejects_non_image(self):
        upload = SimpleUploadedFile('notes.txt', b'not an image', content_type='text/plain')
        with self.assertRaises(AvatarUploadError):
            encode_upload(upload)


class ServeAvatarViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('avatar@example.com')
        image = Image.new('RGB', (12, 12), color='blue')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        self.user.avatar_data = base64.b64encode(buffer.getvalue()).decode('ascii')
        self.user.avatar_content_type = 'image/png'
        self.user.avatar_updated_at = timezone.now()
        self.user.save()
        login_as(self.client, self.user)

    def test_serve_avatar_returns_image(self):
        response = self.client.get(reverse('accounts:avatar', args=[self.user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('max-age=', response['Cache-Control'])
        self.assertIn('ETag', response)

    def test_serve_avatar_returns_304_when_etag_matches(self):
        first = self.client.get(reverse('accounts:avatar', args=[self.user.pk]))
        etag = first['ETag']
        second = self.client.get(
            reverse('accounts:avatar', args=[self.user.pk]),
            HTTP_IF_NONE_MATCH=etag,
        )
        self.assertEqual(second.status_code, 304)

    def test_serve_avatar_404_without_data(self):
        other = make_student('no-avatar@example.com')
        login_as(self.client, other)
        response = self.client.get(reverse('accounts:avatar', args=[other.pk]))
        self.assertEqual(response.status_code, 404)


class ProfileAvatarUploadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_student('upload@example.com', display_name='Uploader')
        login_as(self.client, self.user)

    def _png_file(self):
        image = Image.new('RGB', (10, 10), color='green')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile('avatar.png', buffer.read(), content_type='image/png')

    def test_post_uploads_avatar_to_database(self):
        response = self.client.post(
            reverse('accounts:profile'),
            {
                'display_name': self.user.display_name,
                'email_notifications_enabled': 'on',
                'avatar': self._png_file(),
            },
        )
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_custom_avatar)
        self.assertEqual(self.user.avatar_content_type, 'image/png')
        self.assertIn('accounts/avatar/', self.user.get_avatar_url())

    def test_post_rejects_oversized_avatar(self):
        response = self.client.post(
            reverse('accounts:profile'),
            {
                'display_name': self.user.display_name,
                'email_notifications_enabled': 'on',
                'avatar': SimpleUploadedFile(
                    'big.png',
                    b'x' * (MAX_AVATAR_BYTES + 1),
                    content_type='image/png',
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user.has_custom_avatar)
