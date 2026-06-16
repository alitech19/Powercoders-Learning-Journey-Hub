from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import include, path
from django.views.generic import RedirectView
from two_factor import urls as two_factor_urls

from accounts.two_factor_views import EmailLoginView
from config.views import module_disabled_view


def _two_factor_urlpatterns():
    patterns, namespace = two_factor_urls.urlpatterns
    custom = []
    for route in patterns:
        if getattr(route, 'name', None) == 'login':
            custom.append(path('account/login/', EmailLoginView.as_view(), name='login'))
        else:
            custom.append(route)
    return custom, namespace


tf_urlpatterns = _two_factor_urlpatterns()


def offline(request):
    return render(request, 'offline.html', status=200)


def service_worker(request):
    import os
    from django.http import FileResponse
    path_ = settings.PROJECT_ROOT / 'frontend' / 'static' / 'js' / 'sw.js'
    response = FileResponse(open(path_, 'rb'), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def health_check(request):
    payload = {'status': 'ok'}
    if request.GET.get('db'):
        from django.conf import settings
        from django.db import connection

        host = settings.DATABASES['default'].get('HOST', '?')
        payload['db_host'] = host
        try:
            connection.ensure_connection()
            payload['db'] = 'connected'
        except Exception as exc:
            payload['status'] = 'degraded'
            payload['db'] = 'error'
            payload['db_error'] = str(exc)[:300]
    return JsonResponse(payload)


urlpatterns = [
    path('sw.js', service_worker, name='service_worker'),
    path('offline/', offline, name='offline'),
    path('admin/', admin.site.urls),
    path('', include(tf_urlpatterns)),
    path('accounts/', include('accounts.urls')),
    path('health/', health_check, name='health'),
    path('workflows/', include('workflows.urls')),
    path('feedback/', include('feedback.urls')),
    path('goals/', include('goals.urls')),
    path('tasks/', include('tasks.urls')),
    path('reflections/', include('reflections.urls')),
    path('journal/', include('journal.urls')),
    path('habits/', include('habits.urls')),
    path('group/', include('group_space.urls')),
    path('resources/', include('resources.urls')),
    path('bugs/', include('bug_reports.urls')),
    path('module-disabled/<slug:slug>/', module_disabled_view, name='module_disabled'),
    path('', include('info.urls')),
    path('', include('dashboard.urls')),
    path('home/', RedirectView.as_view(pattern_name='dashboard:dashboard', permanent=False), name='home'),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'config.views.page_not_found'
handler403 = 'config.views.permission_denied'
handler500 = 'config.views.server_error'
