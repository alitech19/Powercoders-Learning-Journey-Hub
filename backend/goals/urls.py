from django.urls import path

from . import views

app_name = 'goals'

urlpatterns = [
    path('', views.goal_list, name='list'),
    path('new/', views.goal_create, name='create'),
    path('<int:pk>/', views.goal_detail, name='detail'),
    path('<int:pk>/edit/', views.goal_edit, name='edit'),
    path('<int:pk>/delete/', views.goal_delete, name='delete'),
    path('<int:pk>/achieve/', views.goal_mark_achieved, name='mark_achieved'),
    path('<int:pk>/reactivate/', views.goal_reactivate, name='reactivate'),
    path('enrollments/<int:enrollment_pk>/reactivate/', views.enrollment_reactivate, name='enrollment_reactivate'),
    path('milestones/<int:pk>/toggle/', views.milestone_toggle, name='milestone_toggle'),
    path('<int:pk>/feedback/', views.goal_add_feedback, name='add_feedback'),
    path('feedback/<int:comment_pk>/delete/', views.goal_delete_feedback, name='delete_feedback'),
]
