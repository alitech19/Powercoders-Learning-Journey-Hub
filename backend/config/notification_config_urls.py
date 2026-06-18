from django.urls import path

from .notification_config_views import notification_config_view

app_name = 'config'

urlpatterns = [
    path('notifications/', notification_config_view, name='notification_config'),
]
