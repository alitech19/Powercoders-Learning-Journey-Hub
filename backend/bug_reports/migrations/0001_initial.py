import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BugReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_url', models.CharField(max_length=2048)),
                ('page_path', models.CharField(blank=True, max_length=512)),
                ('description', models.TextField()),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('submitted', 'Submitted'),
                            ('in_progress', 'In progress'),
                            ('closed', 'Closed'),
                            ('rejected', 'Rejected'),
                            ('reopened', 'Reopened'),
                        ],
                        default='submitted',
                        max_length=20,
                    ),
                ),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'assigned_to',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='assigned_bug_reports',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'reporter',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='bug_reports',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='BugReportMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('is_staff_reply', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'author',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='bug_report_messages',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'report',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='messages',
                        to='bug_reports.bugreport',
                    ),
                ),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='bugreport',
            index=models.Index(fields=['status', 'created_at'], name='bug_reports_status_0a8e2d_idx'),
        ),
        migrations.AddIndex(
            model_name='bugreport',
            index=models.Index(fields=['assigned_to', 'status'], name='bug_reports_assigne_3f1b0a_idx'),
        ),
    ]
