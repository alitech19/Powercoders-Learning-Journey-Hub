from django.urls import path

from . import views

app_name = 'habits'

urlpatterns = [
    path('', views.habit_list, name='list'),
    path('new/', views.habit_create, name='create'),
    path('<int:pk>/', views.habit_detail, name='detail'),
    path('<int:pk>/edit/', views.habit_edit, name='edit'),
    path('<int:pk>/delete/', views.habit_delete, name='delete'),
    path('<int:pk>/complete/', views.habit_complete, name='complete'),
    path('<int:pk>/reactivate/', views.habit_reactivate, name='reactivate'),
    path('<int:pk>/log/done/', views.habit_log_done, name='log_done'),
    path('<int:pk>/log/not-done/', views.habit_log_not_done, name='log_not_done'),
]
