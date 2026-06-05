"""Shared HTML5 date field configuration for edit forms."""

from __future__ import annotations

from datetime import datetime

from django import forms

HTML5_DATE_FORMAT = '%Y-%m-%d'


def html5_date_widget(**attrs) -> forms.DateInput:
    return forms.DateInput(
        format=HTML5_DATE_FORMAT,
        attrs={'type': 'date', **attrs},
    )


def configure_html5_date_field(field: forms.DateField) -> None:
    """Ensure DateField values round-trip through ``<input type=\"date\">``."""
    field.input_formats = [HTML5_DATE_FORMAT]
    if isinstance(field.widget, forms.DateInput):
        field.widget.format = HTML5_DATE_FORMAT
        field.widget.attrs.setdefault('type', 'date')
    else:
        field.widget = html5_date_widget()


def format_html5_date(value) -> str:
    """Format a date/datetime/string for ``value`` on ``<input type=\"date\">``."""
    if value is None or value == '':
        return ''
    if hasattr(value, 'hour'):
        value = value.date()
    if hasattr(value, 'strftime'):
        return value.strftime(HTML5_DATE_FORMAT)
    text = str(value).strip()
    if len(text) >= 10 and text[4] == '-' and text[7] == '-':
        return text[:10]
    from django.utils.dateparse import parse_date

    parsed = parse_date(text)
    if parsed is not None:
        return parsed.strftime(HTML5_DATE_FORMAT)
    for fmt in ('%d/%m/%Y', '%d.%m.%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(text, fmt).date().strftime(HTML5_DATE_FORMAT)
        except ValueError:
            continue
    return text
