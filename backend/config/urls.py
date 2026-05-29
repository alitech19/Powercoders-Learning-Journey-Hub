from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.generic import TemplateView


def health_check(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]
