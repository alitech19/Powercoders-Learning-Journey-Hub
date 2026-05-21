from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm

urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=EmailAuthenticationForm,
        ),
        name='login',
    ),
]
