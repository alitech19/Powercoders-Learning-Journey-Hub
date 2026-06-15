from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group_space', '0004_post_drive_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='drive_doc_kind',
            field=models.CharField(
                blank=True,
                choices=[
                    ('document', 'Google Doc'),
                    ('spreadsheet', 'Google Sheet'),
                    ('presentation', 'Google Slides'),
                    ('form', 'Google Form'),
                ],
                max_length=20,
            ),
        ),
    ]
