from two_factor.views import LoginView as TwoFactorLoginView

from .forms import EmailAuthenticationForm


class EmailLoginView(TwoFactorLoginView):
    """two_factor login wizard with email + password on the first step."""

    form_list = (
        (TwoFactorLoginView.AUTH_STEP, EmailAuthenticationForm),
        *TwoFactorLoginView.form_list[1:],
    )
