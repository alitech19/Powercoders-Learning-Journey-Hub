from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView
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
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
