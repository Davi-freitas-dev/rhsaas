import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.views.defaults import page_not_found
from django.views.decorators.http import require_http_methods, require_POST
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

from .models import Cliente, ConfiguracaoFinanceira, Orcamento, OrcamentoItem, Servico
from .models_custos_extras import EventoCustoExtra, OrcamentoCustoExtra
from .permissions import (
    ADD_BUDGET_ITEM_PERMISSION,
    ADD_BUDGET_PERMISSION,
    CHANGE_BUDGET_PERMISSION,
    VIEW_BUDGET_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
    is_tenant_administrator,
    require_api_permission,
)
from .selectors_cadastros import (
    filtrar_orcamentos,
    status_orcamentos_para_filtro,
    totais_orcamentos,
)
from .serializers_dimensoes_operacionais import serializar_dimensao_operacional
from .services_dimensoes_operacionais import (
    relacao_carregada,
    relacoes_multiplas_carregadas,
)
from .services_cadastros import aprovar_orcamento_como_superuser
from .utils_financeiros import decimal_zero
from .views_clientes_api import JsonBodySafeSessionAuthentication


EDITABLE_BUDGET_STATUSES = {"rascunho", "enviado"}
ITEM_EDITABLE_VALUE_FIELDS = {
    "unidade_cobranca_usada",
    "valor_unitario_usado",
    "valor_diaria_usada",
    "valor_alimentacao_usado",
    "valor_transporte_usado",
    "margem_lucro_usada",
    "aliquota_imposto_usada",
    "usa_regra_especial",
}


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


def _integer_payload_value(payload, field_name, *keys, required=False, positive=False):
    value = _first_payload_value(payload, *keys, default="")
    text = str(value).strip()

    if not text:
        if required:
            raise ValidationError({field_name: "Informe um numero valido."})
        return None

    try:
        number = int(text)
    except (TypeError, ValueError) as error:
        raise ValidationError({field_name: "Informe um numero valido."}) from error

    if positive and number <= 0:
        raise ValidationError({field_name: "Informe um numero maior que zero."})

    return number


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


def _rate_decimal_payload_value(payload, field_name, *keys, required=False):
    value = _first_payload_value(payload, *keys, default="")
    text = str(value).strip().replace(" ", "")

    if not text:
        if required:
            raise ValidationError({field_name: "Informe um valor valido."})
        return Decimal("0.00")

    is_percentage = text.endswith("%")
    if is_percentage:
        text = text[:-1].strip()

    try:
        number = Decimal(text.replace(",", "."))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError({field_name: "Informe um valor numerico valido."}) from error

    if is_percentage:
        number = number / Decimal("100")

    if number < Decimal("0.00"):
        raise ValidationError({field_name: "Informe um valor maior ou igual a zero."})

    return number


def _payload_has_any(payload, *keys):
    return any(key in payload for key in keys)


def _optional_decimal_payload_value(payload, field_name, *keys):
    if not _payload_has_any(payload, *keys):
        return None

    value = _first_payload_value(payload, *keys, default="")
    if str(value).strip() == "":
        return None

    return _decimal_payload_value(payload, field_name, *keys, required=True)


def _optional_rate_decimal_payload_value(payload, field_name, *keys):
    if not _payload_has_any(payload, *keys):
        return None

    value = _first_payload_value(payload, *keys, default="")
    if str(value).strip() == "":
        return None

    return _rate_decimal_payload_value(payload, field_name, *keys, required=True)


def _billing_unit_payload_value(payload, field_name, *keys):
    unidade = _string_payload_value(payload, *keys).lower()
    unidades_validas = {
        Servico.UNIDADE_COBRANCA_DIARIA,
        Servico.UNIDADE_COBRANCA_HORA,
    }
    if unidade not in unidades_validas:
        raise ValidationError({field_name: "Informe diaria ou hora."})
    return unidade


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

    if text in {"0", "false", "nao", "não", "n", "no", "off", ""}:
        return False

    raise ValidationError({field_name: "Informe verdadeiro ou falso."})


def _date_payload_value(payload, field_name, *keys, required=False):
    text = _string_payload_value(payload, *keys)

    if not text:
        if required:
            raise ValidationError({field_name: "Informe uma data valida."})
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


def _choice_options(choices):
    return [{"value": value, "label": label} for value, label in choices]


