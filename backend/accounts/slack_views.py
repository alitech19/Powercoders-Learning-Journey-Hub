"""HTTP views for Slack OAuth and test messages."""

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from . import slack_oauth


@login_required
def slack_connect(request):
    return slack_oauth.start_connect(request)


@login_required
def slack_callback(request):
    return slack_oauth.finish_connect(request)


@login_required
@require_POST
def slack_disconnect(request):
    return slack_oauth.disconnect(request)


@login_required
@require_POST
def slack_test_message(request):
    return slack_oauth.send_test_message(request)
