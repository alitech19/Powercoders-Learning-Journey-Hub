from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from two_factor import urls as two_factor_urls

from accounts.two_factor_views import EmailLoginView


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


def health_check(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
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
    path('', include('info.urls')),
    path('', include('dashboard.urls')),
    path('home/', RedirectView.as_view(pattern_name='dashboard:dashboard', permanent=False), name='home'),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
