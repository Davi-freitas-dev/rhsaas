from django.urls import path

from caixa.views_api_auth import api_auth_csrf
from caixa.views_api_password_reset import (
    api_auth_password_reset_gateway_confirm,
    api_auth_password_reset_gateway_validate,
)
from tenancy.views_demo_public import api_demo_lease, api_demo_status, api_health


urlpatterns = [
    path("api/health/", api_health, name="api_health"),
    path("api/auth/csrf/", api_auth_csrf, name="public_api_auth_csrf"),
    path(
        "api/auth/password-reset/gateway/validate/",
        api_auth_password_reset_gateway_validate,
        name="public_api_auth_password_reset_gateway_validate",
    ),
    path(
        "api/auth/password-reset/gateway/confirm/",
        api_auth_password_reset_gateway_confirm,
        name="public_api_auth_password_reset_gateway_confirm",
    ),
    path("api/demo/lease/", api_demo_lease, name="api_demo_lease"),
    path("api/demo/status/", api_demo_status, name="api_demo_status"),
]
