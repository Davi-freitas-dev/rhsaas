from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .services_auth import password_reset_rate_limit_exceeded


class LoginSeguroView(LoginView):
    template_name = "caixa/login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user

        if user.has_perm("caixa.view_evento"):
            return reverse_lazy("caixa:dashboard_financeiro")

        if user.has_perm("caixa.view_orcamento"):
            return reverse_lazy("caixa:orcamentos_lista")

        if user.has_perm("caixa.add_orcamento"):
            return reverse_lazy("caixa:orcamento_adicionar")

        return reverse_lazy("caixa:dashboard_financeiro")


class LogoutSeguroView(LogoutView):
    next_page = reverse_lazy("caixa:login")


class RecuperarSenhaView(PasswordResetView):
    template_name = "caixa/password_reset_form.html"
    email_template_name = "caixa/password_reset_email.html"
    subject_template_name = "caixa/password_reset_subject.txt"
    success_url = reverse_lazy("caixa:password_reset_done")

    def post(self, request, *args, **kwargs):
        if password_reset_rate_limit_exceeded(request):
            return redirect(self.success_url)

        return super().post(request, *args, **kwargs)


class RecuperarSenhaDoneView(PasswordResetDoneView):
    template_name = "caixa/password_reset_done.html"


class RecuperarSenhaConfirmView(PasswordResetConfirmView):
    template_name = "caixa/password_reset_confirm.html"
    success_url = reverse_lazy("caixa:password_reset_complete")


class RecuperarSenhaCompleteView(PasswordResetCompleteView):
    template_name = "caixa/password_reset_complete.html"
