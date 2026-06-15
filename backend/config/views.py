from django.shortcuts import render

from cohorts.permissions import user_is_admin

from .modules import MODULE_REGISTRY


def module_disabled_view(request, slug: str):
    label = slug.replace('_', ' ').title()
    for spec in MODULE_REGISTRY:
        if spec.slug == slug:
            label = spec.label
            break
    return render(
        request,
        'errors/module_disabled.html',
        {
            'module_slug': slug,
            'module_label': label,
            'show_admin_hint': user_is_admin(request.user),
        },
        status=200,
    )
