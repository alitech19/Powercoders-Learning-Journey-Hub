from django.test import TestCase, override_settings

from google_storage.crypto import decrypt_secret, encrypt_secret, mask_secret


class CryptoTests(TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        plain = 'super-secret-service-account-json'
        encrypted = encrypt_secret(plain)
        self.assertNotEqual(encrypted, plain)
        self.assertEqual(decrypt_secret(encrypted), plain)

    def test_empty_string(self):
        self.assertEqual(encrypt_secret(''), '')
        self.assertEqual(decrypt_secret(''), '')

    def test_decrypt_fails_after_secret_key_rotation(self):
        encrypted = encrypt_secret('token')
        with override_settings(SECRET_KEY='different-key'):
            with self.assertRaises(ValueError):
                decrypt_secret(encrypted)

    def test_mask_secret(self):
        self.assertEqual(mask_secret('abcdefghij'), '••••••••••••…ghij')
