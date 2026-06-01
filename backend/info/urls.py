from django.urls import path

from . import views

app_name = 'info'

urlpatterns = [
    path('info/<slug:app_slug>/', views.topic, name='topic'),
]