def _budget_queryset():
    return _preparar_orcamentos_queryset(Orcamento.objects.all())


def _preparar_orcamentos_queryset(queryset):
    return queryset.select_related(
        "cliente",
        "configuracao_financeira",
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).prefetch_related(
        "itens__servico",
        "custos_extras",
    )


def _serialize_cliente_option(cliente):
    display_name = cliente.nome_fantasia or cliente.nome_razao_social
    return {
        "id": cliente.id,
        "name": cliente.nome_razao_social,
        "tradeName": cliente.nome_fantasia,
        "displayName": display_name,
        "isActive": cliente.ativo,
    }


def _serialize_configuracao_option(configuracao):
    return {
        "id": configuracao.id,
        "name": configuracao.nome,
        "displayName": str(configuracao),
        "isActive": configuracao.ativa,
        "effectiveDate": _date_or_empty(configuracao.data_inicio_vigencia),
        "mealAmount": _money(configuracao.valor_alimentacao),
        "transportAmount": _money(configuracao.valor_transporte),
        "profitMargin": _money(configuracao.margem_lucro),
        "taxRate": _money(configuracao.aliquota_imposto),
    }


def _serialize_servico_option(servico):
    return {
        "id": servico.id,
        "name": servico.nome,
        "code": servico.codigo,
        "billingUnit": servico.unidade_cobranca,
        "unitRate": _money(servico.valor_unitario),
        "dailyRate": _money(servico.diaria_padrao),
        "baseHours": servico.horas_base_diaria,
        "overtimePercent": _money(servico.percentual_hora_extra),
        "usesSpecialRule": servico.usa_regra_especial,
        "isActive": servico.ativo,
    }


def _serialize_orcamento_item(item):
    servico = relacao_carregada(item, "servico")
    return {
        "id": item.id,
        "serviceId": item.servico_id,
        "serviceName": getattr(servico, "nome", ""),
        "hoursPerDay": item.horas_por_dia,
        "daysCount": item.quantidade_dias,
        "peopleCount": item.quantidade_pessoas,
        "billingUnitUsed": item.unidade_cobranca_usada,
        "unitRateUsed": _money(item.valor_unitario_usado),
        "billedHoursQuantity": _money(item.quantidade_horas_cobradas),
        "dailyRateUsed": _money(item.valor_diaria_usada),
        "mealAmountUsed": _money(item.valor_alimentacao_usado),
        "transportAmountUsed": _money(item.valor_transporte_usado),
        "profitMarginUsed": _money(item.margem_lucro_usada),
        "taxRateUsed": _money(item.aliquota_imposto_usada),
        "usesSpecialRule": item.usa_regra_especial,
        "dayValuePerPerson": _money(item.valor_dia_por_pessoa),
        "mealQuantityPerDay": item.quantidade_alimentacao_por_dia,
        "transportQuantityPerDay": item.quantidade_transporte_por_dia,
        "serviceCostAmount": _money(item.custo_servico_total),
        "mealCostAmount": _money(item.gasto_alimentacao_total),
        "transportCostAmount": _money(item.gasto_transporte_total),
        "overtimeAmount": _money(item.valor_horas_extras_total),
        "costAmount": _money(item.custo_total),
        "amountWithMargin": _money(item.valor_com_margem),
        "taxAmount": _money(item.valor_imposto),
        "profitAmount": _money(item.lucro),
        "saleAmount": _money(item.preco_venda),
    }


def _serialize_custo_extra(custo_extra):
    return {
        "id": custo_extra.id,
        "category": custo_extra.categoria,
        "categoryLabel": custo_extra.get_categoria_display(),
        "description": custo_extra.descricao,
        "plannedAmount": _money(custo_extra.valor_previsto),
        "dueDate": _date_or_empty(custo_extra.data_vencimento),
        "notes": custo_extra.observacao,
        "eventExtraCostId": custo_extra.evento_custo_extra_id,
    }


def _event_id_or_empty(orcamento):
    evento = relacao_carregada(orcamento, "evento")
    return getattr(evento, "id", None)


