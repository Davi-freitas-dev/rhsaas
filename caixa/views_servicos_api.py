import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError
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

from .models import Servico
from .permissions import (
    ADD_SERVICE_PERMISSION,
    CHANGE_SERVICE_PERMISSION,
    VIEW_SERVICE_PERMISSION,
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
        if key in payload:
            return payload.get(key)
    return default


def _payload_has_any(payload, *keys):
    return any(key in payload for key in keys)


def _string_payload_value(payload, *keys, default=""):
    value = _first_payload_value(payload, *keys, default=default)
    return str(value).strip() if value is not None else ""


def _boolean_payload_value(payload, *keys, default=False):
    value = _first_payload_value(payload, *keys, default=default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "nao", "no"}

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


def _billing_unit_payload_value(payload, field_name, *keys):
    unidade = _string_payload_value(
        payload,
        *keys,
        default=Servico.UNIDADE_COBRANCA_DIARIA,
    ).lower()
    unidades_validas = {
        Servico.UNIDADE_COBRANCA_DIARIA,
        Servico.UNIDADE_COBRANCA_HORA,
    }
    if unidade not in unidades_validas:
        raise ValidationError({field_name: "Informe diaria ou hora."})
    return unidade


def _integer_payload_value(payload, field_name, *keys, default=0):
    value = _first_payload_value(payload, *keys, default=default)
    text = str(value).strip()

    if not text:
        text = str(default)

    try:
        return int(text)
    except (TypeError, ValueError) as error:
        raise ValidationError({field_name: "Informe um numero inteiro valido."}) from error


def _money(value):
    return f"{quantizar_moeda(value):.2f}"


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _normalizar_filtro_booleano(value):
    value = (value or "").strip().lower()
    return value if value in {"sim", "nao"} else "all"


def _serialize_servico(servico):
    return {
        "id": servico.id,
        "name": servico.nome,
        "code": servico.codigo,
        "billingUnit": servico.unidade_cobranca,
        "unitRate": _money(servico.valor_unitario),
        "dailyRate": _money(servico.diaria_padrao),
        "baseHours": servico.horas_base_diaria,
        "overtimePercent": f"{servico.percentual_hora_extra:.2f}",
        "usesSpecialRule": servico.usa_regra_especial,
        "isActive": servico.ativo,
        "halfDailyRate": _money(servico.meia_diaria),
        "normalHourlyRate": _money(servico.valor_hora_normal),
        "overtimeHourlyRate": _money(servico.valor_hora_extra),
        "createdAt": _datetime_or_empty(servico.criado_em),
        "updatedAt": _datetime_or_empty(servico.atualizado_em),
    }


def _servico_create_data_from_payload(payload):
    unidade_cobranca = _billing_unit_payload_value(
        payload,
        "unidade_cobranca",
        "billingUnit",
        "unidade_cobranca",
    )
    has_unit_rate = _payload_has_any(payload, "unitRate", "valor_unitario")
    has_daily_rate = _payload_has_any(payload, "dailyRate", "diaria_padrao")

    if has_unit_rate:
        valor_unitario = _decimal_payload_value(
            payload,
            "valor_unitario",
            "unitRate",
            "valor_unitario",
        )
    elif has_daily_rate:
        valor_unitario = _decimal_payload_value(
            payload,
            "valor_unitario",
            "dailyRate",
            "diaria_padrao",
        )
    else:
        valor_unitario = Decimal("0.00")

    if has_daily_rate:
        diaria_padrao = _decimal_payload_value(
            payload,
            "diaria_padrao",
            "diaria_padrao",
            "dailyRate",
        )
    elif has_unit_rate:
        diaria_padrao = valor_unitario
    else:
        diaria_padrao = Decimal("0.00")

    return {
        "nome": _string_payload_value(payload, "name"),
        "codigo": _string_payload_value(payload, "code").lower(),
        "unidade_cobranca": unidade_cobranca,
        "valor_unitario": valor_unitario,
        "diaria_padrao": diaria_padrao,
        "horas_base_diaria": _integer_payload_value(
            payload,
            "horas_base_diaria",
            "baseHours",
            default=8,
        ),
        "percentual_hora_extra": _decimal_payload_value(
            payload,
            "percentual_hora_extra",
            "overtimePercent",
            default="1.50",
        ),
        "usa_regra_especial": _boolean_payload_value(
            payload,
            "usesSpecialRule",
            default=False,
        ),
        "ativo": _boolean_payload_value(payload, "isActive", default=True),
    }


def _servico_update_data_from_payload(payload, servico):
    data = {}

    if _payload_has_any(payload, "name"):
        data["nome"] = _string_payload_value(payload, "name")

    if _payload_has_any(payload, "code"):
        data["codigo"] = _string_payload_value(payload, "code").lower()

    if _payload_has_any(payload, "billingUnit", "unidade_cobranca"):
        data["unidade_cobranca"] = _billing_unit_payload_value(
            payload,
            "unidade_cobranca",
            "billingUnit",
            "unidade_cobranca",
        )

    has_unit_rate = _payload_has_any(payload, "unitRate", "valor_unitario")
    has_daily_rate = _payload_has_any(payload, "dailyRate", "diaria_padrao")

    if has_unit_rate:
        data["valor_unitario"] = _decimal_payload_value(
            payload,
            "valor_unitario",
            "unitRate",
            "valor_unitario",
        )

    if has_daily_rate:
        diaria_padrao = _decimal_payload_value(
            payload,
            "diaria_padrao",
            "diaria_padrao",
            "dailyRate",
        )
        data["diaria_padrao"] = diaria_padrao

        unidade_efetiva = data.get("unidade_cobranca", servico.unidade_cobranca)
        if (
            not has_unit_rate
            and unidade_efetiva == Servico.UNIDADE_COBRANCA_DIARIA
        ):
            data["valor_unitario"] = diaria_padrao

    if _payload_has_any(payload, "baseHours", "horas_base_diaria"):
        data["horas_base_diaria"] = _integer_payload_value(
            payload,
            "horas_base_diaria",
            "horas_base_diaria",
            "baseHours",
        )

    if _payload_has_any(payload, "overtimePercent", "percentual_hora_extra"):
        data["percentual_hora_extra"] = _decimal_payload_value(
            payload,
            "percentual_hora_extra",
            "percentual_hora_extra",
            "overtimePercent",
        )

    if _payload_has_any(payload, "usesSpecialRule", "usa_regra_especial"):
        data["usa_regra_especial"] = _boolean_payload_value(
            payload,
            "usesSpecialRule",
            "usa_regra_especial",
        )

    if _payload_has_any(payload, "isActive", "ativo"):
        data["ativo"] = _boolean_payload_value(payload, "isActive", "ativo")

    return data


def _duplicidade_errors(servico):
    errors = {}

    if servico.nome:
        queryset_nome = Servico.objects.filter(nome__iexact=servico.nome)
        if servico.pk:
            queryset_nome = queryset_nome.exclude(pk=servico.pk)
        if queryset_nome.exists():
            errors["nome"] = ["Ja existe um servico com este nome."]

    if servico.codigo:
        queryset_codigo = Servico.objects.filter(codigo__iexact=servico.codigo)
        if servico.pk:
            queryset_codigo = queryset_codigo.exclude(pk=servico.pk)
        if queryset_codigo.exists():
            errors["codigo"] = ["Ja existe um servico com este codigo."]

    return errors


def _servico_validation_errors(servico):
    errors = {}

    if servico.unidade_cobranca not in {
        Servico.UNIDADE_COBRANCA_DIARIA,
        Servico.UNIDADE_COBRANCA_HORA,
    }:
        errors["unidade_cobranca"] = ["Informe diaria ou hora."]

    if servico.valor_unitario < 0:
        errors["valor_unitario"] = ["O valor unitario nao pode ser negativo."]

    if servico.diaria_padrao < 0:
        errors["diaria_padrao"] = ["A diaria padrao nao pode ser negativa."]

    if servico.horas_base_diaria <= 0:
        errors["horas_base_diaria"] = ["As horas base devem ser maiores que zero."]

    if servico.percentual_hora_extra < 0:
        errors["percentual_hora_extra"] = [
            "O percentual de hora extra nao pode ser negativo."
        ]

    return errors


def _servicos_filtrados(request):
    search = (request.GET.get("search") or "").strip()
    active = _normalizar_filtro_booleano(request.GET.get("active", "all"))
    special_rule = _normalizar_filtro_booleano(request.GET.get("specialRule", "all"))

    servicos = Servico.objects.all().order_by("nome", "id")

    if search:
        servicos = servicos.filter(Q(nome__icontains=search) | Q(codigo__icontains=search))

    if active == "sim":
        servicos = servicos.filter(ativo=True)
    elif active == "nao":
        servicos = servicos.filter(ativo=False)

    if special_rule == "sim":
        servicos = servicos.filter(usa_regra_especial=True)
    elif special_rule == "nao":
        servicos = servicos.filter(usa_regra_especial=False)

    filters = {
        "search": search,
        "active": active,
        "specialRule": special_rule,
    }

    return servicos, filters


def _servicos_response(request):
    servicos, filters = _servicos_filtrados(request)

    return api_no_store_json_response(
        {
            "data": {
                "services": [_serialize_servico(servico) for servico in servicos],
                "summary": {
                    "total": servicos.count(),
                    "active": servicos.filter(ativo=True).count(),
                    "inactive": servicos.filter(ativo=False).count(),
                    "specialRule": servicos.filter(usa_regra_especial=True).count(),
                },
                "filters": filters,
                "filterOptions": {
                    "activeStatuses": [
                        {"value": "sim", "label": "Ativo"},
                        {"value": "nao", "label": "Inativo"},
                    ],
                    "specialRuleStatuses": [
                        {"value": "sim", "label": "Com regra especial"},
                        {"value": "nao", "label": "Sem regra especial"},
                    ],
                },
                "permissions": {
                    "canCreate": request.user.has_perm(ADD_SERVICE_PERMISSION),
                    "canUpdate": request.user.has_perm(CHANGE_SERVICE_PERMISSION),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _salvar_servico_response(servico, *, status=200, success_message):
    validation_errors = _servico_validation_errors(servico)
    if validation_errors:
        return api_no_store_json_response(
            {"errors": validation_errors},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    duplicidade_errors = _duplicidade_errors(servico)
    if duplicidade_errors:
        return api_no_store_json_response(
            {"errors": duplicidade_errors},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    try:
        servico.full_clean()
        servico.save()
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
                    "detail": ["Nao foi possivel salvar o servico por duplicidade."]
                }
            },
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "service": _serialize_servico(servico),
                "message": success_message,
            }
        },
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def _criar_servico_response(request):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    try:
        servico = Servico(**_servico_create_data_from_payload(payload))
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return _salvar_servico_response(
        servico,
        status=201,
        success_message="Servico cadastrado com sucesso.",
    )


def _servico_detalhe_response(request, servico):
    return api_no_store_json_response(
        {
            "data": {
                "service": _serialize_servico(servico),
                "permissions": {
                    "canUpdate": request.user.has_perm(CHANGE_SERVICE_PERMISSION),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _atualizar_servico_response(request, servico):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    try:
        for field, value in _servico_update_data_from_payload(payload, servico).items():
            setattr(servico, field, value)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return _salvar_servico_response(
        servico,
        success_message="Servico atualizado com sucesso.",
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
    exception = Http404("No Servico matches the given query.")
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
def api_servicos(request):
    if not request.user.is_authenticated:
        return _drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_SERVICE_PERMISSION):
            return _drf_response_from_json_response(api_permission_denied_response())

        return _drf_response_from_json_response(_servicos_response(request))

    if not request.user.has_perm(ADD_SERVICE_PERMISSION):
        return _drf_response_from_json_response(api_permission_denied_response())

    return _drf_response_from_json_response(_criar_servico_response(request))


@extend_schema(
    methods=["GET"],
    operation_id="servicos_detalhe_retrieve",
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="servicos_detalhe_update",
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_servico_detalhe(request, pk):
    if not request.user.is_authenticated:
        return _drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_SERVICE_PERMISSION):
            return _drf_response_from_json_response(api_permission_denied_response())

        try:
            servico = get_object_or_404(Servico, pk=pk)
        except Http404:
            return _django_not_found_response(request)

        return _drf_response_from_json_response(_servico_detalhe_response(request, servico))

    if not request.user.has_perm(CHANGE_SERVICE_PERMISSION):
        return _drf_response_from_json_response(api_permission_denied_response())

    try:
        servico = get_object_or_404(Servico, pk=pk)
    except Http404:
        return _django_not_found_response(request)

    return _drf_response_from_json_response(
        _atualizar_servico_response(request, servico)
    )
