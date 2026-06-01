from django.urls import path

from . import views

app_name = 'resources'

urlpatterns = [
    path('', views.index, name='index'),
    path('containers/new/', views.container_create, name='container_create'),
    path('containers/<int:pk>/', views.container_detail, name='container_detail'),
    path('containers/<int:pk>/edit/', views.container_edit, name='container_edit'),
    path('containers/<int:pk>/delete/', views.container_delete, name='container_delete'),
    path('containers/<int:container_pk>/items/new/', views.item_create, name='item_create'),
    path('items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('items/<int:pk>/move/', views.item_move, name='item_move'),
]
