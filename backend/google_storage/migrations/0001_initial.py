import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cohorts', '0001_initial'),
        ('group_space', '0003_chat_ordering'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleWorkspaceStorageConfig',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('is_enabled', models.BooleanField(default=False, help_text='Master switch for staff Shared drive uploads.')),
                ('shared_drive_id', models.CharField(blank=True, max_length=128)),
                ('shared_drive_name', models.CharField(blank=True, max_length=255)),
                ('shared_root_folder_id', models.CharField(blank=True, max_length=128)),
                ('root_folder_name', models.CharField(default='PowerHUB', max_length=128)),
                ('service_account_email', models.EmailField(blank=True, editable=False)),
                ('service_account_json_encrypted', models.TextField(blank=True)),
                ('student_oauth_enabled', models.BooleanField(default=False)),
                ('oauth_client_id', models.CharField(blank=True, max_length=255)),
                ('oauth_client_secret_encrypted', models.TextField(blank=True)),
                ('oauth_redirect_uri', models.URLField(blank=True, max_length=512)),
                ('workspace_hosted_domain', models.CharField(blank=True, help_text='Expected Google Workspace domain (e.g. powercoders.org).', max_length=255)),
                ('last_health_check_at', models.DateTimeField(blank=True, null=True)),
                ('last_health_ok', models.BooleanField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='google_storage_config_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Google workspace storage',
                'verbose_name_plural': 'Google workspace storage',
            },
        ),
        migrations.CreateModel(
            name='GoogleAccountConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_subject', models.CharField(max_length=128)),
                ('google_email', models.EmailField(max_length=254)),
                ('access_token_encrypted', models.TextField(blank=True)),
                ('refresh_token_encrypted', models.TextField()),
                ('token_expires_at', models.DateTimeField(blank=True, null=True)),
                ('root_folder_id', models.CharField(blank=True, max_length=128)),
                ('connected_at', models.DateTimeField(auto_now_add=True)),
                ('disconnected_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_account_connection', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='GoogleDriveFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('storage_backend', models.CharField(choices=[('shared_org', 'Org Shared drive'), ('personal', 'My Drive')], max_length=20)),
                ('folder_kind', models.CharField(choices=[('root', 'PowerHUB root'), ('group', 'Group folder')], max_length=20)),
                ('drive_folder_id', models.CharField(max_length=128)),
                ('drive_path', models.CharField(max_length=512)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='google_drive_folders', to='cohorts.group')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='google_drive_folders', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DriveUploadLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('storage_backend', models.CharField(blank=True, max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('duration_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('error_code', models.CharField(blank=True, max_length=64)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drive_upload_logs', to='group_space.post')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drive_upload_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='googleaccountconnection',
            index=models.Index(fields=['google_email'], name='google_stor_google__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='googledrivefolder',
            index=models.Index(fields=['storage_backend', 'folder_kind'], name='google_stor_storage_4d5e6f_idx'),
        ),
        migrations.AddConstraint(
            model_name='googledrivefolder',
            constraint=models.UniqueConstraint(condition=models.Q(('storage_backend', 'shared_org')), fields=('storage_backend', 'folder_kind', 'group'), name='google_storage_unique_shared_folder'),
        ),
        migrations.AddConstraint(
            model_name='googledrivefolder',
            constraint=models.UniqueConstraint(condition=models.Q(('storage_backend', 'personal')), fields=('storage_backend', 'user', 'folder_kind', 'group'), name='google_storage_unique_personal_folder'),
        ),
        migrations.AddIndex(
            model_name='driveuploadlog',
            index=models.Index(fields=['status', 'created_at'], name='google_stor_status_7g8h9i_idx'),
        ),
    ]
