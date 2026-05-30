from django.urls import path

from . import views

app_name = 'feedback'

urlpatterns = [
    path('<int:content_type_id>/<int:object_id>/add/', views.feedback_add, name='add'),
    path('<int:pk>/delete/', views.feedback_delete, name='delete'),
]
