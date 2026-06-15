from django.urls import path

from . import views

app_name = 'bug_reports'

urlpatterns = [
    path('new/', views.report_create, name='report_create'),
    path('inbox/', views.report_list, name='report_list'),
    path('inbox/<int:pk>/', views.report_detail, name='report_detail'),
    path('inbox/<int:pk>/take/', views.report_take, name='report_take'),
    path('inbox/<int:pk>/close/', views.report_close, name='report_close'),
    path('inbox/<int:pk>/reject/', views.report_reject, name='report_reject'),
    path('inbox/<int:pk>/reopen/', views.report_reopen, name='report_reopen'),
    path('inbox/<int:pk>/reply/', views.report_reply, name='report_reply'),
]
