from dataclasses import dataclass

from django.urls import reverse
from django.utils.http import urlencode

from config.module_access import is_module_enabled


@dataclass(frozen=True)
class BugReportButton:
    enabled: bool
    url: str = ''
    aria_label: str = 'Report a bug on this page'


def bug_report_button(request):
    if not request.user.is_authenticated or not is_module_enabled('bug_reports'):
        return {'bug_report_button': BugReportButton(enabled=False)}

    from_param = request.get_full_path()
    url = f"{reverse('bug_reports:report_create')}?{urlencode({'from': from_param})}"
    return {
        'bug_report_button': BugReportButton(
            enabled=True,
            url=url,
            aria_label='Report a bug on this page',
        ),
    }
