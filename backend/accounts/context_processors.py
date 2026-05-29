from .dev_seed import build_dev_login_context


def dev_login_panel(request):
    return build_dev_login_context()
