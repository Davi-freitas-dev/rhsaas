import logging

from django.conf import settings
from django.contrib.auth import login
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_tenants.utils import get_public_schema_name

from caixa.throttling import DemoExchangeRateThrottle, DemoLeaseRateThrottle
from caixa.views_api_auth import (
    _json_payload,
    _user_payload,
    csrf_protect_drf_view,
)
from config.client_ip import get_axes_client_ip

from .demo_visitor import (
    DEMO_VISITOR_COOKIE_NAME,
    DEMO_VISITOR_COOKIE_SALT,
    get_or_create_demo_visitor_identifier,
    is_demo_lease_resume_only,
)

from .services_demo_pool import (
    DemoAccessTokenInvalid,
    DemoLeaseResumeUnavailable,
    DemoNetworkLimitExceeded,
    DemoPoolFull,
    DemoPoolUnavailable,
    allocate_demo_lease,
    consume_demo_exchange_token,
)


logger = logging.getLogger(__name__)


def _iso_datetime(value):
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.isoformat()


def _json_request_payload(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    if content_type != "application/json":
        return None, Response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _json_payload(request)
    if payload is None:
        return None, Response({"detail": "JSON invalido."}, status=400)
    return payload, None


def _visitor_identifier(request):
    return get_or_create_demo_visitor_identifier(request)


def _network_identifier(request, visitor_identifier):
    return get_axes_client_ip(request) or f"visitor:{visitor_identifier}"


def _set_visitor_cookie(response, visitor_identifier):
    response.set_signed_cookie(
        DEMO_VISITOR_COOKIE_NAME,
        visitor_identifier,
        salt=DEMO_VISITOR_COOKIE_SALT,
        max_age=settings.DEMO_VISITOR_COOKIE_MAX_AGE,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )


@require_POST
@sensitive_post_parameters()
@sensitive_variables("grant")
@never_cache
@extend_schema(request=OpenApiTypes.OBJECT, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@parser_classes([JSONParser])
@throttle_classes([DemoLeaseRateThrottle])
@permission_classes([AllowAny])
def api_demo_lease(request):
    django_request = getattr(request, "_request", request)
    allowed_entry_schemas = {
        get_public_schema_name(),
        settings.DEMO_PUBLIC_ENTRY_SCHEMA,
    }
    if getattr(connection, "schema_name", "") not in allowed_entry_schemas:
        return Response({"detail": "Nao encontrado."}, status=404)

    payload, error_response = _json_request_payload(django_request)
    if error_response is not None:
        return error_response
    if payload:
        return Response({"detail": "Este endpoint nao aceita campos."}, status=400)

    visitor_identifier = _visitor_identifier(django_request)
    network_identifier = _network_identifier(django_request, visitor_identifier)
    try:
        grant = allocate_demo_lease(
            visitor_identifier=visitor_identifier,
            network_identifier=network_identifier,
            resume_only=is_demo_lease_resume_only(django_request),
        )
    except DemoLeaseResumeUnavailable:
        logger.info("demo_lease outcome=resume_unavailable")
        return Response(
            {
                "code": "resume_unavailable",
                "detail": "O acesso temporario expirou. Solicite uma nova vaga.",
            },
            status=409,
        )
    except DemoNetworkLimitExceeded:
        logger.info("demo_lease outcome=network_limit")
        return Response(
            {
                "code": "network_limit",
                "detail": "Esta rede já possui acessos temporários ativos.",
            },
            status=429,
        )
    except DemoPoolFull:
        logger.info("demo_lease outcome=pool_full")
        return Response(
            {
                "code": "pool_full",
                "detail": "Todas as vagas da demo estao em uso. Tente novamente mais tarde.",
            },
            status=503,
        )
    except DemoPoolUnavailable:
        logger.warning("demo_lease outcome=disabled_or_inconsistent")
        return Response(
            {
                "code": "unavailable",
                "detail": "A demo esta temporariamente indisponivel.",
            },
            status=503,
        )
    except ImproperlyConfigured:
        logger.exception("demo_lease outcome=misconfigured")
        return Response(
            {
                "code": "unavailable",
                "detail": "A demo esta temporariamente indisponivel.",
            },
            status=503,
        )

    response = Response(
        {
            "apiBaseUrl": grant.api_base_url,
            "exchangeToken": grant.exchange_token,
            "expiresAt": _iso_datetime(grant.expires_at),
            "reused": grant.reused,
        },
        status=201,
    )
    _set_visitor_cookie(response, visitor_identifier)
    logger.info("demo_lease outcome=granted reused=%s", grant.reused)
    return response


@require_POST
@csrf_protect_drf_view
@sensitive_post_parameters("exchangeToken")
@sensitive_variables("raw_token")
@never_cache
@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
@api_view(["POST"])
@parser_classes([JSONParser])
@throttle_classes([DemoExchangeRateThrottle])
@permission_classes([AllowAny])
def api_demo_exchange(request):
    django_request = getattr(request, "_request", request)
    payload, error_response = _json_request_payload(django_request)
    if error_response is not None:
        return error_response
    if set(payload) != {"exchangeToken"}:
        return Response({"detail": "Payload de troca invalido."}, status=400)

    raw_token = payload.get("exchangeToken")
    schema_name = getattr(connection, "schema_name", "")
    try:
        user, expires_at = consume_demo_exchange_token(
            schema_name=schema_name,
            raw_token=raw_token,
        )
    except DemoAccessTokenInvalid:
        logger.info("demo_exchange outcome=rejected schema=%s", schema_name)
        return Response(
            {"detail": "Acesso temporario invalido ou expirado."},
            status=401,
        )

    login(
        django_request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    remaining_seconds = max(
        1,
        int((expires_at - timezone.now()).total_seconds()),
    )
    django_request.session.set_expiry(remaining_seconds)
    logger.info("demo_exchange outcome=success schema=%s", schema_name)
    return Response(
        {
            "authenticated": True,
            "user": _user_payload(user),
            "csrfToken": get_token(django_request),
            "expiresAt": _iso_datetime(expires_at),
        }
    )


@never_cache
@extend_schema(responses={200: OpenApiTypes.OBJECT})
@api_view(["GET"])
@permission_classes([AllowAny])
def api_health(request):
    return Response(
        {
            "status": "ok",
            "demoEntryEnabled": bool(settings.DEMO_PUBLIC_LEASE_ENABLED),
        }
    )
