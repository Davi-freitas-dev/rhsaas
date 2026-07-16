import json
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .frontend_bridge import legacy_frontend_redirect_required_response
from .demo_policy import assert_demo_write_allowed
from .models import Evento
from .models_fci import Investimento
from .permissions import (
    ADD_FINANCIAL_INVESTMENT_PERMISSION,
    CHANGE_FINANCIAL_INVESTMENT_PERMISSION,
    FINANCIAL_INVESTMENTS_PERMISSION,
    api_no_store_json_response,
    api_permission_denied_response,
    require_api_permission,
    require_permission,
)
from .serializers_investimentos import (
    montar_payload_investimentos_api,
    serializar_investimento,
)
from .utils_request import filtros_texto
from .views_api_auth import csrf_protect_drf_view


FILTROS_INVESTIMENTOS_CANONICOS = [
    "startDate",
    "endDate",
    "category",
    "flowType",
    "status",
    "contractCode",
    "eventId",
    "clientId",
    "period",
    "quickPeriod",
]


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


def _text_payload_value(payload, *keys):
    value = _first_payload_value(payload, *keys)
    return value.strip() if isinstance(value, str) else value


def _decimal_payload_value(payload, *keys, default=None):
    value = _first_payload_value(payload, *keys)
    if value in ("", None):
        return default

    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _date_payload_value(payload, *keys, required=False):
    value = _first_payload_value(payload, *keys)
    if value in ("", None):
        return None

    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _event_from_payload(payload, errors):
    event_id = _first_payload_value(payload, "eventId", "evento", "evento_id")
    if event_id in ("", None):
        return None

    try:
        normalized_event_id = int(event_id)
    except (TypeError, ValueError):
        errors["eventId"] = ["Evento invalido."]
        return None

    if normalized_event_id <= 0:
        errors["eventId"] = ["Evento invalido."]
        return None

    try:
        return Evento.objects.get(pk=normalized_event_id)
    except Evento.DoesNotExist:
        errors["eventId"] = ["Evento nao encontrado."]
        return None


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _preservar_405_manual_investimentos(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method not in {"GET", "POST"}:
            return api_no_store_json_response(
                {"detail": "Metodo nao permitido."},
                status=405,
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def _drf_response_from_json_response(response):
    payload = json.loads(response.content.decode(response.charset or "utf-8"))
    drf_response = Response(payload, status=response.status_code)
    for header in ("Cache-Control", "Expires", "Pragma"):
        if header in response:
            drf_response[header] = response[header]
    return drf_response


def _investment_from_payload(payload, user, *, investment=None):
    errors = {}
    planned_amount = _decimal_payload_value(
        payload,
        "plannedAmount",
        "valor_previsto",
    )
    realized_amount = _decimal_payload_value(
        payload,
        "realizedAmount",
        "valor_realizado",
        default=Decimal("0.00"),
    )
    planned_date = _date_payload_value(
        payload,
        "plannedDate",
        "data_prevista",
        required=True,
    )
    realized_date = _date_payload_value(
        payload,
        "realizedDate",
        "data_realizacao",
    )

    if planned_amount is None:
        errors["plannedAmount"] = ["Valor previsto invalido."]
    if realized_amount is None:
        errors["realizedAmount"] = ["Valor realizado invalido."]
    if planned_date is None:
        errors["plannedDate"] = ["Data prevista invalida."]

    event = _event_from_payload(payload, errors)
    if realized_amount and realized_amount > Decimal("0.00") and realized_date is None:
        realized_date = planned_date

    if errors:
        raise ValidationError(errors)

    assert_demo_write_allowed(
        user,
        investment,
        operation=("change_investment" if investment else "create_investment"),
    )
    if event is not None:
        assert_demo_write_allowed(
            user,
            event,
            operation="associate_investment_with_event",
        )

    if investment is None:
        investment = Investimento(criado_por=user)

    investment.descricao = _text_payload_value(payload, "description", "descricao")
    investment.categoria = _text_payload_value(payload, "category", "categoria")
    investment.tipo_fluxo = _text_payload_value(payload, "flowType", "tipo_fluxo")
    investment.valor_previsto = planned_amount
    investment.valor_realizado = realized_amount
    investment.data_prevista = planned_date
    investment.data_realizacao = realized_date
    investment.evento = event
    investment.observacao = _text_payload_value(payload, "notes", "observacao") or ""
    investment.atualizado_por = user
    investment.save()
    return investment


def _api_criar_investimento(request):
    if not request.user.has_perm(ADD_FINANCIAL_INVESTMENT_PERMISSION):
        return api_permission_denied_response()

    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response(
            {"detail": "JSON invalido."},
            status=400,
        )

    try:
        with transaction.atomic():
            investment = _investment_from_payload(payload, request.user)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    investment = Investimento.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).get(pk=investment.pk)

    return api_no_store_json_response(
        {
            "data": {
                "investment": serializar_investimento(investment),
                "message": "Investimento cadastrado com sucesso.",
            }
        },
        status=201,
        json_dumps_params={"ensure_ascii": False},
    )


@require_permission(FINANCIAL_INVESTMENTS_PERMISSION)
def lista_investimentos(request):
    return legacy_frontend_redirect_required_response(request, "lista_investimentos")


@csrf_protect_drf_view
@require_api_permission(FINANCIAL_INVESTMENTS_PERMISSION)
@_preservar_405_manual_investimentos
@extend_schema(
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def api_investimentos(request):
    django_request = getattr(request, "_request", request)

    if request.method == "POST":
        return _drf_response_from_json_response(
            _api_criar_investimento(django_request)
        )

    payload = montar_payload_investimentos_api(
        filtros_texto(django_request, FILTROS_INVESTIMENTOS_CANONICOS),
        django_request.session,
    )
    payload["permissions"] = {
        "canCreate": django_request.user.has_perm(ADD_FINANCIAL_INVESTMENT_PERMISSION),
        "canUpdate": django_request.user.has_perm(
            CHANGE_FINANCIAL_INVESTMENT_PERMISSION
        ),
    }
    return Response(payload)


@csrf_protect_drf_view
@require_api_permission(CHANGE_FINANCIAL_INVESTMENT_PERMISSION)
@extend_schema(
    methods=["PUT"],
    operation_id="fci_investment_update",
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["PUT"])
@permission_classes([AllowAny])
def api_investimento_detalhe(request, pk):
    django_request = getattr(request, "_request", request)
    if not _is_json_request(django_request):
        return _drf_response_from_json_response(
            api_no_store_json_response(
                {"detail": "Content-Type deve ser application/json."},
                status=415,
            )
        )

    payload = _payload_json(django_request)
    if payload is None:
        return _drf_response_from_json_response(
            api_no_store_json_response({"detail": "JSON invalido."}, status=400)
        )

    try:
        with transaction.atomic():
            investment = get_object_or_404(
                Investimento.objects.select_for_update(),
                pk=pk,
            )
            investment = _investment_from_payload(
                payload,
                django_request.user,
                investment=investment,
            )
    except ValidationError as error:
        return _drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _errors_from_validation_error(error)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    investment = Investimento.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).get(pk=investment.pk)
    return _drf_response_from_json_response(
        api_no_store_json_response(
            {
                "data": {
                    "investment": serializar_investimento(investment),
                    "message": "Investimento atualizado com sucesso.",
                }
            },
            status=200,
            json_dumps_params={"ensure_ascii": False},
        )
    )
