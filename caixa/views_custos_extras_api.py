import json

from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .forms_custos_extras import EventoCustoExtraForm
from .models_custos_extras import EventoCustoExtra
from .permissions import (
    ADD_EVENT_EXTRA_COST_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .serializers_dimensoes_operacionais import serializar_dimensao_operacional
from .services_cadastros import criar_custo_extra
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


def _first_payload_value(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return ""


def _form_data_from_payload(payload):
    return {
        "evento": _first_payload_value(payload, "eventId", "evento", "evento_id"),
        "categoria": _first_payload_value(payload, "category", "categoria"),
        "descricao": _first_payload_value(payload, "description", "descricao"),
        "valor_previsto": _first_payload_value(
            payload,
            "plannedAmount",
            "valor_previsto",
        ),
        "valor_pago": "0.00",
        "data_vencimento": _first_payload_value(
            payload,
            "dueDate",
            "data_vencimento",
        ),
        "observacao": _first_payload_value(payload, "notes", "observacao"),
    }


def _errors_from_form(form):
    return {
        field: [message for error in errors for message in error.messages]
        for field, errors in form.errors.as_data().items()
    }


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _money(value):
    return f"{value:.2f}"


def _date_or_empty(value):
    return value.isoformat() if value else ""


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _serialize_event_extra_cost(custo_extra):
    dimensao = serializar_dimensao_operacional(custo_extra)

    return {
        "id": custo_extra.id,
        "eventId": dimensao["eventId"],
        "eventNumber": dimensao["eventNumber"],
        "eventName": dimensao["eventName"],
        "eventLabel": dimensao["eventLabel"],
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "contractLabel": dimensao["contractLabel"],
        "clientId": dimensao["clientId"],
        "clientName": dimensao["clientName"],
        "category": custo_extra.categoria,
        "categoryLabel": custo_extra.get_categoria_display(),
        "description": custo_extra.descricao,
        "plannedAmount": _money(custo_extra.valor_previsto),
        "paidAmount": _money(custo_extra.valor_pago),
        "pendingPaymentAmount": _money(custo_extra.valor_pendente_pagamento),
        "dueDate": _date_or_empty(custo_extra.data_vencimento),
        "notes": custo_extra.observacao,
        "createdAt": _datetime_or_empty(custo_extra.criado_em),
        "updatedAt": _datetime_or_empty(custo_extra.atualizado_em),
    }


@require_POST
@extend_schema(
    methods=["POST"],
    operation_id="eventos_custos_extras_create",
    request=OpenApiTypes.OBJECT,
    responses={201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_criar_custo_extra_evento(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    django_request = getattr(request, "_request", request)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(ADD_EVENT_EXTRA_COST_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    if not _is_json_request(django_request):
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"detail": "Content-Type deve ser application/json."},
                status=415,
            )
        )

    payload = _payload_json(django_request)
    if payload is None:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"detail": "JSON invalido."},
                status=400,
            )
        )

    form = EventoCustoExtraForm(_form_data_from_payload(payload))
    if not form.is_valid():
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _errors_from_form(form)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    try:
        custo_extra = criar_custo_extra(form, request.user)
    except ValidationError as error:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _errors_from_validation_error(error)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    custo_extra = EventoCustoExtra.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).get(pk=custo_extra.pk)

    return drf_response_from_json_response(
        api_no_store_json_response(
            {
                "data": {
                    "extraCost": _serialize_event_extra_cost(custo_extra),
                    "message": "Custo extra cadastrado com sucesso.",
                }
            },
            status=201,
            json_dumps_params={"ensure_ascii": False},
        )
    )
