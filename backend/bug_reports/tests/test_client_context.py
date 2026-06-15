from django.test import SimpleTestCase

from bug_reports.client_context import parse_client_context


class ClientContextTests(SimpleTestCase):
    def test_parses_allowed_fields(self):
        raw = {
            'browser': 'Firefox 128',
            'os': 'Linux',
            'viewport': '1280×720',
            'screen': '1920×1080',
            'pixel_ratio': 1.25,
            'color_scheme': 'dark',
            'timezone': 'Europe/Zurich',
            'language': 'en-US',
            'touch': False,
            'connection': '4g',
            'geolocation': 'secret',
            'user_agent': 'Mozilla/5.0...',
        }
        cleaned = parse_client_context(raw)
        self.assertEqual(cleaned['browser'], 'Firefox 128')
        self.assertEqual(cleaned['timezone'], 'Europe/Zurich')
        self.assertNotIn('geolocation', cleaned)
        self.assertNotIn('user_agent', cleaned)

    def test_rejects_invalid_json(self):
        self.assertEqual(parse_client_context('not-json'), {})

    def test_clamps_pixel_ratio(self):
        self.assertNotIn('pixel_ratio', parse_client_context({'pixel_ratio': 99}))
