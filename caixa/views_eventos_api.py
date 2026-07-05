import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.views.defaults import page_not_found
from django.views.decorators.http import require_GET, require_http_methods
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Cliente, Evento
from .permissions import (
    CHANGE_EVENT_PERMISSION,
    VIEW_EVENT_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
    is_tenant_administrator,
    require_api_permission,
)
from .selectors_cadastros import (
    filtrar_eventos,
    resolver_periodo_eventos_lista,
    status_eventos_para_filtro,
    totais_eventos,
)
from .selectors_opcoes_filtros import listar_clientes_filtro
from .serializers_dimensoes_operacionais import serializar_dimensao_operacional
from .services_dimensoes_operacionais import relacao_carregada
from .utils_financeiros import decimal_zero
from .views_clientes_api import JsonBodySafeSessionAuthentication


EVENT_QUICK_PERIOD_OPTIONS = [
    {"value": "hoje", "label": "Hoje"},
    {"value": "mes_atual", "label": "Este mes"},
    {"value": "30_dias", "label": "Ultimos 30 dias"},
    {"value": "vencidos", "label": "Vencidos"},
    {"value": "todos", "label": "Todos"},
]

EDITABLE_EVENT_FIELDS = [
    "cliente",
    "numero",
    "nome_evento",
    "data_inicio",
    "data_fim",
    "local",
    "status",
    "observacoes",
]


def _money(value):
    return f"{decimal_zero(value):.2f}"


def _date_or_empty(value):
    return value.isoformat() if value else ""


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _choice_options(choices):
    return [{"value": value, "label": label} for value, label in choices]


