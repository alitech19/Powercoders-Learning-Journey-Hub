# Generated manually: email login, display_name, avatar, remove username

from django.db import migrations, models

import accounts.models


def populate_profile_from_username(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        if not user.display_name:
            user.display_name = user.username or user.email.split('@')[0] or 'User'
        if not user.email:
            user.email = f'{user.username}@localhost.invalid'
        user.save(update_fields=['display_name', 'email'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='display_name',
            field=models.CharField(
                default='User',
                help_text='Name shown on the site (not your legal name).',
                max_length=150,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, upload_to='avatars/%Y/%m/'),
        ),
        migrations.RunPython(populate_profile_from_username, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True, verbose_name='email address'),
        ),
        migrations.RemoveField(
            model_name='user',
            name='username',
        ),
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', accounts.models.UserManager()),
            ],
        ),
    ]
