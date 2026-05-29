from django.urls import path

from . import views

app_name = 'workflows'

urlpatterns = [
    path('', views.workflow_list, name='list'),
    path('create/', views.workflow_create, name='create'),
    path('<int:pk>/', views.workflow_detail, name='detail'),
    path('<int:pk>/edit/', views.workflow_edit, name='edit'),
    path('<int:pk>/delete/', views.workflow_delete, name='delete'),
    path('<int:workflow_pk>/steps/add/', views.step_add, name='step_add'),
    path('steps/<int:pk>/delete/', views.step_delete, name='step_delete'),
    path('steps/<int:step_pk>/toggle/', views.step_toggle, name='step_toggle'),
    path('<int:workflow_pk>/enroll/', views.enroll_student, name='enroll'),
    path('<int:workflow_pk>/unenroll/<int:student_pk>/', views.unenroll_student, name='unenroll'),
]
