import json
from functools import wraps
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .demo_policy import assert_demo_write_allowed
from .frontend_bridge import legacy_frontend_redirect_required_response
from .models import Evento
from .models_dividas import Credor, DividaFinanceira
from .models_fcf import FinanciamentoMovimentacao
from .permissions import (
    ADD_FINANCIAL_CREDITOR_PERMISSION,
    ADD_FINANCIAL_DEBT_PERMISSION,
    ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION,
    FINANCIAL_CREDITORS_PERMISSION,
    FINANCIAL_DEBT_INSTALLMENTS_PERMISSION,
    PAY_DEBT_INSTALLMENT_PERMISSION,
    api_no_store_json_response,
    api_permission_denied_response,
    require_api_permission,
    require_permission,
)
from .serializers_financiamentos import (
    montar_payload_credores_financiamentos_api,
    montar_payload_financiamentos_api,
    serializar_credor_financiamento,
    serializar_divida_financiamento,
    serializar_movimentacao_financiamento,
    serializar_parcela_financiamento,
)
from .selectors_financiamentos import totais_financiamentos
from .selectors_opcoes_filtros import listar_credores_cadastrados_fcf_filtro
from .utils_request import filtros_texto
from .views_api_auth import csrf_protect_drf_view
from .views_clientes_api import JsonBodySafeSessionAuthentication


FILTROS_FINANCIAMENTOS_CANONICOS = [
    "startDate",
    "endDate",
    "type",
    "status",
    "creditor",
    "creditorId",
    "sourceType",
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


def _bool_payload_value(payload, *keys, default=True):
    value = _first_payload_value(payload, *keys)
    if value in ("", None):
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() not in {
            "0",
            "false",
            "nao",
            "no",
            "inativo",
            "inactive",
        }

    if isinstance(value, (int, float)):
        return bool(value)

    return default


def _decimal_payload_value(payload, *keys, default=None):
    value = _first_payload_value(payload, *keys)
    if value in ("", None):
        return default

    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _date_payload_value(payload, *keys):
    value = _first_payload_value(payload, *keys)
    if value in ("", None):
        return None

    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _positive_integer_payload_value(payload, *keys, default=None):
    value = _first_payload_value(payload, *keys)
    if value in ("", None):
        return default

    try:
        normalized_value = int(value)
    except (TypeError, ValueError):
        return None

    return normalized_value if normalized_value > 0 else None


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


def _truthy_query_value(value):
    return str(value or "").strip().lower() in {"1", "true", "sim", "yes", "all", "todos"}


def _credores_queryset_para_request(request):
    if _truthy_query_value(request.GET.get("includeInactive")):
        return Credor.objects.all().order_by("nome", "id"), False

    return listar_credores_cadastrados_fcf_filtro(), True


def _credor_from_payload(payload, user):
    assert_demo_write_allowed(
        user,
        operation="create_financial_creditor",
    )
    credor = Credor(
        nome=_text_payload_value(payload, "name", "nome"),
        documento=_text_payload_value(payload, "document", "documento") or "",
        ativo=_bool_payload_value(payload, "isActive", "ativo", default=True),
        observacao=_text_payload_value(
            payload,
            "notes",
            "observacao",
            "observation",
        ) or "",
        criado_por=user,
        atualizado_por=user,
    )
    credor.save()
    return credor


def _registered_creditor_from_payload(payload, errors):
    creditor_id = _positive_integer_payload_value(
        payload,
        "creditorId",
        "credor_id",
        "credorCadastroId",
        "credor_cadastro",
    )
    if creditor_id is None:
        errors["creditorId"] = ["Credor invalido."]
        return None

    try:
        return Credor.objects.get(pk=creditor_id)
    except Credor.DoesNotExist:
        errors["creditorId"] = ["Credor nao encontrado."]
        return None


def _api_criar_credor_financiamento(request):
    if not request.user.has_perm(ADD_FINANCIAL_CREDITOR_PERMISSION):
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
        credor = _credor_from_payload(payload, request.user)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "creditor": serializar_credor_financiamento(credor),
                "message": "Credor cadastrado com sucesso.",
            }
        },
        status=201,
        json_dumps_params={"ensure_ascii": False},
    )


