def unread_notifications(request):
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0}
    try:
        count = request.user.notifications.filter(is_read=False).count()
    except Exception:
        count = 0
    return {'unread_notifications_count': count}
