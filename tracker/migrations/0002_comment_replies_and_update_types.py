# Generated manually for tracker workflow updates

from django.db import migrations, models
import django.db.models.deletion


def convert_question_updates_to_note(apps, schema_editor):
    TaskUpdate = apps.get_model('tracker', 'TaskUpdate')
    TaskUpdate.objects.filter(update_type='question').update(update_type='note')


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            convert_question_updates_to_note,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='taskupdate',
            name='update_type',
            field=models.CharField(
                choices=[
                    ('progress', 'Progress'),
                    ('blocker', 'Blocker'),
                    ('note', 'Note'),
                ],
                default='note',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='taskcomment',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='replies',
                to='tracker.taskcomment',
            ),
        ),
    ]
