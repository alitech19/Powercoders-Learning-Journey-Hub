from celery import shared_task


@shared_task
def sync_post_to_slack_channel_task(post_id: int) -> bool:
    from .slack_sync import deliver_post_to_slack_channel

    return deliver_post_to_slack_channel(post_id)
