import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from tenancy.models import DEMO_SLOT_CODES

from .frontend_bridge import build_next_frontend_url
from .permissions import current_schema_name
from .services_auth import (
    create_password_reset_tenant_context,
    password_reset_rate_limit_exceeded,
    password_reset_tenant_context_is_valid,
    tenant_password_reset_token_generator,
)
from .views_api_auth import csrf_protect_drf_view


logger = logging.getLogger(__name__)
GENERIC_REQUEST_MESSAGE = (
    "Se existir uma conta com esse e-mail, enviaremos as instrucoes de recuperacao."
)
INVALID_LINK_MESSAGE = "Este link de recuperacao e invalido ou expirou."
PASSWORD_RESET_LINK_PARAMETERS = [
    OpenApiParameter("uidb64", str, OpenApiParameter.PATH),
    OpenApiParameter("token", str, OpenApiParameter.PATH),
    OpenApiParameter("context", str, OpenApiParameter.QUERY, required=True),
]


def _payload(request):
    return request.data if isinstance(request.data, dict) else None


def _string_value(payload, key, *, strip=True):
    value = payload.get(key)
    if not isinstance(value, str):
        return ""
    return value.strip() if strip else value


def _audit_password_reset_event(request, action, outcome, *, user=None):
    logger.info(
        "password_reset_event action=%s outcome=%s schema=%s user_id=%s host=%s",
        action,
        outcome,
        current_schema_name(),
        getattr(user, "pk", "") or "",
        request.get_host(),
    )


def _password_reset_user(uidb64):
    user_model = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = user_model._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError, user_model.DoesNotExist):
        return None

    if not user.is_active or not user.has_usable_password():
        return None
    return user


def _valid_password_reset_user(uidb64, token, tenant_context):
    if not password_reset_tenant_context_is_valid(tenant_context):
        return None

    user = _password_reset_user(uidb64)
    if user is None or not tenant_password_reset_token_generator.check_token(user, token):
        return None
    return user


@never_cache
@require_POST
@csrf_protect_drf_view
@sensitive_post_parameters("email")
@extend_schema(
    operation_id="auth_password_reset_request",
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["POST"])
@parser_classes([JSONParser])
@permission_classes([AllowAny])
def api_auth_password_reset_request(request):
    django_request = getattr(request, "_request", request)
    payload = _payload(request)
    if payload is None:
        return Response({"detail": "O corpo deve ser um objeto JSON."}, status=400)

    email = _string_value(payload, "email").lower()
    if password_reset_rate_limit_exceeded(django_request, email=email):
        _audit_password_reset_event(django_request, "request", "rate_limited")
        return Response({"detail": GENERIC_REQUEST_MESSAGE})

    form = PasswordResetForm({"email": email})
    if not form.is_valid():
        return Response({"detail": "Informe um e-mail valido."}, status=400)

    frontend_password_reset_url = build_next_frontend_url("/redefinir-senha")
    if not frontend_password_reset_url:
        logger.error("Password reset indisponivel: NEXT_FRONTEND_URL invalida.")
        return Response(
            {"detail": "A recuperacao de senha esta temporariamente indisponivel."},
            status=503,
        )

    frontend_origin = urlsplit(frontend_password_reset_url)
    schema_name = current_schema_name()
    try:
        form.save(
            domain_override=frontend_origin.netloc,
            use_https=frontend_origin.scheme == "https",
            token_generator=tenant_password_reset_token_generator,
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_template_name="caixa/password_reset_email.html",
            subject_template_name="caixa/password_reset_subject.txt",
            request=django_request,
            extra_email_context={
                "frontend_password_reset_url": frontend_password_reset_url,
                "password_reset_context": create_password_reset_tenant_context(),
                "frontend_demo_tenant": schema_name if schema_name in DEMO_SLOT_CODES else "",
            },
        )
    except Exception:
        logger.exception(
            "Falha ao enviar recuperacao de senha no schema=%s.",
            schema_name,
        )
    _audit_password_reset_event(django_request, "request", "accepted")
    return Response({"detail": GENERIC_REQUEST_MESSAGE})


@never_cache
@csrf_protect_drf_view
@sensitive_post_parameters("newPassword1", "newPassword2")
@extend_schema_view(
    get=extend_schema(
        operation_id="auth_password_reset_validate",
        parameters=PASSWORD_RESET_LINK_PARAMETERS,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    ),
    post=extend_schema(
        operation_id="auth_password_reset_confirm",
        parameters=PASSWORD_RESET_LINK_PARAMETERS,
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    ),
)
@api_view(["GET", "POST"])
@parser_classes([JSONParser])
@permission_classes([AllowAny])
def api_auth_password_reset_confirm(request, uidb64, token):
    django_request = getattr(request, "_request", request)
    tenant_context = request.query_params.get("context", "")
    user = _valid_password_reset_user(uidb64, token, tenant_context)
    if user is None:
        _audit_password_reset_event(django_request, "confirm", "invalid")
        return Response({"detail": INVALID_LINK_MESSAGE}, status=400)

    if request.method == "GET":
        return Response({"valid": True})

    payload = _payload(request)
    if payload is None:
        return Response({"detail": "O corpo deve ser um objeto JSON."}, status=400)

    form = SetPasswordForm(
        user,
        data={
            "new_password1": _string_value(payload, "newPassword1", strip=False),
            "new_password2": _string_value(payload, "newPassword2", strip=False),
        },
    )
    if not form.is_valid():
        errors = {
            field: [str(error) for error in field_errors]
            for field, field_errors in form.errors.items()
        }
        return Response(
            {"detail": "Revise as senhas informadas.", "errors": errors},
            status=400,
        )

    try:
        form.save()
    except ValidationError:
        return Response(
            {"detail": "Nao foi possivel alterar a senha."},
            status=400,
        )

    _audit_password_reset_event(django_request, "confirm", "success", user=user)
    return Response({"passwordReset": True})
