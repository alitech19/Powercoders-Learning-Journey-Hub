from django.core.exceptions import ValidationError


def clamp_text(value, max_length):
    return (value or '')[:max_length]


def validate_text_length(value, max_length, field_label='Text'):
    text = value or ''
    if len(text) > max_length:
        raise ValidationError(
            f'{field_label} must be at most {max_length} characters.'
        )
    return text
