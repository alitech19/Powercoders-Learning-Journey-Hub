from celery import shared_task


@shared_task
def sync_post_to_slack_channel_task(post_id: int) -> bool:
    from .slack_sync import deliver_post_to_slack_channel

    return deliver_post_to_slack_channel(post_id)


@shared_task
def sync_post_update_to_slack_channel_task(post_id: int) -> bool:
    from .slack_sync import deliver_post_update_to_slack_channel

    return deliver_post_update_to_slack_channel(post_id)


@shared_task
def sync_post_delete_from_slack_channel_task(channel_id: str, slack_ts: str) -> bool:
    from .slack_sync import deliver_post_delete_from_slack

    return deliver_post_delete_from_slack(channel_id, slack_ts)
