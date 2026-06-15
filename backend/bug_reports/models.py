from django.conf import settings
from django.db import models


class BugReport(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        IN_PROGRESS = 'in_progress', 'In progress'
        CLOSED = 'closed', 'Closed'
        REJECTED = 'rejected', 'Rejected'
        REOPENED = 'reopened', 'Reopened'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bug_reports',
    )
    page_url = models.CharField(max_length=2048)
    page_path = models.CharField(max_length=512, blank=True)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_bug_reports',
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['status', 'created_at'], name='bug_reports_status_0a8e2d_idx'),
            models.Index(fields=['assigned_to', 'status'], name='bug_reports_assigne_3f1b0a_idx'),
        ]

    def __str__(self):
        return f'Bug #{self.pk} ({self.get_status_display()})'


class BugReportMessage(models.Model):
    report = models.ForeignKey(
        BugReport,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bug_report_messages',
    )
    body = models.TextField()
    is_staff_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f'Message on #{self.report_id}'