def _serialize_orcamento(orcamento):
    configuracao = relacao_carregada(orcamento, "configuracao_financeira")
    itens = relacoes_multiplas_carregadas(orcamento, "itens")
    custos_extras = relacoes_multiplas_carregadas(orcamento, "custos_extras")
    dimensao = serializar_dimensao_operacional(orcamento)

    return {
        "id": orcamento.id,
        "number": orcamento.numero,
        "contract": dimensao["contractCode"],
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "contractLabel": dimensao["contractLabel"],
        "clientId": dimensao["clientId"] or orcamento.cliente_id,
        "clientName": dimensao["clientName"],
        "clientTradeName": dimensao["clientTradeName"],
        "clientDisplayName": dimensao["clientDisplayName"],
        "configurationId": orcamento.configuracao_financeira_id,
        "configurationName": str(configuracao) if configuracao is not None else "",
        "eventName": orcamento.nome_evento,
        "eventDate": _date_or_empty(orcamento.data_evento),
        "local": orcamento.local,
        "validUntil": _date_or_empty(orcamento.validade),
        "status": orcamento.status,
        "statusLabel": orcamento.get_status_display(),
        "notes": orcamento.observacoes,
        "subtotalCosts": _money(orcamento.subtotal_custos),
        "taxAmount": _money(orcamento.total_impostos),
        "profitAmount": _money(orcamento.total_lucro),
        "saleAmount": _money(orcamento.total_venda),
        "items": [_serialize_orcamento_item(item) for item in itens],
        "extraCosts": [
            _serialize_custo_extra(custo_extra)
            for custo_extra in custos_extras
        ],
        "isEditable": orcamento.status in EDITABLE_BUDGET_STATUSES,
        "approvedEventId": _event_id_or_empty(orcamento),
        "createdAt": _datetime_or_empty(orcamento.criado_em),
        "updatedAt": _datetime_or_empty(orcamento.atualizado_em),
    }


def _filter_options():
    return {
        "statuses": _choice_options(status_orcamentos_para_filtro()),
        "editableStatuses": _choice_options(
            [
                choice
                for choice in Orcamento.STATUS_CHOICES
                if choice[0] in EDITABLE_BUDGET_STATUSES
            ]
        ),
        "clients": [
            _serialize_cliente_option(cliente)
            for cliente in Cliente.objects.filter(ativo=True).order_by("nome_razao_social", "id")
        ],
        "configurations": [
            _serialize_configuracao_option(configuracao)
            for configuracao in ConfiguracaoFinanceira.objects.order_by(
                "-ativa",
                "-data_inicio_vigencia",
                "-id",
            )
        ],
        "services": [
            _serialize_servico_option(servico)
            for servico in Servico.objects.filter(ativo=True).order_by("nome", "id")
        ],
        "extraCostCategories": _choice_options(EventoCustoExtra.CATEGORIA_CHOICES),
    }


def _permissions_payload(user):
    return {
        "canCreate": all(
            user.has_perm(permission)
            for permission in [ADD_BUDGET_PERMISSION, ADD_BUDGET_ITEM_PERMISSION]
        ),
        "canUpdate": user.has_perm(CHANGE_BUDGET_PERMISSION),
        "canApprove": is_tenant_administrator(user)
        and user.has_perm(CHANGE_BUDGET_PERMISSION),
    }


def _summary_payload(orcamentos):
    totais = totais_orcamentos(orcamentos)

    return {
        "total": orcamentos.count(),
        "draftCount": orcamentos.filter(status="rascunho").count(),
        "sentCount": orcamentos.filter(status="enviado").count(),
        "approvedCount": orcamentos.filter(status="aprovado").count(),
        "saleAmount": _money(totais["total_venda"]),
    }


