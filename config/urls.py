from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('tracker/', include('tracker.urls')),
    path('', RedirectView.as_view(pattern_name='dashboard:dashboard', permanent=False)),
]
