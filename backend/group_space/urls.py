from django.urls import path

from . import project_views, views

app_name = 'group_space'

urlpatterns = [
    path('', views.feed, name='feed'),
    path('poll/', views.chat_poll, name='chat_poll'),
    path('send/', views.message_create, name='message_create'),
    path('google-doc/', views.google_doc_create, name='google_doc_create'),
    path('share/', views.share_create, name='share_create'),
    path('new/', views.post_create, name='post_create'),
    path('share/start/', views.share_start, name='share_start'),
    path('projects/', project_views.project_list, name='project_list'),
    path('projects/new/', project_views.project_create, name='project_create'),
    path('projects/<int:pk>/', project_views.project_detail, name='project_detail'),
    path('projects/<int:pk>/members/add/', project_views.project_member_add, name='project_member_add'),
    path('projects/<int:pk>/members/<int:user_pk>/remove/', project_views.project_member_remove, name='project_member_remove'),
    path('projects/<int:pk>/archive/', project_views.project_archive, name='project_archive'),
    path('projects/<int:pk>/unarchive/', project_views.project_unarchive, name='project_unarchive'),
    path('<int:pk>/poll/', views.post_upload_poll, name='post_upload_poll'),
    path('<int:pk>/retry-upload/', views.post_upload_retry, name='post_upload_retry'),
    path('<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('<int:pk>/delete/', views.post_delete, name='post_delete'),
]
