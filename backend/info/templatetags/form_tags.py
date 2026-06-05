from django import template

from config.form_widgets import format_html5_date

register = template.Library()


@register.filter
def html_date(value):
    """Render a date value for HTML5 ``<input type=\"date\">``."""
    return format_html5_date(value)


@register.filter
def is_checked(value):
    """Boolean model field: checked unless explicitly False (None → default on)."""
    return value is not False


@register.simple_tag
def bound_date_value(field, fallback=''):
    """Formatted date for manual inputs — uses bound field value, then fallback."""
    value = field.value()
    if not value and fallback not in (None, ''):
        value = fallback
    return format_html5_date(value)
