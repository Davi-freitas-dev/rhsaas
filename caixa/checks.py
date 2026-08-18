import math

from django.conf import settings
from django.core.checks import Error, Tags, register

from .frontend_bridge import frontend_origin_error


@register(Tags.security, deploy=True)
def check_next_frontend_origin(app_configs, **kwargs):
    error = frontend_origin_error(
        getattr(settings, "NEXT_FRONTEND_URL", ""),
        require_https=True,
    )
    if error is None:
        return []

    return [
        Error(
            error,
            hint=(
                "Configure NEXT_FRONTEND_URL com a origem HTTPS oficial, por exemplo "
                "https://app.rhsaas.example.com."
            ),
            id="caixa.E001",
        )
    ]


@register(Tags.security, deploy=True)
def check_password_reset_security_settings(app_configs, **kwargs):
    errors = []
    if not str(getattr(settings, "PASSWORD_RESET_GATEWAY_SCHEMA", "") or "").strip():
        errors.append(
            Error(
                "PASSWORD_RESET_GATEWAY_SCHEMA nao pode ficar vazio.",
                hint="Use o schema servido pelo host canonico da API do frontend.",
                id="caixa.E002",
            )
        )
    timing_settings = (
        (
            "PASSWORD_RESET_MIN_RESPONSE_SECONDS",
            "PASSWORD_RESET_MIN_RESPONSE_MAX_SECONDS",
            "caixa.E003",
        ),
        (
            "PASSWORD_RESET_RESPONSE_JITTER_SECONDS",
            "PASSWORD_RESET_JITTER_MAX_SECONDS",
            "caixa.E004",
        ),
    )
    for setting_name, max_setting_name, error_id in timing_settings:
        value = float(getattr(settings, setting_name, 0))
        maximum = float(getattr(settings, max_setting_name))
        if (
            not math.isfinite(value)
            or not math.isfinite(maximum)
            or maximum < 0
            or value < 0
            or value > maximum
        ):
            errors.append(
                Error(
                    f"{setting_name} deve ficar entre 0 e {maximum} segundos.",
                    id=error_id,
                )
            )
    if getattr(settings, "PASSWORD_RESET_E2E_ENABLED", False) and not settings.DEBUG:
        errors.append(
            Error(
                "PASSWORD_RESET_E2E_ENABLED nao pode ser ativado fora de DEBUG.",
                id="caixa.E005",
            )
        )
    return errors