def _orcamentos_response(request):
    filtros = {
        "busca": (request.GET.get("search") or request.GET.get("busca", "")).strip(),
        "status": request.GET.get("status", "").strip(),
    }
    orcamentos = _preparar_orcamentos_queryset(filtrar_orcamentos(**filtros))
    filters_payload = {
        **filtros,
        "search": filtros["busca"],
    }

    return api_no_store_json_response(
        {
            "data": {
                "budgets": [_serialize_orcamento(orcamento) for orcamento in orcamentos],
                "summary": _summary_payload(orcamentos),
                "filters": filters_payload,
                "filterOptions": _filter_options(),
                "permissions": _permissions_payload(request.user),
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _blank_item_payload(item):
    return not any(
        _string_payload_value(
            item,
            "serviceId",
            "servico",
            "hoursPerDay",
            "horas_por_dia",
            "daysCount",
            "quantidade_dias",
            "peopleCount",
            "quantidade_pessoas",
            "billingUnitUsed",
            "unidade_cobranca_usada",
            "unitRateUsed",
            "valor_unitario_usado",
            "billedHoursQuantity",
            "quantidade_horas_cobradas",
            "dailyRateUsed",
            "valor_diaria_usada",
            "mealAmountUsed",
            "valor_alimentacao_usado",
            "transportAmountUsed",
            "valor_transporte_usado",
            "profitMarginUsed",
            "margem_lucro_usada",
            "taxRateUsed",
            "aliquota_imposto_usada",
            "usesSpecialRule",
            "usa_regra_especial",
        )
    )


def _itens_from_payload(payload):
    raw_items = _first_payload_value(payload, "items", "itens", default=[])
    if not isinstance(raw_items, list):
        raise ValidationError({"items": "Informe uma lista de itens."})

    itens = []
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise ValidationError({f"items[{index}]": "Informe um item valido."})

        if _blank_item_payload(raw_item):
            continue

        service_id = _integer_payload_value(
            raw_item,
            f"items[{index}].serviceId",
            "serviceId",
            "servico",
            required=True,
            positive=True,
        )
        item_data = {
            "servico_id": service_id,
            "horas_por_dia": _integer_payload_value(
                raw_item,
                f"items[{index}].hoursPerDay",
                "hoursPerDay",
                "horas_por_dia",
                required=True,
                positive=True,
            ),
            "quantidade_dias": _integer_payload_value(
                raw_item,
                f"items[{index}].daysCount",
                "daysCount",
                "quantidade_dias",
                required=True,
                positive=True,
            ),
            "quantidade_pessoas": _integer_payload_value(
                raw_item,
                f"items[{index}].peopleCount",
                "peopleCount",
                "quantidade_pessoas",
                required=True,
                positive=True,
            ),
        }

        quantidade_horas_cobradas = _optional_decimal_payload_value(
            raw_item,
            f"items[{index}].billedHoursQuantity",
            "billedHoursQuantity",
            "quantidade_horas_cobradas",
        )
        if quantidade_horas_cobradas is not None:
            item_data["quantidade_horas_cobradas"] = quantidade_horas_cobradas

        if _payload_has_any(raw_item, "billingUnitUsed", "unidade_cobranca_usada"):
            item_data["unidade_cobranca_usada"] = _billing_unit_payload_value(
                raw_item,
                f"items[{index}].billingUnitUsed",
                "billingUnitUsed",
                "unidade_cobranca_usada",
            )

        decimal_fields = [
            (
                "valor_unitario_usado",
                "unitRateUsed",
                "valor_unitario_usado",
                _optional_decimal_payload_value,
            ),
            (
                "valor_diaria_usada",
                "dailyRateUsed",
                "valor_diaria_usada",
                _optional_decimal_payload_value,
            ),
            (
                "valor_alimentacao_usado",
                "mealAmountUsed",
                "valor_alimentacao_usado",
                _optional_decimal_payload_value,
            ),
            (
                "valor_transporte_usado",
                "transportAmountUsed",
                "valor_transporte_usado",
                _optional_decimal_payload_value,
            ),
            (
                "margem_lucro_usada",
                "profitMarginUsed",
                "margem_lucro_usada",
                _optional_rate_decimal_payload_value,
            ),
            (
                "aliquota_imposto_usada",
                "taxRateUsed",
                "aliquota_imposto_usada",
                _optional_rate_decimal_payload_value,
            ),
        ]
        for model_field, api_key, legacy_key, parser in decimal_fields:
            value = parser(
                raw_item,
                f"items[{index}].{api_key}",
                api_key,
                legacy_key,
            )
            if value is not None:
                item_data[model_field] = value

        if (
            "valor_unitario_usado" not in item_data
            and "valor_diaria_usada" in item_data
        ):
            item_data["valor_unitario_usado"] = item_data["valor_diaria_usada"]

        if _payload_has_any(raw_item, "usesSpecialRule", "usa_regra_especial"):
            item_data["usa_regra_especial"] = _boolean_payload_value(
                raw_item,
                f"items[{index}].usesSpecialRule",
                "usesSpecialRule",
                "usa_regra_especial",
            )

        itens.append(
            item_data
        )

    if not itens:
        raise ValidationError({"items": "Informe pelo menos um item do orçamento."})

    return itens


def _blank_extra_cost_payload(extra_cost):
    return not any(
        _string_payload_value(
            extra_cost,
            "category",
            "categoria",
            "description",
            "descricao",
            "plannedAmount",
            "valor_previsto",
            "dueDate",
            "data_vencimento",
            "notes",
            "observacao",
        )
    )


def _custos_extras_from_payload(payload):
    raw_extra_costs = _first_payload_value(payload, "extraCosts", "custos_extras", default=[])
    if not isinstance(raw_extra_costs, list):
        raise ValidationError({"extraCosts": "Informe uma lista de custos extras."})

    categorias_validas = {value for value, _label in EventoCustoExtra.CATEGORIA_CHOICES}
    custos_extras = []

    for index, raw_extra_cost in enumerate(raw_extra_costs):
        if not isinstance(raw_extra_cost, dict):
            raise ValidationError({f"extraCosts[{index}]": "Informe um custo extra valido."})

        if _blank_extra_cost_payload(raw_extra_cost):
            continue

        categoria = _string_payload_value(raw_extra_cost, "category", "categoria") or "insumo"
        if categoria not in categorias_validas:
            raise ValidationError({f"extraCosts[{index}].category": "Categoria invalida."})

        descricao = _string_payload_value(raw_extra_cost, "description", "descricao")
        if not descricao:
            raise ValidationError(
                {f"extraCosts[{index}].description": "Informe a descrição."}
            )

        custos_extras.append(
            {
                "categoria": categoria,
                "descricao": descricao,
                "valor_previsto": _decimal_payload_value(
                    raw_extra_cost,
                    f"extraCosts[{index}].plannedAmount",
                    "plannedAmount",
                    "valor_previsto",
                    required=True,
                ),
                "data_vencimento": _date_payload_value(
                    raw_extra_cost,
                    f"extraCosts[{index}].dueDate",
                    "dueDate",
                    "data_vencimento",
                    required=True,
                ),
                "observacao": _string_payload_value(raw_extra_cost, "notes", "observacao"),
            }
        )

    return custos_extras


def _orcamento_data_from_payload(payload):
    status = _string_payload_value(payload, "status") or "rascunho"
    if status not in EDITABLE_BUDGET_STATUSES:
        raise ValidationError({"status": "Use rascunho ou enviado antes da aprovação."})

    return {
        "cliente_id": _integer_payload_value(
            payload,
            "clientId",
            "clientId",
            "cliente",
            required=True,
            positive=True,
        ),
        "configuracao_financeira_id": _integer_payload_value(
            payload,
            "configurationId",
            "configurationId",
            "configuracao_financeira",
            required=True,
            positive=True,
        ),
        "numero": _string_payload_value(payload, "number", "numero", "contract", "contrato"),
        "nome_evento": _string_payload_value(payload, "eventName", "nome_evento"),
        "data_evento": _date_payload_value(
            payload,
            "eventDate",
            "eventDate",
            "data_evento",
            required=True,
        ),
        "local": _string_payload_value(payload, "local"),
        "validade": _date_payload_value(payload, "validUntil", "validade"),
        "status": status,
        "observacoes": _string_payload_value(payload, "notes", "observacoes"),
    }


def _salvar_orcamento_from_payload(payload, *, orcamento=None):
    orcamento_data = _orcamento_data_from_payload(payload)
    itens_data = _itens_from_payload(payload)
    custos_extras_data = _custos_extras_from_payload(payload)

    if orcamento is not None and orcamento.status not in EDITABLE_BUDGET_STATUSES:
        raise ValidationError(
            {
                "status": (
                    "Orçamentos aprovados, recusados ou cancelados ficam somente "
                    "leitura no Next."
                )
            }
        )

    with transaction.atomic():
        orcamento = orcamento or Orcamento()

        for field, value in orcamento_data.items():
            setattr(orcamento, field, value)

        orcamento.full_clean()
        orcamento.save()

        orcamento.itens.all().delete()
        orcamento.custos_extras.all().delete()

        for item_data in itens_data:
            item_data = item_data.copy()
            valores_editaveis = {
                field: item_data.pop(field)
                for field in ITEM_EDITABLE_VALUE_FIELDS
                if field in item_data
            }
            item = OrcamentoItem.objects.create(orcamento=orcamento, **item_data)

            if valores_editaveis:
                for field, value in valores_editaveis.items():
                    setattr(item, field, value)
                item.save()

        for custo_extra_data in custos_extras_data:
            OrcamentoCustoExtra.objects.create(orcamento=orcamento, **custo_extra_data)

        orcamento.recalcular_totais()

    return _budget_queryset().get(pk=orcamento.pk)


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


def _criar_orcamento_response(request):
    payload = _json_required_response(request)
    if not isinstance(payload, dict):
        return payload

    try:
        orcamento = _salvar_orcamento_from_payload(payload)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"number": ["Já existe um orçamento com este contrato."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "budget": _serialize_orcamento(orcamento),
                "message": "Orçamento cadastrado com sucesso.",
            }
        },
        status=201,
        json_dumps_params={"ensure_ascii": False},
    )


def _atualizar_orcamento_response(request, orcamento):
    payload = _json_required_response(request)
    if not isinstance(payload, dict):
        return payload

    try:
        orcamento = _salvar_orcamento_from_payload(payload, orcamento=orcamento)
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"number": ["Já existe um orçamento com este contrato."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "budget": _serialize_orcamento(orcamento),
                "message": "Orçamento atualizado com sucesso.",
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_http_methods(["GET", "POST"])
@extend_schema(methods=["GET"], responses={200: OpenApiTypes.OBJECT}, auth=[{"cookieAuth": []}])
@extend_schema(
    methods=["POST"],
    request=OpenApiTypes.OBJECT,
    responses={201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_orcamentos(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_BUDGET_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        return drf_response_from_json_response(_orcamentos_response(request))

    if not all(
        request.user.has_perm(permission)
        for permission in [ADD_BUDGET_PERMISSION, ADD_BUDGET_ITEM_PERMISSION]
    ):
        return drf_response_from_json_response(api_permission_denied_response())

    return drf_response_from_json_response(_criar_orcamento_response(request))


@extend_schema(
    methods=["GET"],
    operation_id="orcamentos_detalhe_retrieve",
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="orcamentos_detalhe_update",
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@require_http_methods(["GET", "PUT"])
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_orcamento_detalhe(request, pk):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    def django_not_found_response():
        django_request = getattr(request, "_request", request)
        exception = Http404("No Orcamento matches the given query.")
        return page_not_found(django_request, exception)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_BUDGET_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        try:
            orcamento = get_object_or_404(_budget_queryset(), pk=pk)
        except Http404:
            return django_not_found_response()

        return drf_response_from_json_response(
            api_no_store_json_response(
                {
                    "data": {
                        "budget": _serialize_orcamento(orcamento),
                        "permissions": _permissions_payload(request.user),
                        "filterOptions": _filter_options(),
                        "meta": {"source": "backend"},
                    }
                },
                json_dumps_params={"ensure_ascii": False},
            )
        )

    if not request.user.has_perm(CHANGE_BUDGET_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        orcamento = get_object_or_404(_budget_queryset(), pk=pk)
    except Http404:
        return django_not_found_response()

    return drf_response_from_json_response(_atualizar_orcamento_response(request, orcamento))


@require_POST
@extend_schema(
    methods=["POST"],
    operation_id="orcamentos_aprovar_create",
    request=None,
    responses={200: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_aprovar_orcamento(request, pk):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    def django_not_found_response():
        django_request = getattr(request, "_request", request)
        exception = Http404("No Orcamento matches the given query.")
        return page_not_found(django_request, exception)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(CHANGE_BUDGET_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        orcamento = get_object_or_404(_budget_queryset(), pk=pk)
    except Http404:
        return django_not_found_response()

    resultado = aprovar_orcamento_como_superuser(orcamento, request.user)

    if not resultado["ok"]:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"detail": resultado["mensagem"]},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    orcamento = _budget_queryset().get(pk=orcamento.pk)
    evento = resultado["evento"]

    return drf_response_from_json_response(
        api_no_store_json_response(
            {
                "data": {
                    "budget": _serialize_orcamento(orcamento),
                    "event": {
                        "id": evento.id,
                        "contract": evento.contrato,
                        "number": evento.numero,
                        "name": evento.nome_evento,
                    },
                    "message": resultado["mensagem"],
                },
            },
            json_dumps_params={"ensure_ascii": False},
        )
    )
