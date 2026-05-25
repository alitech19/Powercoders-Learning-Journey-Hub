from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm
from . import views

app_name = 'accounts'

urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=EmailAuthenticationForm,
        ),
        name='login',
    ),
    path('dev-login/student/', views.dev_login_student, name='dev_login_student'),
    path('dev-login/teacher/', views.dev_login_teacher, name='dev_login_teacher'),
    path('dev-login/admin/', views.dev_login_admin, name='dev_login_admin'),
]
