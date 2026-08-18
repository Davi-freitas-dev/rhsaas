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
