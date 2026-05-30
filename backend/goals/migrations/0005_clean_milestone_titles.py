import ast

from django.db import migrations


def normalize_milestone_title(raw):
    title = (raw or '').strip()
    while title.startswith('{') and 'title' in title:
        try:
            parsed = ast.literal_eval(title)
        except (ValueError, SyntaxError):
            break
        if not isinstance(parsed, dict):
            break
        inner = parsed.get('title')
        if not isinstance(inner, str) or inner == title:
            break
        title = inner.strip()
    return title


def clean_milestone_titles(apps, schema_editor):
    Milestone = apps.get_model('goals', 'Milestone')
    for milestone in Milestone.objects.all().iterator():
        cleaned = normalize_milestone_title(milestone.title)
        if cleaned != milestone.title:
            milestone.title = cleaned
            milestone.save(update_fields=['title'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('goals', '0004_remove_legacy_goal_fields'),
    ]

    operations = [
        migrations.RunPython(clean_milestone_titles, noop),
    ]