def _preservar_metodo_manual_credores_fcf(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method not in {"GET", "POST"}:
            return api_no_store_json_response(
                {"detail": "Metodo nao permitido."},
                status=405,
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def _preservar_metodo_manual_post_divida_fcf(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method != "POST":
            return api_no_store_json_response(
                {"detail": "Metodo nao permitido."},
                status=405,
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def _financial_debt_from_payload(payload, user):
    errors = {}
    creditor = _registered_creditor_from_payload(payload, errors)
    contracted_amount = _decimal_payload_value(
        payload,
        "contractedAmount",
        "valor_contratado",
    )
    monthly_interest_rate = _decimal_payload_value(
        payload,
        "monthlyInterestRate",
        "taxa_juros_mensal",
        default=Decimal("0.0000"),
    )
    installments_count = _positive_integer_payload_value(
        payload,
        "installmentsCount",
        "quantidade_parcelas",
    )
    due_day = _positive_integer_payload_value(
        payload,
        "dueDay",
        "dia_vencimento",
        default=10,
    )
    contracted_date = _date_payload_value(
        payload,
        "contractedDate",
        "data_contratacao",
    )
    event = _event_from_payload(payload, errors)

    if contracted_amount is None:
        errors["contractedAmount"] = ["Valor contratado invalido."]
    if monthly_interest_rate is None:
        errors["monthlyInterestRate"] = ["Taxa de juros mensal invalida."]
    if installments_count is None:
        errors["installmentsCount"] = ["Quantidade de parcelas invalida."]
    if due_day is None:
        errors["dueDay"] = ["Dia de vencimento invalido."]
    if contracted_date is None:
        errors["contractedDate"] = ["Data de contratacao invalida."]

    if errors:
        raise ValidationError(errors)

    assert_demo_write_allowed(
        user,
        event,
        operation="create_financial_debt",
    )
    debt = DividaFinanceira(
        descricao=_text_payload_value(payload, "description", "descricao"),
        credor_cadastro=creditor,
        tipo=_text_payload_value(payload, "type", "tipo"),
        data_contratacao=contracted_date,
        valor_contratado=contracted_amount,
        taxa_juros_mensal=monthly_interest_rate,
        quantidade_parcelas=installments_count,
        dia_vencimento=due_day,
        evento=event,
        observacao=_text_payload_value(payload, "notes", "observacao") or "",
        criado_por=user,
        atualizado_por=user,
    )
    debt.save()
    debt.gerar_parcelas_iniciais()
    return debt


@csrf_protect_drf_view
@require_api_permission(ADD_FINANCIAL_DEBT_PERMISSION)
@_preservar_metodo_manual_post_divida_fcf
@extend_schema(
    methods=["POST"],
    operation_id="fcf_debts_create",
    request=OpenApiTypes.OBJECT,
    responses={201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def api_criar_divida_financeira(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires", "Pragma"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    django_request = getattr(request, "_request", request)

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

    try:
        with transaction.atomic():
            debt = _financial_debt_from_payload(payload, django_request.user)
    except ValidationError as error:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _errors_from_validation_error(error)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    debt = DividaFinanceira.objects.select_related(
        "credor_cadastro",
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).prefetch_related("parcelas").get(pk=debt.pk)
    installments = list(debt.parcelas.order_by("numero_parcela", "id"))
    totais_financiamentos(installments)

    return drf_response_from_json_response(
        api_no_store_json_response(
            {
                "data": {
                    "debt": serializar_divida_financiamento(debt),
                    "divida": serializar_divida_financiamento(debt),
                    "installments": [
                        serializar_parcela_financiamento(installment)
                        for installment in installments
                    ],
                    "parcelas": [
                        serializar_parcela_financiamento(installment)
                        for installment in installments
                    ],
                    "message": "Divida financeira cadastrada com sucesso.",
                }
            },
            status=201,
            json_dumps_params={"ensure_ascii": False},
        )
    )


def _financing_movement_from_payload(payload, user):
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
        event,
        operation="create_financing_movement",
    )
    movement = FinanciamentoMovimentacao(
        descricao=_text_payload_value(payload, "description", "descricao"),
        categoria=_text_payload_value(payload, "category", "categoria"),
        tipo_fluxo=_text_payload_value(payload, "flowType", "tipo_fluxo"),
        valor_previsto=planned_amount,
        valor_realizado=realized_amount,
        data_prevista=planned_date,
        data_realizacao=realized_date,
        evento=event,
        observacao=_text_payload_value(payload, "notes", "observacao") or "",
        criado_por=user,
        atualizado_por=user,
    )
    movement.save()
    return movement


def _api_criar_movimentacao_financiamento(request):
    if not request.user.has_perm(ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION):
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
            movement = _financing_movement_from_payload(payload, request.user)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    movement = FinanciamentoMovimentacao.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
        "divida_financeira",
        "divida_financeira__credor_cadastro",
    ).get(pk=movement.pk)

    return api_no_store_json_response(
        {
            "data": {
                "financingMovement": serializar_movimentacao_financiamento(movement),
                "message": "Movimentacao FCF cadastrada com sucesso.",
            }
        },
        status=201,
        json_dumps_params={"ensure_ascii": False},
    )


@require_permission(FINANCIAL_DEBT_INSTALLMENTS_PERMISSION)
def lista_financiamentos(request):
    return legacy_frontend_redirect_required_response(request, "lista_financiamentos")


@csrf_protect_drf_view
@require_api_permission(FINANCIAL_DEBT_INSTALLMENTS_PERMISSION)
@_preservar_metodo_manual_credores_fcf
@extend_schema(
    methods=["GET"],
    operation_id="fcf_retrieve",
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["POST"],
    operation_id="fcf_create_financing_movement",
    request=OpenApiTypes.OBJECT,
    responses={201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def api_financiamentos(request):
    django_request = getattr(request, "_request", request)

    if request.method == "POST":
        response = _api_criar_movimentacao_financiamento(django_request)
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires", "Pragma"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    payload = montar_payload_financiamentos_api(
        filtros_texto(django_request, FILTROS_FINANCIAMENTOS_CANONICOS),
        django_request.session,
        django_request.user,
    )
    payload["permissions"] = {
        "canCreate": django_request.user.has_perm(ADD_FINANCIAL_DEBT_PERMISSION),
        "canCreateDebt": django_request.user.has_perm(ADD_FINANCIAL_DEBT_PERMISSION),
        "canCreateFinancingMovement": django_request.user.has_perm(
            ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION
        ),
    }
    return Response(payload)


@require_api_permission(FINANCIAL_CREDITORS_PERMISSION)
@_preservar_metodo_manual_credores_fcf
@extend_schema(
    methods=["GET"],
    operation_id="fcf_creditors_retrieve",
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["POST"],
    operation_id="fcf_creditors_create",
    request=OpenApiTypes.OBJECT,
    responses={201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_credores_financiamentos(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    django_request = getattr(request, "_request", request)

    if request.method == "POST":
        return drf_response_from_json_response(
            _api_criar_credor_financiamento(django_request)
        )

    credores, only_active = _credores_queryset_para_request(django_request)
    payload = montar_payload_credores_financiamentos_api(
        credores,
        only_active=only_active,
    )
    payload["permissions"] = {
        "canCreate": request.user.has_perm(ADD_FINANCIAL_CREDITOR_PERMISSION),
    }
    return drf_response_from_json_response(
        JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
    )


@require_permission(PAY_DEBT_INSTALLMENT_PERMISSION)
def pagar_parcela(request, pk):
    return legacy_frontend_redirect_required_response(
        request,
        "pagar_parcela",
        extra_query={"sourceId": pk},
    )
