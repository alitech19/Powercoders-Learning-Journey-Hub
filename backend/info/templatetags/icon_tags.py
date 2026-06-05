from django import template

from config.icon_map import is_valid_icon_key, normalize_size, normalize_variant

register = template.Library()


@register.inclusion_tag('includes/_volumetric_icon.html')
def volumetric_icon(icon, size=None, variant=None, extra_class=''):
    return {
        'icon_key': icon if is_valid_icon_key(icon) else 'unknown',
        'size': normalize_size(size),
        'variant': normalize_variant(variant),
        'extra_class': extra_class,
    }
