"""Read-only aggregates for the admin File storage page."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import DriveUploadLog, GoogleAccountConnection, GoogleDriveFolder


def storage_dashboard_context() -> dict:
    now = timezone.now()
    since = now - timedelta(days=7)

    recent_logs = (
        DriveUploadLog.objects.select_related('user', 'post')
        .order_by('-created_at')[:25]
    )
    connections = (
        GoogleAccountConnection.objects.filter(disconnected_at__isnull=True)
        .select_related('user')
        .order_by('-connected_at')[:50]
    )
    folder_rows = (
        GoogleDriveFolder.objects.select_related('group', 'user')
        .order_by('-created_at')[:30]
    )
    upload_stats = (
        DriveUploadLog.objects.filter(created_at__gte=since)
        .values('status')
        .annotate(count=Count('id'))
    )
    stats_by_status = {row['status']: row['count'] for row in upload_stats}

    return {
        'student_connections': connections,
        'recent_upload_logs': recent_logs,
        'drive_folder_mappings': folder_rows,
        'upload_stats_7d': {
            'success': stats_by_status.get(DriveUploadLog.Status.SUCCESS, 0),
            'failed': stats_by_status.get(DriveUploadLog.Status.FAILED, 0),
            'pending': stats_by_status.get(DriveUploadLog.Status.PENDING, 0),
        },
    }
