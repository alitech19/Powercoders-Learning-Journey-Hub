from django import template

from config.icon_map import get_glyph, normalize_size, normalize_variant

register = template.Library()


@register.inclusion_tag('includes/_volumetric_icon.html')
def volumetric_icon(icon, size=None, variant=None, extra_class=''):
    return {
        'glyph': get_glyph(icon),
        'size': normalize_size(size),
        'variant': normalize_variant(variant),
        'extra_class': extra_class,
    }
