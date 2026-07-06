import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.defaults import page_not_found
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .models import ConfiguracaoFinanceira
from .permissions import (
    ADD_FINANCIAL_CONFIGURATION_PERMISSION,
    CHANGE_FINANCIAL_CONFIGURATION_PERMISSION,
    VIEW_FINANCIAL_CONFIGURATION_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .utils_financeiros import quantizar_moeda
from .views_clientes_api import JsonBodySafeSessionAuthentication


def _is_json_request(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    return content_type == "application/json"


def _payload_json(request):
    if isinstance(request, Request):
        try:
            payload = request.data
        except ParseError:
            return None

        return payload if isinstance(payload, dict) else None

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _first_payload_value(payload, *keys, default=""):
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return default


def _string_payload_value(payload, *keys, default=""):
    value = _first_payload_value(payload, *keys, default=default)
    return str(value).strip() if value is not None else ""


def _boolean_payload_value(payload, *keys, default=True):
    value = _first_payload_value(payload, *keys, default=default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "nao", "não", "no"}

    return bool(value)


def _decimal_payload_value(payload, field_name, *keys, default="0.00"):
    value = _first_payload_value(payload, *keys, default=default)
    text = str(value).strip().replace(" ", "")

    if not text:
        text = str(default)

    try:
        return Decimal(text.replace(",", "."))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError({field_name: "Informe um valor numerico valido."}) from error


def _date_payload_value(payload, field_name, *keys):
    value = _first_payload_value(payload, *keys, default="")
    text = str(value).strip()

    if not text:
        raise ValidationError({field_name: "Informe uma data valida."})

    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValidationError({field_name: "Informe uma data valida."}) from error


def _money(value):
    return f"{quantizar_moeda(value):.2f}"


def _date_or_empty(value):
    return value.isoformat() if value else ""


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _normalizar_filtro_booleano(value):
    value = (value or "").strip().lower()
    return value if value in {"sim", "nao"} else "all"


def _serialize_configuracao(configuracao):
    return {
        "id": configuracao.id,
        "name": configuracao.nome,
        "displayName": str(configuracao),
        "mealAmount": _money(configuracao.valor_alimentacao),
        "transportAmount": _money(configuracao.valor_transporte),
        "profitMargin": _money(configuracao.margem_lucro),
        "taxRate": _money(configuracao.aliquota_imposto),
        "isActive": configuracao.ativa,
        "effectiveDate": _date_or_empty(configuracao.data_inicio_vigencia),
        "notes": configuracao.observacao,
        "createdAt": _datetime_or_empty(configuracao.criado_em),
        "updatedAt": _datetime_or_empty(configuracao.atualizado_em),
    }


def _configuracao_data_from_payload(payload):
    return {
        "nome": _string_payload_value(payload, "name", "nome") or "Padrao",
        "valor_alimentacao": _decimal_payload_value(
            payload,
            "valor_alimentacao",
            "mealAmount",
            "valor_alimentacao",
        ),
        "valor_transporte": _decimal_payload_value(
            payload,
            "valor_transporte",
            "transportAmount",
            "valor_transporte",
        ),
        "margem_lucro": _decimal_payload_value(
            payload,
            "margem_lucro",
            "profitMargin",
            "margem_lucro",
            default="0.30",
        ),
        "aliquota_imposto": _decimal_payload_value(
            payload,
            "aliquota_imposto",
            "taxRate",
            "aliquota_imposto",
            default="0.06",
        ),
        "data_inicio_vigencia": _date_payload_value(
            payload,
            "data_inicio_vigencia",
            "effectiveDate",
            "data_inicio_vigencia",
        ),
        "ativa": _boolean_payload_value(payload, "isActive", "ativa", default=True),
        "observacao": _string_payload_value(payload, "notes", "observacao"),
    }


def _configuracoes_filtradas(request):
    search = (request.GET.get("search") or "").strip()
    active = _normalizar_filtro_booleano(request.GET.get("active", "all"))

    configuracoes = ConfiguracaoFinanceira.objects.all().order_by(
        "-ativa",
        "-data_inicio_vigencia",
        "-id",
    )

    if search:
        configuracoes = configuracoes.filter(
            Q(nome__icontains=search) | Q(observacao__icontains=search)
        )

    if active == "sim":
        configuracoes = configuracoes.filter(ativa=True)
    elif active == "nao":
        configuracoes = configuracoes.filter(ativa=False)

    filters = {
        "search": search,
        "active": active,
    }

    return configuracoes, filters


def _configuracoes_response(request):
    configuracoes, filters = _configuracoes_filtradas(request)

    return api_no_store_json_response(
        {
            "data": {
                "configurations": [
                    _serialize_configuracao(configuracao)
                    for configuracao in configuracoes
                ],
                "summary": {
                    "total": configuracoes.count(),
                    "active": configuracoes.filter(ativa=True).count(),
                    "inactive": configuracoes.filter(ativa=False).count(),
                },
                "filters": filters,
                "filterOptions": {
                    "activeStatuses": [
                        {"value": "sim", "label": "Ativa"},
                        {"value": "nao", "label": "Inativa"},
                    ],
                },
                "permissions": {
                    "canCreate": request.user.has_perm(
                        ADD_FINANCIAL_CONFIGURATION_PERMISSION
                    ),
                    "canUpdate": request.user.has_perm(
                        CHANGE_FINANCIAL_CONFIGURATION_PERMISSION
                    ),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _salvar_configuracao_response(configuracao, *, status=200, success_message):
    try:
        with transaction.atomic():
            if configuracao.ativa:
                ConfiguracaoFinanceira.objects.filter(ativa=True).exclude(
                    pk=configuracao.pk
                ).update(ativa=False)

            configuracao.full_clean()
            configuracao.save()
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {
                "errors": {
                    "detail": [
                        "Nao foi possivel salvar a configuracao financeira."
                    ]
                }
            },
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "configuration": _serialize_configuracao(configuracao),
                "message": success_message,
            }
        },
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def _criar_configuracao_response(request):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    try:
        configuracao = ConfiguracaoFinanceira(**_configuracao_data_from_payload(payload))
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return _salvar_configuracao_response(
        configuracao,
        status=201,
        success_message="Configuracao financeira cadastrada com sucesso.",
    )


def _configuracao_detalhe_response(request, configuracao):
    return api_no_store_json_response(
        {
            "data": {
                "configuration": _serialize_configuracao(configuracao),
                "permissions": {
                    "canUpdate": request.user.has_perm(
                        CHANGE_FINANCIAL_CONFIGURATION_PERMISSION
                    ),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _atualizar_configuracao_response(request, configuracao):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    try:
        for field, value in _configuracao_data_from_payload(payload).items():
            setattr(configuracao, field, value)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return _salvar_configuracao_response(
        configuracao,
        success_message="Configuracao financeira atualizada com sucesso.",
    )


def _drf_response_from_json_response(response):
    payload = json.loads(response.content.decode(response.charset or "utf-8"))
    drf_response = Response(payload, status=response.status_code)
    for header_name in ("Cache-Control", "Expires"):
        if header_name in response:
            drf_response[header_name] = response[header_name]
    return drf_response


def _django_not_found_response(request):
    django_request = request._request if isinstance(request, Request) else request
    exception = Http404("No ConfiguracaoFinanceira matches the given query.")
    return page_not_found(django_request, exception)


@never_cache
@extend_schema(methods=["GET"], responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@extend_schema(
    methods=["POST"],
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_configuracoes_financeiras(request):
    if not request.user.is_authenticated:
        return _drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_FINANCIAL_CONFIGURATION_PERMISSION):
            return _drf_response_from_json_response(api_permission_denied_response())

        return _drf_response_from_json_response(_configuracoes_response(request))

    if not request.user.has_perm(ADD_FINANCIAL_CONFIGURATION_PERMISSION):
        return _drf_response_from_json_response(api_permission_denied_response())

    return _drf_response_from_json_response(_criar_configuracao_response(request))


@extend_schema(
    methods=["GET"],
    operation_id="configuracoes_financeiras_detalhe_retrieve",
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="configuracoes_financeiras_detalhe_update",
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_configuracao_financeira_detalhe(request, pk):
    if not request.user.is_authenticated:
        return _drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_FINANCIAL_CONFIGURATION_PERMISSION):
            return _drf_response_from_json_response(api_permission_denied_response())

        try:
            configuracao = get_object_or_404(ConfiguracaoFinanceira, pk=pk)
        except Http404:
            return _django_not_found_response(request)

        return _drf_response_from_json_response(
            _configuracao_detalhe_response(request, configuracao)
        )

    if not request.user.has_perm(CHANGE_FINANCIAL_CONFIGURATION_PERMISSION):
        return _drf_response_from_json_response(api_permission_denied_response())

    try:
        configuracao = get_object_or_404(ConfiguracaoFinanceira, pk=pk)
    except Http404:
        return _django_not_found_response(request)

    return _drf_response_from_json_response(
        _atualizar_configuracao_response(request, configuracao)
    )
