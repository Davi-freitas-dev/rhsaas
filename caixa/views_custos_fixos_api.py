import json
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.defaults import page_not_found
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .constants_financeiros import STATUS_CANCELADO, STATUS_PAGO, STATUS_PENDENTE
from .models_custo_fixo import CustoFixo, PlanoCustoRecorrente
from .demo_policy import assert_demo_write_allowed, demo_object_flags
from .permissions import (
    ADD_FIXED_COST_PERMISSION,
    CHANGE_FIXED_COST_PERMISSION,
    VIEW_FIXED_COST_PERMISSION,
    VIEW_SERVER_SALARY_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .selectors_custos_fixos import (
    Q_CUSTO_FIXO_RECORRENTE,
    agrupar_custos_fixos_por_categoria,
    categorias_custo_fixo_para_filtro,
    listar_custos_fixos_ordenados,
    recorrencia_custo_fixo_para_filtro,
    resolver_periodo_custos_fixos,
    status_custo_fixo_para_filtro,
    tipos_registro_custo_fixo_para_filtro,
    totais_custos_fixos,
)
from .services_custos_recorrentes import (
    adicionar_meses_competencia,
    criar_plano_recorrente,
    horizonte_maximo_meses,
    projetar_custos_recorrentes,
)
from .services_idempotencia import (
    ChaveIdempotenciaInvalida,
    ConflitoChaveIdempotencia,
    executar_requisicao_idempotente,
    parsear_chave_idempotencia,
)
from .serializers_api import HttpApiErrorSerializer
from .serializers_custos_fixos_api import (
    FixedCostDetailResponseSerializer,
    FixedCostListResponseSerializer,
    FixedCostMutationResponseSerializer,
    FixedCostPayloadSerializer,
)
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


def _first_payload_value(payload, *keys, default=""):
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return default


def _string_payload_value(payload, *keys, default=""):
    value = _first_payload_value(payload, *keys, default=default)
    return str(value).strip() if value is not None else ""


def _boolean_payload_value(payload, *keys, default=False):
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


def _money(value):
    return f"{value:.2f}"


def _date_or_empty(value):
    return value.isoformat() if value else ""


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _choice_options(choices):
    return [{"value": value, "label": label} for value, label in choices]


def _is_overdue(custo_fixo):
    return (
        custo_fixo.data_vencimento < timezone.localdate()
        and custo_fixo.valor_pendente_pagamento > Decimal("0.00")
        and custo_fixo.status not in [STATUS_PAGO, STATUS_CANCELADO]
    )


def _record_type(custo_fixo):
    return "automatico" if custo_fixo.gerado_automaticamente else "manual"


def _record_type_label(custo_fixo):
    return "Automático" if custo_fixo.gerado_automaticamente else "Manual"


def _serialize_custo_fixo(custo_fixo):
    salarial = custo_fixo.origem_recorrencia == "salario"
    return {
        "id": custo_fixo.id,
        "description": custo_fixo.descricao,
        "category": custo_fixo.categoria,
        "categoryLabel": custo_fixo.get_categoria_display(),
        "plannedAmount": _money(custo_fixo.valor_previsto),
        "paidAmount": _money(custo_fixo.valor_pago),
        "pendingPaymentAmount": _money(custo_fixo.valor_pendente_pagamento),
        "dueDate": _date_or_empty(custo_fixo.data_vencimento),
        "paymentDate": _date_or_empty(custo_fixo.data_pagamento),
        "status": custo_fixo.status,
        "statusLabel": custo_fixo.get_status_display(),
        "manuallySettled": custo_fixo.baixado_manualmente,
        "settlementReason": custo_fixo.motivo_baixa,
        "notes": custo_fixo.observacao,
        "isActive": custo_fixo.ativo,
        "isRecurring": custo_fixo.eh_recorrente,
        "monthsCount": custo_fixo.quantidade_meses,
        "parentId": custo_fixo.custo_pai_id,
        "generatedAutomatically": custo_fixo.gerado_automaticamente,
        "recordType": _record_type(custo_fixo),
        "recordTypeLabel": _record_type_label(custo_fixo),
        "kind": "occurrence",
        "origin": custo_fixo.origem_recorrencia,
        "planId": custo_fixo.plano_recorrente_id,
        "competence": _date_or_empty(custo_fixo.competencia),
        "serverId": custo_fixo.servidor_salario_id,
        "serverReferenceId": custo_fixo.servidor_salario_id,
        "source": (
            "salaryHistory"
            if custo_fixo.origem_recorrencia == "salario"
            else (
                "recurringPlan"
                if custo_fixo.plano_recorrente_id
                else "fixedCost"
            )
        ),
        "projectedAmount": "0.00",
        "forecastAmount": _money(custo_fixo.valor_pendente_pagamento),
        "readOnly": salarial,
        "canEdit": not salarial,
        "canPay": custo_fixo.status not in [STATUS_PAGO, STATUS_CANCELADO],
        "isOverdue": _is_overdue(custo_fixo),
        "createdAt": _datetime_or_empty(custo_fixo.criado_em),
        "updatedAt": _datetime_or_empty(custo_fixo.atualizado_em),
        **demo_object_flags(custo_fixo),
    }


def _serialize_salario_fixo(item):
    return {
        **item,
        "plannedAmount": _money(item["plannedAmount"]),
        "paidAmount": _money(item["paidAmount"]),
        "pendingPaymentAmount": _money(item["pendingPaymentAmount"]),
        "dueDate": _date_or_empty(item["dueDate"]),
        "paymentDate": "",
        "manuallySettled": False,
        "settlementReason": "",
        "notes": "Fonte única: histórico salarial do servidor.",
        "monthsCount": 1,
        "parentId": None,
        "createdAt": "",
        "updatedAt": "",
    }


def _serialize_group(grupo):
    return {
        "category": grupo["categoria"],
        "categoryLabel": grupo["categoria_nome"],
        "items": [_serialize_custo_fixo(item) for item in grupo["itens"]],
        "plannedAmount": _money(grupo["subtotal_previsto"]),
        "paidAmount": _money(grupo["subtotal_pago"]),
        "pendingPaymentAmount": _money(grupo["subtotal_contas_pendentes"]),
        "realizedAmount": _money(grupo["subtotal_pago"]),
        "materializedPlannedAmount": _money(grupo["subtotal_previsto"]),
        "projectedAmount": "0.00",
        "forecastAmount": _money(grupo["subtotal_contas_pendentes"]),
        "total": grupo["quantidade"],
        "overdueCount": grupo["quantidade_vencidos"],
    }


def _build_filters(request):
    busca = (request.GET.get("search") or request.GET.get("busca", "")).strip()
    ativo = (request.GET.get("active") or request.GET.get("ativo", "sim")).strip() or "sim"
    filtros_raw = {
        "data_inicial": (
            request.GET.get("startDate") or request.GET.get("data_inicial", "")
        ).strip(),
        "data_final": (
            request.GET.get("endDate") or request.GET.get("data_final", "")
        ).strip(),
        "categoria": (request.GET.get("category") or request.GET.get("categoria", "")).strip(),
        "status": request.GET.get("status", "").strip(),
        "recorrente": (
            request.GET.get("recurring") or request.GET.get("recorrente", "")
        ).strip(),
        "tipo_registro": (
            request.GET.get("recordType") or request.GET.get("tipo_registro", "")
        ).strip(),
        "periodo_rapido": (
            request.GET.get("quickPeriod") or request.GET.get("periodo_rapido", "")
        ).strip(),
    }
    tem_periodo_explicito = bool(
        filtros_raw["periodo_rapido"]
        or filtros_raw["data_inicial"]
        or filtros_raw["data_final"]
    )
    tem_filtro_personalizado = bool(
        busca
        or filtros_raw["categoria"]
        or filtros_raw["status"]
        or filtros_raw["recorrente"]
        or filtros_raw["tipo_registro"]
        or ativo != "sim"
    )

    if tem_filtro_personalizado and not tem_periodo_explicito:
        filtros_raw["periodo_rapido"] = "todos"

    filtros = resolver_periodo_custos_fixos(filtros_raw, request.session)

    return {
        **filtros,
        "busca": busca,
        "ativo": ativo,
    }


def _filtered_fixed_costs(filtros, *, pode_ver_salario):
    custos = CustoFixo.objects.all()

    if not pode_ver_salario:
        custos = custos.exclude(
            Q(origem_recorrencia="salario") | Q(categoria="salario")
        )

    if filtros["ativo"] == "nao":
        custos = custos.filter(ativo=False)
    elif filtros["ativo"] != "todos":
        custos = custos.filter(ativo=True)

    if filtros["periodo_rapido"] == "vencidos":
        custos = custos.filter(data_vencimento__lt=timezone.localdate()).exclude(
            status__in=[STATUS_PAGO, STATUS_CANCELADO],
        )

    if filtros["data_inicial"]:
        custos = custos.filter(data_vencimento__gte=filtros["data_inicial"])

    if filtros["data_final"]:
        custos = custos.filter(data_vencimento__lte=filtros["data_final"])

    if filtros["categoria"]:
        custos = custos.filter(categoria=filtros["categoria"])

    if filtros["status"]:
        custos = custos.filter(status=filtros["status"])

    if filtros["recorrente"] == "sim":
        custos = custos.filter(Q_CUSTO_FIXO_RECORRENTE)
    elif filtros["recorrente"] == "nao":
        custos = custos.exclude(Q_CUSTO_FIXO_RECORRENTE)

    if filtros["tipo_registro"] == "manual":
        custos = custos.filter(gerado_automaticamente=False)
    elif filtros["tipo_registro"] == "automatico":
        custos = custos.filter(gerado_automaticamente=True)

    if filtros["busca"]:
        custos = custos.filter(
            Q(descricao__icontains=filtros["busca"])
            | Q(observacao__icontains=filtros["busca"])
        )

    return custos


def _projection_for_filters(filtros, *, pode_ver_salario):
    if (
        filtros["ativo"] == "nao"
        or filtros["recorrente"] == "nao"
        or filtros["tipo_registro"] == "manual"
        or (
            filtros["status"]
            and filtros["status"] not in {"projected", "blocked"}
        )
        or filtros["periodo_rapido"] == "vencidos"
    ):
        return {
            "items": [],
            "summary": {
                "projectedAmount": "0.00",
                "projectedCount": 0,
                "blockedCount": 0,
            },
            "period": None,
        }

    hoje = timezone.localdate()
    inicio = filtros["data_inicial"] or hoje
    fim = filtros["data_final"]
    if isinstance(inicio, str):
        inicio = parse_date(inicio) or hoje
    if isinstance(fim, str):
        fim = parse_date(fim)
    if not fim:
        ultima_competencia = adicionar_meses_competencia(
            inicio,
            horizonte_maximo_meses() - 1,
        )
        fim = date(
            ultima_competencia.year,
            ultima_competencia.month,
            calendar.monthrange(
                ultima_competencia.year,
                ultima_competencia.month,
            )[1],
        )

    planos = PlanoCustoRecorrente.objects.filter(ativo=True)
    if not pode_ver_salario:
        planos = planos.exclude(origem=PlanoCustoRecorrente.ORIGEM_SALARIO)
    if filtros["categoria"]:
        planos = planos.filter(categoria=filtros["categoria"])
    if filtros["busca"]:
        planos = planos.filter(
            Q(descricao__icontains=filtros["busca"])
            | Q(observacao__icontains=filtros["busca"])
        )
    resultado = projetar_custos_recorrentes(inicio=inicio, fim=fim, planos=planos)
    if filtros["status"] in {"projected", "blocked"}:
        resultado["items"] = [
            item
            for item in resultado["items"]
            if item["status"] == filtros["status"]
        ]
        resultado["summary"]["projectedAmount"] = _money(
            sum(
                (
                    Decimal(item["projectedAmount"])
                    for item in resultado["items"]
                    if item["status"] == "projected"
                ),
                Decimal("0.00"),
            )
        )
        resultado["summary"]["projectedCount"] = sum(
            item["status"] == "projected" for item in resultado["items"]
        )
        resultado["summary"]["blockedCount"] = sum(
            item["status"] == "blocked" for item in resultado["items"]
        )
    return resultado


def _custo_fixo_data_from_payload(payload):
    return {
        "descricao": _string_payload_value(payload, "description", "descricao"),
        "categoria": _string_payload_value(payload, "category", "categoria") or "outro",
        "valor_previsto": _decimal_payload_value(
            payload,
            "valor_previsto",
            "plannedAmount",
            "valor_previsto",
        ),
        "valor_pago": _decimal_payload_value(
            payload,
            "valor_pago",
            "paidAmount",
            "valor_pago",
        ),
        "data_vencimento": _date_payload_value(
            payload,
            "data_vencimento",
            "dueDate",
            "data_vencimento",
            required=True,
        ),
        "data_pagamento": _date_payload_value(
            payload,
            "data_pagamento",
            "paymentDate",
            "data_pagamento",
        ),
        "status": _string_payload_value(payload, "status") or STATUS_PENDENTE,
        "baixado_manualmente": _boolean_payload_value(
            payload,
            "manuallySettled",
            "baixado_manualmente",
        ),
        "motivo_baixa": _string_payload_value(payload, "settlementReason", "motivo_baixa"),
        "observacao": _string_payload_value(payload, "notes", "observacao"),
        "ativo": _boolean_payload_value(payload, "isActive", "ativo", default=True),
        "recorrente": _boolean_payload_value(payload, "isRecurring", "recorrente", default=True),
        "quantidade_meses": int(
            _decimal_payload_value(
                payload,
                "quantidade_meses",
                "monthsCount",
                "quantidade_meses",
                default="12",
            )
        ),
    }


def _custos_fixos_response(request):
    filtros = _build_filters(request)
    pode_ver_salario = request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION)
    lista_custos = listar_custos_fixos_ordenados(
        _filtered_fixed_costs(filtros, pode_ver_salario=pode_ver_salario)
    )
    totais = totais_custos_fixos(lista_custos)
    grupos = agrupar_custos_fixos_por_categoria(lista_custos)
    projecao = _projection_for_filters(
        filtros,
        pode_ver_salario=pode_ver_salario,
    )
    itens_projetados = projecao["items"]
    total_projetado = Decimal(projecao["summary"]["projectedAmount"])
    overdue_count = sum(1 for custo in lista_custos if _is_overdue(custo))
    grupos_payload = [_serialize_group(grupo) for grupo in grupos]
    for item in itens_projetados:
        grupo_projecao = next(
            (
                grupo
                for grupo in grupos_payload
                if grupo["category"] == item["category"]
            ),
            None,
        )
        if grupo_projecao is None:
            grupo_projecao = {
                "category": item["category"],
                "categoryLabel": item["categoryLabel"],
                "items": [],
                "plannedAmount": "0.00",
                "paidAmount": "0.00",
                "pendingPaymentAmount": "0.00",
                "realizedAmount": "0.00",
                "materializedPlannedAmount": "0.00",
                "projectedAmount": "0.00",
                "forecastAmount": "0.00",
                "total": 0,
                "overdueCount": 0,
            }
            grupos_payload.append(grupo_projecao)
        grupo_projecao["items"].append(item)
        grupo_projecao["projectedAmount"] = _money(
            Decimal(grupo_projecao["projectedAmount"])
            + (
                Decimal(item["projectedAmount"])
                if item["status"] == "projected"
                else Decimal("0.00")
            )
        )
        grupo_projecao["forecastAmount"] = _money(
            Decimal(grupo_projecao["pendingPaymentAmount"])
            + Decimal(grupo_projecao["projectedAmount"])
        )
        grupo_projecao["total"] += 1
    grupos_payload.sort(key=lambda grupo: grupo["categoryLabel"])
    filters_payload = {
        **filtros,
        "search": filtros["busca"],
        "startDate": filtros["data_inicial"],
        "endDate": filtros["data_final"],
        "category": filtros["categoria"],
        "recurring": filtros["recorrente"],
        "recordType": filtros["tipo_registro"],
        "active": filtros["ativo"],
        "quickPeriod": filtros["periodo_rapido"],
    }

    return api_no_store_json_response(
        {
            "data": {
                "fixedCosts": [
                    *[_serialize_custo_fixo(custo) for custo in lista_custos],
                    *itens_projetados,
                ],
                "projections": itens_projetados,
                "groups": grupos_payload,
                "summary": {
                    "plannedAmount": _money(totais["total_previsto"]),
                    "paidAmount": _money(totais["total_pago"]),
                    "realizedAmount": _money(totais["total_pago"]),
                    "materializedPlannedAmount": _money(totais["total_previsto"]),
                    "pendingPaymentAmount": _money(totais["total_contas_pendentes"]),
                    "projectedAmount": _money(total_projetado),
                    "forecastAmount": _money(
                        totais["total_contas_pendentes"] + total_projetado
                    ),
                    "total": totais["quantidade"] + len(itens_projetados),
                    "materializedCount": totais["quantidade"],
                    "projectedCount": projecao["summary"]["projectedCount"],
                    "blockedProjectionCount": projecao["summary"]["blockedCount"],
                    "manualCount": totais["quantidade_manuais"],
                    "automaticCount": totais["quantidade_automaticos"],
                    "overdueCount": overdue_count,
                },
                "filters": filters_payload,
                "filterOptions": {
                    "categories": _choice_options(categorias_custo_fixo_para_filtro()),
                    "statuses": [
                        *_choice_options(status_custo_fixo_para_filtro()),
                        {"value": "projected", "label": "Projetado"},
                        {"value": "blocked", "label": "Bloqueado"},
                    ],
                    "recurring": _choice_options(recorrencia_custo_fixo_para_filtro()),
                    "recordTypes": _choice_options(tipos_registro_custo_fixo_para_filtro()),
                    "activeStatuses": [
                        {"value": "sim", "label": "Ativo"},
                        {"value": "nao", "label": "Inativo"},
                        {"value": "todos", "label": "Todos"},
                    ],
                    "quickPeriods": [
                        {"value": "hoje", "label": "Hoje"},
                        {"value": "mes_atual", "label": "Este mes"},
                        {"value": "30_dias", "label": "30 dias"},
                        {"value": "vencidos", "label": "Vencidos"},
                        {"value": "todos", "label": "Todos"},
                    ],
                },
                "permissions": {
                    "canCreate": request.user.has_perm(ADD_FIXED_COST_PERMISSION),
                    "canUpdate": request.user.has_perm(CHANGE_FIXED_COST_PERMISSION),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _custo_fixo_detalhe_response(request, custo_fixo):
    return api_no_store_json_response(
        {
            "data": {
                "fixedCost": _serialize_custo_fixo(custo_fixo),
                "permissions": {
                    "canUpdate": request.user.has_perm(CHANGE_FIXED_COST_PERMISSION),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _criar_custo_fixo_response(request):
    assert_demo_write_allowed(request.user, operation="create_fixed_cost")
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)
    categoria_payload = _string_payload_value(payload, "category", "categoria")
    if (
        categoria_payload == "salario"
        and not request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION)
    ):
        return api_permission_denied_response()

    replayed = False
    try:
        dados_custo = _custo_fixo_data_from_payload(payload)
        if dados_custo["recorrente"]:
            if dados_custo["categoria"] == "salario":
                raise ValidationError(
                    {
                        "categoria": (
                            "Custo salarial recorrente deve ser configurado "
                            "no cadastro do servidor."
                        )
                    }
                )
            if (
                dados_custo["valor_pago"] > Decimal("0.00")
                or dados_custo["baixado_manualmente"]
            ):
                raise ValidationError(
                    {
                        "valor_pago": (
                            "Plano recorrente deve ser criado sem pagamento; "
                            "liquide a ocorrência materializada."
                        )
                    }
                )
            inicio = dados_custo["data_vencimento"].replace(day=1)
            fim = None
            if not _boolean_payload_value(
                payload,
                "openEnded",
                "sem_data_fim",
                default=False,
            ):
                ultima_competencia = adicionar_meses_competencia(
                    inicio,
                    dados_custo["quantidade_meses"] - 1,
                )
                fim = date(
                    ultima_competencia.year,
                    ultima_competencia.month,
                    calendar.monthrange(
                        ultima_competencia.year,
                        ultima_competencia.month,
                    )[1],
                )
            autorizacao = _date_payload_value(
                payload,
                "authorizedMaterializationDate",
                "authorizedMaterializationDate",
                "data_autorizacao_materializacao",
            )
            if autorizacao is None:
                raise ValidationError(
                    {
                        "authorizedMaterializationDate": (
                            "Informe explicitamente a data autorizada."
                        )
                    }
                )
            idempotency_key = parsear_chave_idempotencia(
                request.headers.get("Idempotency-Key")
            )
            dados_plano = {
                    "descricao": dados_custo["descricao"],
                    "categoria": dados_custo["categoria"],
                    "origem": PlanoCustoRecorrente.ORIGEM_COMUM,
                    "periodicidade": PlanoCustoRecorrente.PERIODICIDADE_MENSAL,
                    "valor_previsto": dados_custo["valor_previsto"],
                    "data_inicio": inicio,
                    "data_fim": fim,
                    "dia_vencimento": dados_custo["data_vencimento"].day,
                    "data_autorizacao_materializacao": autorizacao,
                    "ativo": dados_custo["ativo"],
                    "observacao": dados_custo["observacao"],
            }

            def criar_plano_compatibilidade():
                plano_criado, materializacao_criada = criar_plano_recorrente(
                    dados=dados_plano,
                    usuario=request.user,
                    materializar_atual=True,
                )
                materializacao_segura = (
                    {
                        chave: valor
                        for chave, valor in materializacao_criada.items()
                        if chave != "value"
                    }
                    if materializacao_criada
                    else None
                )
                return (
                    {
                        "planId": plano_criado.pk,
                        "materialization": materializacao_segura,
                    },
                    201,
                )

            resultado_idempotente, _, replayed = executar_requisicao_idempotente(
                escopo="criar-plano-via-custo-fixo",
                chave=idempotency_key,
                payload=payload,
                ator=request.user,
                operacao=criar_plano_compatibilidade,
            )
            plano = PlanoCustoRecorrente.objects.get(
                pk=resultado_idempotente["planId"]
            )
            materializacao = resultado_idempotente["materialization"]
            custo_fixo = (
                CustoFixo.objects.get(pk=materializacao["fixedCostId"])
                if materializacao and materializacao["status"] == "created"
                else None
            )
        else:
            plano = None
            materializacao = None
            custo_fixo = CustoFixo(**dados_custo)
            custo_fixo.criado_por = request.user
            custo_fixo.atualizado_por = request.user
            custo_fixo.full_clean()
            custo_fixo.save()
    except (ChaveIdempotenciaInvalida, ConflitoChaveIdempotencia) as error:
        return api_no_store_json_response(
            {"errors": {"Idempotency-Key": [str(error)]}},
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
            {"errors": {"detail": ["Nao foi possivel cadastrar o custo fixo."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    response = api_no_store_json_response(
        {
            "data": {
                "fixedCost": _serialize_custo_fixo(custo_fixo) if custo_fixo else None,
                "recurringPlan": (
                    {
                        "id": plano.pk,
                        "description": plano.descricao,
                        "category": plano.categoria,
                        "plannedAmount": _money(plano.valor_previsto),
                        "startDate": plano.data_inicio.isoformat(),
                        "endDate": plano.data_fim.isoformat() if plano.data_fim else None,
                        "dueDay": plano.dia_vencimento,
                        "authorizedMaterializationDate": (
                            plano.data_autorizacao_materializacao.isoformat()
                        ),
                        "isActive": plano.ativo,
                    }
                    if plano
                    else None
                ),
                "materialization": materializacao,
                "message": (
                    "Plano recorrente cadastrado com sucesso."
                    if plano
                    else "Custo fixo cadastrado com sucesso."
                ),
            }
        },
        status=201,
        json_dumps_params={"ensure_ascii": False},
    )
    if plano:
        response["Idempotency-Replayed"] = "true" if replayed else "false"
    return response


def _atualizar_custo_fixo_response(request, custo_fixo):
    assert_demo_write_allowed(
        request.user,
        custo_fixo,
        operation="change_fixed_cost",
    )
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    try:
        for field, value in _custo_fixo_data_from_payload(payload).items():
            setattr(custo_fixo, field, value)

        custo_fixo.atualizado_por = request.user
        custo_fixo.full_clean()
        custo_fixo.save()
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"detail": ["Nao foi possivel atualizar o custo fixo."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "fixedCost": _serialize_custo_fixo(custo_fixo),
                "message": "Custo fixo atualizado com sucesso.",
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_http_methods(["GET", "POST"])
@extend_schema(
    methods=["GET"],
    responses={
        200: FixedCostListResponseSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["POST"],
    parameters=[
        OpenApiParameter(
            name="Idempotency-Key",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Obrigatória quando isRecurring=true.",
        ),
        OpenApiParameter(
            name="Idempotency-Replayed",
            type=str,
            location=OpenApiParameter.HEADER,
            response=[201],
            description="Indica replay da criação recorrente compatível.",
        ),
    ],
    request=FixedCostPayloadSerializer,
    responses={
        201: FixedCostMutationResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        415: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_custos_fixos(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in (
            "Cache-Control",
            "Expires",
            "Idempotency-Replayed",
        ):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    django_request = getattr(request, "_request", request)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_FIXED_COST_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        return drf_response_from_json_response(_custos_fixos_response(django_request))

    if not request.user.has_perm(ADD_FIXED_COST_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    return drf_response_from_json_response(_criar_custo_fixo_response(django_request))


@require_http_methods(["GET", "PUT"])
@extend_schema(
    methods=["GET"],
    operation_id="custos_fixos_detalhe_retrieve",
    responses={
        200: FixedCostDetailResponseSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="custos_fixos_detalhe_update",
    request=FixedCostPayloadSerializer,
    responses={
        200: FixedCostMutationResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        415: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_custo_fixo_detalhe(request, pk):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    def django_not_found_response():
        django_request = getattr(request, "_request", request)
        exception = Http404("No CustoFixo matches the given query.")
        return page_not_found(django_request, exception)

    django_request = getattr(request, "_request", request)
    custos_visiveis = CustoFixo.objects.all()
    if not request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION):
        custos_visiveis = custos_visiveis.exclude(
            Q(origem_recorrencia="salario") | Q(categoria="salario")
        )

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_FIXED_COST_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        try:
            custo_fixo = get_object_or_404(custos_visiveis, pk=pk)
        except Http404:
            return django_not_found_response()

        return drf_response_from_json_response(
            _custo_fixo_detalhe_response(django_request, custo_fixo)
        )

    if not request.user.has_perm(CHANGE_FIXED_COST_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        custo_fixo = get_object_or_404(custos_visiveis, pk=pk)
    except Http404:
        return django_not_found_response()

    if custo_fixo.origem_recorrencia == "salario":
        return drf_response_from_json_response(
            api_no_store_json_response(
                {
                    "errors": {
                        "detail": [
                            "A ocorrência salarial é derivada; altere contrato e salário no cadastro do servidor."
                        ]
                    }
                },
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    return drf_response_from_json_response(
        _atualizar_custo_fixo_response(django_request, custo_fixo)
    )
