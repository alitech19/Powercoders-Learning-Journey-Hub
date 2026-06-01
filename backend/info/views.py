from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

from .content import load_topic, visible_sections
from .registry import ALLOWED_APP_SLUGS, HELP_LABELS, build_info_url


def _source_label(help_key: str) -> str:
    view_name = help_key.replace('.', ':')
    return HELP_LABELS.get(view_name, help_key.replace('.', ' · ').replace('_', ' ').title())


@login_required
def topic(request, app_slug: str):
    if app_slug not in ALLOWED_APP_SLUGS:
        raise Http404

    topic_doc = load_topic(app_slug)
    sections = visible_sections(topic_doc, request.user)
    if not sections:
        raise Http404

    section_id = (request.GET.get('section') or '').strip()
    visible_ids = {s.section_id for s in sections}
    if section_id not in visible_ids:
        section_id = sections[0].section_id

    help_key = (request.GET.get('from') or '').strip()
    back_url = request.META.get('HTTP_REFERER') or reverse('dashboard:dashboard')

    toc = [
        {
            'id': s.section_id,
            'title': s.title,
            'url': build_info_url(
                app_slug=app_slug,
                section=s.section_id,
                help_key=help_key or f'{app_slug}.overview',
            ),
            'active': s.section_id == section_id,
        }
        for s in sections
    ]

    context = {
        'topic': topic_doc,
        'sections': sections,
        'active_section': section_id,
        'toc': toc,
        'source_label': _source_label(help_key) if help_key else topic_doc.title,
        'help_key': help_key,
        'back_url': back_url,
    }
    return render(request, 'info/topic.html', context)
