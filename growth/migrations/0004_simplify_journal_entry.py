"""
Simplify DailyJournalEntry: replace did_today, progress_made, blockers,
next_steps with a single content TextField.

Steps:
1. Add content field with temporary default.
2. Migrate existing data into content.
3. Remove old fields.
"""

from django.db import migrations, models


def merge_journal_fields(apps, schema_editor):
    DailyJournalEntry = apps.get_model('growth', 'DailyJournalEntry')
    for entry in DailyJournalEntry.objects.all():
        parts = []
        if entry.did_today and entry.did_today.strip():
            parts.append(f'What did I do today?\n{entry.did_today.strip()}')
        if entry.progress_made and entry.progress_made.strip():
            parts.append(f'What progress did I make?\n{entry.progress_made.strip()}')
        if entry.blockers and entry.blockers.strip():
            parts.append(f'What blocked me?\n{entry.blockers.strip()}')
        if entry.next_steps and entry.next_steps.strip():
            parts.append(f'What should I do next?\n{entry.next_steps.strip()}')
        entry.content = '\n\n'.join(parts) if parts else ''
        entry.save(update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('growth', '0003_add_daily_journal_entry'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyjournalentry',
            name='content',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.RunPython(merge_journal_fields, migrations.RunPython.noop),
        migrations.RemoveField(model_name='dailyjournalentry', name='did_today'),
        migrations.RemoveField(model_name='dailyjournalentry', name='progress_made'),
        migrations.RemoveField(model_name='dailyjournalentry', name='blockers'),
        migrations.RemoveField(model_name='dailyjournalentry', name='next_steps'),
    ]
