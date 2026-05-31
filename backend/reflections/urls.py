from django.urls import path

from . import views

app_name = 'reflections'

urlpatterns = [
    path('', views.reflection_list, name='list'),
    path('new/', views.reflection_create, name='create'),
    path('<int:pk>/', views.reflection_detail, name='detail'),
    path('<int:pk>/edit/', views.reflection_edit, name='edit'),
    path('<int:pk>/delete/', views.reflection_delete, name='delete'),
]
