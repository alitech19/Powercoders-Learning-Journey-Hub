from django.template import Context, Template
from django.test import SimpleTestCase

from config.icon_map import (
    icon_key_for_url,
    is_valid_icon_key,
    normalize_size,
    normalize_variant,
)
from config.nav import integrated_nav_groups


class IconMapTests(SimpleTestCase):
    def test_known_icon_keys(self):
        self.assertTrue(is_valid_icon_key('tasks'))
        self.assertFalse(is_valid_icon_key('missing'))

    def test_url_icon_keys(self):
        self.assertEqual(icon_key_for_url('tasks:task_list'), 'tasks')
        self.assertEqual(icon_key_for_url('unknown:view'), '')

    def test_normalize_defaults(self):
        self.assertEqual(normalize_size(None), 'md')
        self.assertEqual(normalize_size('lg'), 'lg')
        self.assertEqual(normalize_size('huge'), 'md')
        self.assertEqual(normalize_variant('soft'), 'soft')
        self.assertEqual(normalize_variant('invalid'), 'brand')

    def test_nav_children_include_icon_key(self):
        groups = integrated_nav_groups()
        learning = groups[0]
        tasks = next(c for c in learning['children'] if c['url_name'] == 'tasks:task_list')
        self.assertEqual(tasks['icon_key'], 'tasks')

    def test_volumetric_icon_template_tag_renders_svg_glyph(self):
        template = Template(
            '{% load icon_tags %}'
            '{% volumetric_icon "goals" size="sm" variant="soft" %}'
        )
        html = template.render(Context())
        self.assertIn('h-8 w-8', html)
        self.assertIn('bg-[#F5EDE0]', html)
        self.assertIn('<svg', html)
        self.assertIn('viewBox="0 0 24 24"', html)
