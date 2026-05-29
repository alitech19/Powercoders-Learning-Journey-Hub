from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import views

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
    path('welcome/', views.welcome, name='welcome'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('password-change/', views.password_change_required, name='password_change_required'),
    path('dev-login/<str:email>/', views.dev_quick_login, name='dev_quick_login'),
]
