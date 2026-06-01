from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import management_views, privacy_views, views

app_name = 'accounts'

urlpatterns = [
    path(
        'login/',
        RedirectView.as_view(pattern_name='two_factor:login', permanent=False),
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path('profile/', views.profile, name='profile'),
    path('profile/export/', privacy_views.data_export, name='data_export'),
    path('profile/delete/', privacy_views.delete_own_account, name='delete_own_account'),
    path('profile/deleted/', privacy_views.account_deleted, name='account_deleted'),
    path('notifications/', privacy_views.notifications_list, name='notifications'),
    path(
        'notifications/<int:pk>/read/',
        privacy_views.notification_mark_read,
        name='notification_read',
    ),
    path('welcome/', views.welcome, name='welcome'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('password-change/', views.password_change_required, name='password_change_required'),
    path('dev-login/<str:email>/', views.dev_quick_login, name='dev_quick_login'),
    path('users/', management_views.user_list, name='user_list'),
    path('users/create/', management_views.user_create, name='user_create'),
    path('users/import/', management_views.user_import, name='user_import'),
    path('users/<int:pk>/deactivate/', management_views.user_deactivate, name='user_deactivate'),
    path('users/<int:pk>/reactivate/', management_views.user_reactivate, name='user_reactivate'),
    path('users/<int:pk>/delete/', management_views.user_delete_account, name='user_delete_account'),
    path('students/', management_views.student_progress, name='student_progress'),
    path('students/<int:pk>/', management_views.student_detail, name='student_detail'),
    path('cohorts/', management_views.cohort_list, name='cohort_list'),
    path('cohorts/new/', management_views.cohort_create, name='cohort_create'),
    path('cohorts/<int:pk>/edit/', management_views.cohort_edit, name='cohort_edit'),
    path('cohorts/<int:pk>/delete/', management_views.cohort_delete, name='cohort_delete'),
    path('cohorts/<int:cohort_pk>/groups/new/', management_views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', management_views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', management_views.group_delete, name='group_delete'),
    path(
        'groups/<int:pk>/assign-students/',
        management_views.group_assign_students,
        name='group_assign_students',
    ),
]
