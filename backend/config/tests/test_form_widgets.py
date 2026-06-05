from datetime import date, datetime

from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase

from config.form_widgets import (
    configure_html5_date_field,
    format_html5_date,
    html5_date_widget,
    resolve_form_date,
)


class FormWidgetTests(SimpleTestCase):
    def test_format_html5_date_from_date(self):
        self.assertEqual(format_html5_date(date(2026, 6, 4)), '2026-06-04')

    def test_format_html5_date_from_datetime(self):
        self.assertEqual(format_html5_date(datetime(2026, 6, 4, 15, 30)), '2026-06-04')

    def test_format_html5_date_from_iso_string(self):
        self.assertEqual(format_html5_date('2026-06-04T00:00:00'), '2026-06-04')

    def test_format_html5_date_empty(self):
        self.assertEqual(format_html5_date(None), '')
        self.assertEqual(format_html5_date(''), '')

    def test_configure_html5_date_field(self):
        field = forms.DateField(widget=html5_date_widget())
        configure_html5_date_field(field)
        self.assertEqual(field.input_formats, ['%Y-%m-%d'])
        self.assertEqual(field.widget.format, '%Y-%m-%d')
        self.assertEqual(field.widget.attrs['type'], 'date')

    def test_html_date_template_filter(self):
        template = Template(
            '{% load form_tags %}'
            '<input type="date" value="{{ value|html_date }}">'
        )
        html = template.render(Context({'value': date(2026, 3, 15)}))
        self.assertIn('value="2026-03-15"', html)

    def test_is_checked_filter(self):
        template = Template(
            '{% load form_tags %}'
            '{% if value|is_checked %}yes{% else %}no{% endif %}'
        )
        self.assertEqual(template.render(Context({'value': True})), 'yes')
        self.assertEqual(template.render(Context({'value': False})), 'no')
        self.assertEqual(template.render(Context({'value': None})), 'yes')

    def test_format_html5_date_parses_dmy_string(self):
        self.assertEqual(format_html5_date('04/07/2026'), '2026-07-04')

    def test_resolve_form_date_uses_instance_fallback(self):
        from goals.forms import GoalForm
        from goals.models import Goal

        goal = Goal(
            pk=1,
            title='G',
            category=Goal.Category.TECHNICAL,
            visibility=Goal.Visibility.PRIVATE,
            target_date=date(2026, 5, 1),
        )
        form = GoalForm(instance=goal, show_status=False)
        self.assertEqual(
            resolve_form_date(form, 'target_date', instance=goal),
            '2026-05-01',
        )

    def test_bound_date_value_tag_uses_fallback(self):
        from django import forms

        class TestForm(forms.Form):
            target_date = forms.DateField(required=False)

        form = TestForm()
        template = Template(
            '{% load form_tags %}'
            '{% bound_date_value form.target_date fallback as out %}{{ out }}'
        )
        html = template.render(Context({
            'form': form,
            'fallback': date(2026, 5, 1),
        }))
        self.assertEqual(html, '2026-05-01')
