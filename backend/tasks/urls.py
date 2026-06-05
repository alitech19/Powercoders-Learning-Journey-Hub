from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('new/', views.task_create, name='task_create'),
    path('<int:pk>/', views.task_detail, name='task_detail'),
    path('<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('<int:pk>/status/', views.task_quick_status, name='task_quick_status'),
    path('<int:pk>/enroll/', views.task_add_enrollment, name='task_add_enrollment'),
    path('<int:pk>/updates/new/', views.update_create, name='update_create'),
    path('<int:pk>/comments/new/', views.comment_create, name='comment_create'),
    path('<int:pk>/subtasks/new/', views.subtask_create, name='subtask_create'),
    path('<int:pk>/subtasks/participant/new/', views.participant_subtask_create, name='participant_subtask_create'),
    path('subtasks/<int:pk>/edit/', views.subtask_edit, name='subtask_edit'),
    path('subtasks/<int:pk>/delete/', views.subtask_delete, name='subtask_delete'),
    path('subtasks/<int:pk>/status/', views.subtask_status, name='subtask_status'),
    path('comments/<int:comment_pk>/reply/', views.comment_reply_create, name='comment_reply_create'),
]