def _is_json_request(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    return content_type == "application/json"


def _payload_json(request):
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


def _date_payload_value(payload, field_name, *keys, required=False):
    text = _string_payload_value(payload, *keys)

    if not text:
        if required:
            raise ValidationError({field_name: "Informe uma data válida."})
        return None

    value = parse_date(text)
    if value is None:
        raise ValidationError({field_name: "Informe uma data válida."})

    return value


def _integer_payload_value(payload, field_name, *keys, required=False, positive=False):
    text = _string_payload_value(payload, *keys)

    if not text:
        if required:
            raise ValidationError({field_name: "Informe um número válido."})
        return None

    try:
        value = int(text)
    except (TypeError, ValueError) as error:
        raise ValidationError({field_name: "Informe um número válido."}) from error

    if positive and value <= 0:
        raise ValidationError({field_name: "Informe um número maior que zero."})

    return value


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _serialize_cliente_option(cliente):
    return {
        "id": cliente.id,
        "value": str(cliente.id),
        "label": cliente.nome_razao_social,
        "name": cliente.nome_razao_social,
    }


def _eventos_queryset():
    return Evento.objects.select_related("cliente", "orcamento")


def _serialize_evento(evento):
    orcamento = relacao_carregada(evento, "orcamento")
    dimensao = serializar_dimensao_operacional(evento)

    return {
        "id": evento.id,
        "number": evento.numero,
        "contract": evento.contrato,
        "eventName": evento.nome_evento,
        "clientId": evento.cliente_id,
        "clientName": dimensao["clientName"],
        "clientTradeName": dimensao["clientTradeName"],
        "clientDisplayName": dimensao["clientDisplayName"],
        "budgetId": evento.orcamento_id,
        "budgetNumber": orcamento.numero if orcamento else "",
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "startDate": _date_or_empty(evento.data_inicio),
        "endDate": _date_or_empty(evento.data_fim),
        "local": evento.local,
        "status": evento.status,
        "statusLabel": evento.get_status_display(),
        "notes": evento.observacoes,
        "plannedRevenueAmount": _money(evento.valor_total_previsto),
        "realizedRevenueAmount": _money(evento.valor_total_realizado),
        "plannedCostAmount": _money(evento.custo_total_previsto),
        "realizedCostAmount": _money(evento.custo_total_realizado),
        "plannedResultAmount": _money(evento.resultado_financeiro_previsto),
        "realizedResultAmount": _money(evento.resultado_financeiro_realizado),
        "plannedProfitAmount": _money(evento.lucro_previsto),
        "realizedProfitAmount": _money(evento.lucro_realizado),
        "createdAt": _datetime_or_empty(evento.criado_em),
        "updatedAt": _datetime_or_empty(evento.atualizado_em),
    }


def _summary_payload(eventos, totais):
    return {
        "total": eventos.count(),
        "plannedCount": eventos.filter(status="planejado").count(),
        "confirmedCount": eventos.filter(status="confirmado").count(),
        "inProgressCount": eventos.filter(status="em_andamento").count(),
        "completedCount": eventos.filter(status="concluido").count(),
        "cancelledCount": eventos.filter(status="cancelado").count(),
        "plannedRevenueAmount": _money(totais["receita_prevista"]),
        "realizedRevenueAmount": _money(totais["receita_realizada"]),
        "plannedCostAmount": _money(totais["custo_previsto"]),
        "realizedCostAmount": _money(totais["custo_realizado"]),
        "plannedResultAmount": _money(totais["lucro_previsto"]),
        "realizedResultAmount": _money(totais["lucro_realizado"]),
    }


def _eventos_response(request):
    filtros = {
        "busca": (request.GET.get("search") or request.GET.get("busca", "")).strip(),
        "status": request.GET.get("status", "").strip(),
        "cliente": (
            request.GET.get("clientId", "").strip()
            or request.GET.get("cliente", "").strip()
            or request.GET.get("cliente_id", "").strip()
        ),
        "periodo_rapido": (
            request.GET.get("quickPeriod") or request.GET.get("periodo_rapido", "")
        ).strip(),
        "data_inicial": (
            request.GET.get("startDate") or request.GET.get("data_inicial", "")
        ).strip(),
        "data_final": (
            request.GET.get("endDate") or request.GET.get("data_final", "")
        ).strip(),
    }
    filtros = resolver_periodo_eventos_lista(filtros)
    filters_payload = {
        **filtros,
        "search": filtros["busca"],
        "clientId": filtros["cliente"],
        "quickPeriod": filtros["periodo_rapido"],
        "startDate": filtros["data_inicial"],
        "endDate": filtros["data_final"],
    }

    eventos = filtrar_eventos(
        busca=filtros["busca"],
        status=filtros["status"],
        data_inicial=filtros["data_inicial"],
        data_final=filtros["data_final"],
        cliente_id=filtros["cliente"],
        periodo_rapido=filtros["periodo_rapido"],
    ).select_related("cliente", "orcamento")
    totais = totais_eventos(eventos)

    return api_no_store_json_response(
        {
            "data": {
                "events": [_serialize_evento(evento) for evento in eventos],
                "summary": _summary_payload(eventos, totais),
                "filters": filters_payload,
                "filterOptions": {
                    "statuses": _choice_options(status_eventos_para_filtro()),
                    "clients": [
                        _serialize_cliente_option(cliente)
                        for cliente in listar_clientes_filtro()
                    ],
                    "quickPeriods": EVENT_QUICK_PERIOD_OPTIONS,
                },
                "permissions": {
                    "canView": request.user.has_perm(VIEW_EVENT_PERMISSION),
                    "canUpdate": request.user.has_perm(CHANGE_EVENT_PERMISSION),
                    "canManageInAdmin": is_tenant_administrator(request.user),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _json_required_response(request):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON inválido."}, status=400)

    return payload


def _evento_data_from_payload(payload):
    status = _string_payload_value(payload, "status") or "planejado"
    status_values = {value for value, _label in Evento.STATUS_CHOICES}
    if status not in status_values:
        raise ValidationError({"status": "Status inválido."})

    cliente_id = _integer_payload_value(
        payload,
        "clientId",
        "clientId",
        "cliente",
        "cliente_id",
        required=True,
        positive=True,
    )

    return {
        "cliente": Cliente.objects.get(pk=cliente_id),
        "numero": _string_payload_value(payload, "number", "numero", "contract"),
        "nome_evento": _string_payload_value(payload, "eventName", "nome_evento"),
        "data_inicio": _date_payload_value(
            payload,
            "startDate",
            "startDate",
            "data_inicio",
            required=True,
        ),
        "data_fim": _date_payload_value(
            payload,
            "endDate",
            "endDate",
            "data_fim",
            required=True,
        ),
        "local": _string_payload_value(payload, "local"),
        "status": status,
        "observacoes": _string_payload_value(payload, "notes", "observacoes"),
    }


def _atualizar_evento_response(request, evento):
    payload = _json_required_response(request)
    if not isinstance(payload, dict):
        return payload

    try:
        evento_data = _evento_data_from_payload(payload)
        for field, value in evento_data.items():
            setattr(evento, field, value)

        evento.full_clean()
        evento.save(update_fields=[*EDITABLE_EVENT_FIELDS, "atualizado_em"])
        evento = _eventos_queryset().get(pk=evento.pk)
    except Cliente.DoesNotExist:
        return api_no_store_json_response(
            {"errors": {"clientId": ["Cliente não encontrado."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"number": ["Já existe um evento com este contrato."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "event": _serialize_evento(evento),
                "message": "Evento atualizado com sucesso.",
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_eventos(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(VIEW_EVENT_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    return drf_response_from_json_response(_eventos_response(request))


@extend_schema(
    methods=["GET"],
    operation_id="eventos_detalhe_retrieve",
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="eventos_detalhe_update",
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@require_http_methods(["GET", "PUT"])
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_evento_detalhe(request, pk):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    def django_not_found_response():
        django_request = getattr(request, "_request", request)
        exception = Http404("No Evento matches the given query.")
        return page_not_found(django_request, exception)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_EVENT_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        try:
            evento = get_object_or_404(_eventos_queryset(), pk=pk)
        except Http404:
            return django_not_found_response()

        return drf_response_from_json_response(
            api_no_store_json_response(
                {
                    "data": {
                        "event": _serialize_evento(evento),
                        "permissions": {
                            "canView": request.user.has_perm(VIEW_EVENT_PERMISSION),
                            "canUpdate": request.user.has_perm(CHANGE_EVENT_PERMISSION),
                            "canManageInAdmin": is_tenant_administrator(request.user),
                        },
                        "meta": {"source": "backend"},
                    }
                },
                json_dumps_params={"ensure_ascii": False},
            )
        )

    if not request.user.has_perm(CHANGE_EVENT_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        evento = get_object_or_404(_eventos_queryset(), pk=pk)
    except Http404:
        return django_not_found_response()

    return drf_response_from_json_response(_atualizar_evento_response(request, evento))
