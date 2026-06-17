import gzip
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def backup_database(self):
    """Weekly pg_dump → gzip → S3-compatible upload with automatic retention pruning."""
    from django.conf import settings

    bucket = getattr(settings, 'BACKUP_S3_BUCKET', '')
    access_key = getattr(settings, 'BACKUP_S3_ACCESS_KEY', '')
    secret_key = getattr(settings, 'BACKUP_S3_SECRET_KEY', '')

    if not all([bucket, access_key, secret_key]):
        logger.warning('Database backup skipped: BACKUP_S3_BUCKET / ACCESS_KEY / SECRET_KEY not set.')
        return 'skipped'

    pg_dump = shutil.which('pg_dump')
    if not pg_dump:
        logger.error('Database backup failed: pg_dump not found in PATH.')
        return 'error: pg_dump missing'

    import boto3

    db = settings.DATABASES['default']
    env = {**os.environ, 'PGPASSWORD': db.get('PASSWORD', '')}
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    key = f"db-backups/powerhub_{timestamp}.sql.gz"

    try:
        result = subprocess.run(
            [
                pg_dump,
                '-h', db.get('HOST', 'localhost'),
                '-p', str(db.get('PORT', '5432')),
                '-U', db.get('USER', ''),
                db.get('NAME', ''),
            ],
            capture_output=True,
            env=env,
            check=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as exc:
        logger.error('pg_dump failed: %s', exc.stderr.decode()[:500])
        raise self.retry(exc=exc)

    compressed = gzip.compress(result.stdout, compresslevel=6)

    s3 = boto3.client(
        's3',
        endpoint_url=getattr(settings, 'BACKUP_S3_ENDPOINT_URL', '') or None,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=getattr(settings, 'BACKUP_S3_REGION', 'us-east-1'),
    )
    s3.put_object(Bucket=bucket, Key=key, Body=compressed, ContentType='application/gzip')
    logger.info('Database backup uploaded: %s (%d KB)', key, len(compressed) // 1024)

    _prune_old_backups(s3, bucket, getattr(settings, 'BACKUP_RETENTION_DAYS', 30))
    return key


def _prune_old_backups(s3, bucket: str, retention_days: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    paginator = s3.get_paginator('list_objects_v2')
    to_delete = []
    for page in paginator.paginate(Bucket=bucket, Prefix='db-backups/'):
        for obj in page.get('Contents', []):
            if obj['LastModified'] < cutoff:
                to_delete.append({'Key': obj['Key']})
    if to_delete:
        s3.delete_objects(Bucket=bucket, Delete={'Objects': to_delete})
        logger.info('Pruned %d old backup(s) older than %d days', len(to_delete), retention_days)


@shared_task
def ping():
    return 'pong'


@shared_task
def publish_scheduled_entity_task(entity_type: str, entity_pk: int) -> bool:
    from config.entity_publish import publish_entity_now

    try:
        return publish_entity_now(entity_type, entity_pk)
    except Exception:
        logger.exception('Scheduled publish failed for %s %s', entity_type, entity_pk)
        return False
