from django.conf import settings


def dev_login(request):
    return {
        'ENABLE_DEV_LOGIN': getattr(settings, 'ENABLE_DEV_LOGIN', False),
    }
