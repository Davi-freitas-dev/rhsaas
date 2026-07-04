import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.defaults import page_not_found
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import DespesaOperacional
from .permissions import (
    CHANGE_EXPENSE_PERMISSION,
    VIEW_EXPENSE_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .serializers_dimensoes_operacionais import serializar_dimensao_operacional
from .utils_financeiros import decimal_zero
from .views_clientes_api import JsonBodySafeSessionAuthentication


def _is_json_request(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    return content_type == "application/json"


def _payload_json(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _payload_has_any(payload, *keys):
    return any(key in payload for key in keys)


def _first_payload_value(payload, *keys, default=""):
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return default


def _string_payload_value(payload, *keys, default=""):
    value = _first_payload_value(payload, *keys, default=default)
    return str(value).strip() if value is not None else ""


def _decimal_payload_value(payload, field_name, *keys, required=False):
    value = _first_payload_value(payload, *keys, default="")
    text = str(value).strip().replace(" ", "")

    if not text:
        if required:
            raise ValidationError({field_name: "Informe um valor valido."})
        return Decimal("0.00")

    try:
        number = Decimal(text.replace(",", "."))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError({field_name: "Informe um valor numerico valido."}) from error

    if number < Decimal("0.00"):
        raise ValidationError({field_name: "Informe um valor maior ou igual a zero."})

    return number


def _optional_decimal_payload_value(payload, field_name, *keys):
    if not _payload_has_any(payload, *keys):
        return None

    value = _first_payload_value(payload, *keys, default="")
    if str(value).strip() == "":
        return None

    return _decimal_payload_value(payload, field_name, *keys, required=True)


def _boolean_payload_value(payload, field_name, *keys, default=False):
    if not _payload_has_any(payload, *keys):
        return default

    value = _first_payload_value(payload, *keys, default=default)

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    text = str(value).strip().lower()
    if text in {"1", "true", "sim", "s", "yes", "on"}:
        return True

    if text in {"0", "false", "nao", "n", "no", "off", ""}:
        return False

    raise ValidationError({field_name: "Informe verdadeiro ou falso."})


def _date_payload_value(payload, field_name, *keys):
    text = _string_payload_value(payload, *keys)

    if not text:
        return None

    value = parse_date(text)
    if value is None:
        raise ValidationError({field_name: "Informe uma data valida."})

    return value


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _money(value):
    return f"{decimal_zero(value):.2f}"


def _date_or_empty(value):
    return value.isoformat() if value else ""


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _despesas_queryset():
    return DespesaOperacional.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).filter(origem=DespesaOperacional.ORIGEM_MANUAL)


def _serialize_despesa(despesa):
    dimensao = serializar_dimensao_operacional(despesa)

    return {
        "id": despesa.id,
        "description": despesa.descricao,
        "category": despesa.categoria,
        "categoryLabel": despesa.get_categoria_display(),
        "plannedAmount": _money(despesa.valor_previsto),
        "paidAmount": _money(despesa.valor_pago),
        "pendingPaymentAmount": _money(despesa.valor_pendente_pagamento),
        "dueDate": _date_or_empty(despesa.data_vencimento),
        "paymentDate": _date_or_empty(despesa.data_pagamento),
        "status": despesa.status,
        "statusLabel": despesa.get_status_display(),
        "paymentMethod": despesa.forma_pagamento,
        "manuallySettled": despesa.baixado_manualmente,
        "settlementReason": despesa.motivo_baixa,
        "notes": despesa.observacao,
        "eventId": despesa.evento_id,
        "eventLabel": dimensao["eventName"],
        "eventNumber": dimensao["eventNumber"],
        "clientId": dimensao["clientId"],
        "clientName": dimensao["clientName"],
        "contractCode": dimensao["contractCode"],
        "contractLabel": dimensao["contractLabel"],
        "createdAt": _datetime_or_empty(despesa.criado_em),
        "updatedAt": _datetime_or_empty(despesa.atualizado_em),
    }


def _json_required_response(request):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    return payload


def _atualizar_despesa_data(despesa, payload):
    valor_previsto = _optional_decimal_payload_value(
        payload,
        "plannedAmount",
        "plannedAmount",
        "valor_previsto",
    )
    if valor_previsto is None:
        valor_previsto = decimal_zero(despesa.valor_previsto)

    pago = _boolean_payload_value(
        payload,
        "paid",
        "paid",
        "pago",
        default=despesa.status == "pago",
    )

    despesa.valor_previsto = valor_previsto

    if pago:
        valor_pago = _optional_decimal_payload_value(
            payload,
            "paidAmount",
            "paidAmount",
            "valor_pago",
        )
        despesa.valor_pago = valor_pago if valor_pago is not None else valor_previsto
        despesa.data_pagamento = (
            _date_payload_value(payload, "paymentDate", "paymentDate", "data_pagamento")
            or despesa.data_pagamento
            or timezone.localdate()
        )
        despesa.status = "pendente"
    else:
        despesa.valor_pago = Decimal("0.00")
        despesa.data_pagamento = None
        despesa.status = "pendente"
        despesa.forma_pagamento = ""
        despesa.baixado_manualmente = False
        despesa.motivo_baixa = ""

    despesa.observacao = _string_payload_value(
        payload,
        "notes",
        "observacao",
        default=despesa.observacao,
    )
    return despesa


def _despesa_detalhe_response(request, despesa):
    return api_no_store_json_response(
        {
            "data": {
                "expense": _serialize_despesa(despesa),
                "permissions": {
                    "canView": request.user.has_perm(VIEW_EXPENSE_PERMISSION),
                    "canUpdate": request.user.has_perm(CHANGE_EXPENSE_PERMISSION),
                    "canManageInAdmin": request.user.is_superuser,
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _atualizar_despesa_response(request, despesa):
    payload = _json_required_response(request)
    if not isinstance(payload, dict):
        return payload

    try:
        _atualizar_despesa_data(despesa, payload)
        despesa.atualizado_por = request.user
        despesa.full_clean()
        despesa.save()
        despesa = _despesas_queryset().get(pk=despesa.pk)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"detail": ["Nao foi possivel atualizar a despesa."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "expense": _serialize_despesa(despesa),
                "message": "Despesa atualizada com sucesso.",
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_http_methods(["GET", "PUT"])
@csrf_protect
@extend_schema(
    methods=["GET"],
    operation_id="despesas_detalhe_retrieve",
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="despesas_detalhe_update",
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_despesa_detalhe(request, pk):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    def django_not_found_response(error):
        django_request = getattr(request, "_request", request)
        return page_not_found(django_request, error)

    django_request = getattr(request, "_request", request)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_EXPENSE_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        try:
            despesa = get_object_or_404(_despesas_queryset(), pk=pk)
        except Http404 as error:
            return django_not_found_response(error)

        return drf_response_from_json_response(
            _despesa_detalhe_response(django_request, despesa)
        )

    if not request.user.has_perm(CHANGE_EXPENSE_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        despesa = get_object_or_404(_despesas_queryset(), pk=pk)
    except Http404 as error:
        return django_not_found_response(error)

    return drf_response_from_json_response(
        _atualizar_despesa_response(django_request, despesa)
    )


# Preserve Django's CSRF 403 HTML contract for missing/invalid PUT tokens.
api_despesa_detalhe.csrf_exempt = False
