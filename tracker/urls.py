from django.urls import path

from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.tracker_home, name='home'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/edit-status/', views.task_edit_status, name='task_edit_status'),
    path('tasks/<int:task_id>/subtasks/create/', views.subtask_create, name='subtask_create'),
    path('tasks/<int:task_id>/updates/create/', views.update_create, name='update_create'),
    path('tasks/<int:task_id>/comments/create/', views.comment_create, name='comment_create'),
    path('groups/<int:group_id>/tasks/create/', views.group_task_create, name='group_task_create'),
]
