from django.urls import path

from . import views

app_name = 'group_space'

urlpatterns = [
    path('', views.feed, name='feed'),
    path('send/', views.message_create, name='message_create'),
    path('share/', views.share_create, name='share_create'),
    path('new/', views.post_create, name='post_create'),
    path('share/start/', views.share_start, name='share_start'),
    path('<int:pk>/poll/', views.post_upload_poll, name='post_upload_poll'),
    path('<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('<int:pk>/delete/', views.post_delete, name='post_delete'),
]
