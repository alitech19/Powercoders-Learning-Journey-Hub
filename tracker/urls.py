from django.urls import path

from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('create/', views.task_create, name='task_create'),
    path('<int:task_id>/', views.task_detail, name='task_detail'),
    path('<int:task_id>/edit/', views.task_update, name='task_update'),
    path('<int:task_id>/delete/', views.task_delete, name='task_delete'),
    path('<int:task_id>/edit-status/', views.task_edit_status, name='task_edit_status'),
    path('<int:task_id>/subtasks/create/', views.subtask_create, name='subtask_create'),
    path('<int:task_id>/updates/create/', views.update_create, name='update_create'),
    path('<int:task_id>/comments/create/', views.comment_create, name='comment_create'),
    path('comments/<int:comment_id>/reply/', views.comment_reply_create, name='comment_reply_create'),
    path('groups/<int:group_id>/tasks/create/', views.group_task_create, name='group_task_create'),
    path('cohorts/<int:cohort_id>/tasks/create/', views.cohort_task_create, name='cohort_task_create'),
]
