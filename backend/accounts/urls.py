from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from google_storage import views as google_storage_views

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
    path('storage/', google_storage_views.storage_settings, name='storage_settings'),
    path(
        'storage/test-connection/',
        google_storage_views.storage_test_connection,
        name='storage_test_connection',
    ),
    path(
        'storage/test-oauth/',
        google_storage_views.storage_test_oauth,
        name='storage_test_oauth',
    ),
    path(
        'storage/ensure-root/',
        google_storage_views.storage_ensure_root,
        name='storage_ensure_root',
    ),
    path('google/connect/', google_storage_views.google_connect, name='google_connect'),
    path('google/callback/', google_storage_views.google_callback, name='google_callback'),
    path('google/disconnect/', google_storage_views.google_disconnect, name='google_disconnect'),
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
    path('password-reset/', views.SafePasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.txt',
        subject_template_name='accounts/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
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
