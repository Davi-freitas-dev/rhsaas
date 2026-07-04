from collections import defaultdict
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Max, Sum
from django.utils import timezone

from .models import DespesaOperacional, Evento
from .models_custo_fixo import CustoFixo
from .models_fci import Investimento
from .constants_nomenclatura import montar_metadados_nomenclatura_financeira
from .selectors_dashboard_contexto import STATUS_DASHBOARD_FILTRO
from .selectors_dashboard import montar_contexto_custos_por_evento, montar_dados_dashboard
from .selectors_dashboard_filtros import querysets_dashboard_filtrados
from .selectors_obrigacoes import resumir_obrigacoes_financeiras
from .selectors_lancamentos import (
    calcular_diferencas_totais,
    calcular_totais_lancamentos_financeiros,
    calcular_totais_realizados_legados_dashboard,
)
from .selectors_opcoes_filtros import montar_opcoes_eventos_clientes_filtro
from .serializers_dimensoes_operacionais import (
    serializar_dimensao_operacional,
    serializar_opcoes_entidades_operacionais,
)
from .serializers_lancamentos import serializar_totais
from .serializers_obrigacoes import (
    listar_obrigacoes_com_fonte_leitura_visual,
    normalizar_filtros_obrigacoes,
)
from .services_dimensoes_operacionais import serializar_dimensao_operacional_financeira
from .services_posicao_caixa import montar_posicao_caixa_periodo
from .utils_financeiros import decimal_zero, quantizar_moeda
from .utils_fluxos_caixa import calcular_saldo_inicial_fluxo_caixa, normalizar_fluxo_caixa
from .utils_moeda import formatar_moeda_br


MESES_CURTOS = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)
MESES_COMPLETOS = (
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)
CORES_CATEGORIAS = (
    "#2563EB",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#06B6D4",
    "#64748B",
)


def montar_payload_dashboard_financial_overview_api(filtros, session):
    dados_dashboard = montar_dados_dashboard(filtros, session)
    totais_basicos = dados_dashboard["totais_basicos"]
    totais_financeiros = dados_dashboard["totais_financeiros"]
    totais_movimentacoes = dados_dashboard["totais_movimentacoes"]
    querysets = dados_dashboard["querysets"]
    filtros_dashboard = dados_dashboard["filtros_dashboard"]
    realized_cash_flow = montar_realized_cash_flow_dashboard(
        filtros_dashboard,
        totais_financeiros,
    )
    comparativo = montar_comparativo_dashboard(filtros_dashboard, session)

    movimentacoes = totais_movimentacoes["movimentacoes"]
    contas_a_pagar = montar_contas_a_pagar_dashboard(movimentacoes)
    contas_vencidas_all_time = montar_contas_vencidas_all_time_dashboard(
        filtros_dashboard
    )
    contas_a_receber = montar_contas_a_receber_dashboard(
        querysets["receitas"],
        filtros_dashboard,
    )
    resumo_servicos_anterior = (
        montar_resumo_receitas_servico(
            comparativo["totais_basicos"],
            comparativo["querysets"],
        )
        if comparativo
        else None
    )
    receitas_servico_anterior = mapa_receitas_servico_anterior(
        resumo_servicos_anterior
    )
    resumo_servicos = montar_resumo_receitas_servico(
        totais_basicos,
        querysets,
        receitas_servico_anterior=receitas_servico_anterior,
    )
    receitas_servico = resumo_servicos["receitas_servico"]
    disponibilidade_caixa = montar_disponibilidade_caixa_dashboard(
        filtros_dashboard,
        totais_movimentacoes,
    )

    total_despesa_prevista = decimal_para_numero(
        totais_movimentacoes["total_saida_movimentacoes_prevista"]
    )
    deficit_caixa = decimal_para_numero(totais_movimentacoes["deficit_caixa_movimentacoes"])
    contas_pendentes_total = decimal_para_numero(
        totais_movimentacoes["total_contas_pendentes_movimentacoes"]
    )
    payload = {
        "total_despesa_prevista": total_despesa_prevista,
        "totalDespesaPrevista": total_despesa_prevista,
        "kpis": montar_kpis_dashboard(
            totais_basicos,
            totais_financeiros,
            totais_movimentacoes,
            comparativo=comparativo,
        ),
        "resultadoFinanceiro": montar_resultado_financeiro_api(
            totais_financeiros,
            totais_movimentacoes,
            realized_cash_flow,
        ),
        "cashDeficitAmount": deficit_caixa,
        "pendingAccountsAmount": contas_pendentes_total,
        "deficitCaixa": deficit_caixa,
        "contasPendentesTotal": contas_pendentes_total,
        "cashAvailability": montar_payload_disponibilidade_caixa_dashboard(
            disponibilidade_caixa,
            totais_movimentacoes,
        ),
        "revenueExpense": montar_receitas_despesas_por_mes(movimentacoes, filtros_dashboard),
        "operationalRevenueExpense": montar_receitas_despesas_operacionais_por_mes(
            movimentacoes,
            filtros_dashboard,
        ),
        "expenseCategories": montar_despesas_por_categoria(querysets, totais_financeiros),
        "serviceRevenue": receitas_servico,
        "accountsPayable": contas_a_pagar["itens"][:5],
        "overduePayablesAllTime": contas_vencidas_all_time,
        "accountsReceivable": contas_a_receber["itens"][:5],
        "contractSummary": resumo_servicos["contratos"],
        "financialIndicators": montar_indicadores_financeiros(
            totais_basicos,
            totais_financeiros,
            totais_movimentacoes,
            disponibilidade_caixa,
        ),
        "financialGoals": montar_metas_financeiras(totais_basicos, totais_movimentacoes),
        "cashEvolution": montar_evolucao_caixa(movimentacoes, filtros_dashboard),
        "cashFlow": montar_fluxo_caixa(
            totais_movimentacoes,
            disponibilidade_caixa,
        ),
        "summary": {
            "serviceRevenueTotalVariation": calcular_variacao_percentual_numero(
                resumo_servicos["total"],
                (resumo_servicos_anterior or {}).get("total")
                if resumo_servicos_anterior
                else None,
            ),
            "accountsPayableCount": contas_a_pagar["quantidade"],
            "accountsReceivableCount": contas_a_receber["quantidade"],
            "overduePayablesAllTimeCount": contas_vencidas_all_time["count"],
            "overduePayablesAllTimeAmount": contas_vencidas_all_time["amount"],
            "activeOperationalEventsCount": totais_financeiros[
                "eventos_operacionais_ativos"
            ],
            "activeContractsCount": totais_financeiros["eventos_abertos"],
            "pendingAccountsCount": contas_a_pagar["quantidade"],
        },
        "filterOptions": montar_opcoes_filtros_dashboard_api(),
        "meta": {
            "generatedAt": timezone.now().isoformat(),
            "source": "backend",
            "periodLabel": montar_rotulo_periodo(filtros_dashboard),
            "currency": "BRL",
            "nomenclature": montar_metadados_nomenclatura_financeira(),
            "cashFlowSemantics": serializar_semantica_fluxo_caixa_dashboard(),
        },
    }

    if realized_cash_flow is not None:
        payload["cashBasisRealizedFlow"] = realized_cash_flow["totals"]
        payload["competenceBasisRealizedFlow"] = realized_cash_flow["comparison"]["legacy"]
        payload["realizedCashFlow"] = realized_cash_flow["totals"]
        payload["realizedCashFlowComparison"] = realized_cash_flow["comparison"]

    return {"data": payload}


def montar_contas_vencidas_all_time_dashboard(filtros_dashboard):
    params = {
        "overdueScope": "all",
        "obligationType": "pagar",
        "dataSource": "canonical",
        "contractCode": filtros_dashboard.get("contrato_codigo", ""),
        "eventId": filtros_dashboard.get("evento_id", ""),
        "clientId": filtros_dashboard.get("cliente_id", ""),
    }
    filtros_obrigacoes = normalizar_filtros_obrigacoes(params)
    itens, fonte_dados = listar_obrigacoes_com_fonte_leitura_visual(
        filtros_obrigacoes
    )
    resumo = resumir_obrigacoes_financeiras(itens)

    return {
        "count": resumo["overdue_count"],
        "amount": decimal_para_numero(resumo["overdue_amount"]),
        "pendingAmount": decimal_para_numero(resumo["pending_amount"]),
        "referenceDate": timezone.localdate().isoformat(),
        "dateBasis": "dueDate",
        "overdueScope": "all",
        "periodIgnored": True,
        "filters": {
            "obligationType": "pagar",
            "contractCode": filtros_obrigacoes.get("contractCode") or "",
            "eventId": filtros_obrigacoes.get("eventId") or "",
            "clientId": filtros_obrigacoes.get("clientId") or "",
        },
        "readModel": {
            "requested": fonte_dados.get("requested") or "",
            "actual": fonte_dados.get("actual") or "",
        },
    }


def montar_payload_custos_por_evento_api(filtros, session):
    contexto = montar_contexto_custos_por_evento(filtros, session)
    grupos_raw = contexto["custos_por_evento"]
    eventos_info = _eventos_info_custos_por_evento(grupos_raw)
    grupos = [
        serializar_grupo_custos_por_evento_api(
            grupo,
            eventos_info.get(grupo["evento_id"], {}),
        )
        for grupo in grupos_raw
    ]

    return {
        "data": {
            "groups": grupos,
            "summary": {
                "eventsCount": len(grupos),
                "plannedCostAmount": decimal_para_numero(
                    contexto["total_custo_previsto_eventos"]
                ),
                "realizedCostAmount": decimal_para_numero(
                    contexto["total_pago_eventos"]
                ),
                "pendingCostAmount": decimal_para_numero(
                    contexto["total_valor_pendente_eventos"]
                ),
                "plannedRevenueAmount": decimal_para_numero(
                    contexto["total_receita_eventos_custos"]
                ),
                "realizedRevenueAmount": decimal_para_numero(
                    sum(
                        (grupo["receita_recebida_evento"] for grupo in grupos_raw),
                        Decimal("0.00"),
                    )
                ),
                "projectedResultAmount": decimal_para_numero(
                    contexto["total_lucro_previsto_eventos"]
                ),
                "realizedResultAmount": decimal_para_numero(
                    contexto["total_lucro_real_eventos"]
                ),
                "pendingItemsCount": sum(
                    grupo["pendingItemsCount"] for grupo in grupos
                ),
                "overdueItemsCount": sum(
                    grupo["overdueItemsCount"] for grupo in grupos
                ),
            },
            "filters": {
                **contexto["filtros"],
                "periodo_rapido": contexto["periodo_rapido"],
                "quickPeriod": contexto["periodo_rapido"],
            },
            "filterOptions": montar_opcoes_filtros_dashboard_api(),
            "pagination": {
                "limit": len(grupos),
                "offset": 0,
                "total": len(grupos),
                "hasMore": False,
            },
            "meta": {
                "generatedAt": timezone.now().isoformat(),
                "source": "backend",
                "currency": "BRL",
                "dateBasis": "eventStartDate",
                "requiredPermission": "caixa.view_evento",
                "periodLabel": montar_rotulo_periodo(
                    {
                        "data_inicial": contexto["filtros"].get("data_inicial"),
                        "data_final": contexto["filtros"].get("data_final"),
                    }
                ),
                "nomenclature": montar_metadados_nomenclatura_financeira(),
            },
        }
    }


def _eventos_info_custos_por_evento(grupos):
    ids = [grupo["evento_id"] for grupo in grupos if grupo.get("evento_id")]
    if not ids:
        return {}

    eventos = (
        Evento.objects.select_related("cliente", "orcamento")
        .filter(pk__in=ids)
        .only(
            "id",
            "numero",
            "nome_evento",
            "cliente__nome_razao_social",
            "orcamento__numero",
        )
    )
    eventos_info = {}
    for evento in eventos:
        dimensao = serializar_dimensao_operacional(evento)
        eventos_info[evento.id] = {
            "eventNumber": dimensao["eventNumber"],
            "eventName": dimensao["eventName"],
            "clientName": dimensao["clientName"],
            "contractLabel": dimensao["contractLabel"],
        }
    return eventos_info


def serializar_grupo_custos_por_evento_api(grupo, evento_info):
    itens = [
        serializar_item_custos_por_evento_api(grupo, item, index)
        for index, item in enumerate(grupo["itens"], start=1)
    ]
    service_cost_amount = sum(
        (
            como_decimal(item["plannedAmount"])
            for item in itens
            if item["source"] == "custo_servico"
        ),
        Decimal("0.00"),
    )
    extra_cost_amount = sum(
        (
            como_decimal(item["plannedAmount"])
            for item in itens
            if item["source"] == "custo_extra"
        ),
        Decimal("0.00"),
    )
    manual_cost_amount = sum(
        (
            como_decimal(item["plannedAmount"])
            for item in itens
            if item["source"] == "despesa_operacional"
        ),
        Decimal("0.00"),
    )
    event_number = evento_info.get("eventNumber") or ""
    event_name = evento_info.get("eventName") or grupo["evento_nome"] or ""
    event_label = " - ".join(parte for parte in [event_number, event_name] if parte)

    return {
        "key": f"event-{grupo['evento_id']}",
        "eventId": grupo["evento_id"],
        "eventName": event_name,
        "eventNumber": event_number,
        "eventLabel": event_label or event_name or "Evento sem identificacao",
        "clientName": evento_info.get("clientName") or "",
        "contractLabel": evento_info.get("contractLabel") or event_number,
        "firstDueDate": serializar_data_iso_custos_evento(grupo["data_inicio"]),
        "plannedCostAmount": decimal_para_numero(grupo["subtotal_geral"]),
        "realizedCostAmount": decimal_para_numero(grupo["subtotal_pago_geral"]),
        "pendingCostAmount": decimal_para_numero(
            grupo["subtotal_valor_pendente_geral"]
        ),
        "plannedRevenueAmount": decimal_para_numero(grupo["receita_evento"]),
        "realizedRevenueAmount": decimal_para_numero(
            grupo["receita_recebida_evento"]
        ),
        "projectedResultAmount": decimal_para_numero(grupo["lucro_previsto"]),
        "realizedResultAmount": decimal_para_numero(grupo["lucro_real"]),
        "pendingItemsCount": sum(1 for item in itens if item["pendingAmount"] > 0),
        "overdueItemsCount": sum(1 for item in itens if item["isOverdue"]),
        "serviceCostAmount": decimal_para_numero(service_cost_amount),
        "dailyAmount": decimal_para_numero(grupo["subtotal_diarias"]),
        "foodAmount": decimal_para_numero(grupo["subtotal_alimentacao"]),
        "transportAmount": decimal_para_numero(grupo["subtotal_transporte"]),
        "extraCostAmount": decimal_para_numero(extra_cost_amount),
        "manualCostAmount": decimal_para_numero(manual_cost_amount),
        "serviceCostBreakdown": serializar_breakdown_custos_por_evento_api(
            grupo.get("custos_servico_breakdown", [])
        ),
        "extraCostBreakdown": serializar_breakdown_custos_por_evento_api(
            grupo.get("custos_extras_breakdown", [])
        ),
        "manualCostBreakdown": serializar_breakdown_custos_por_evento_api(
            grupo.get("despesas_manuais_breakdown", [])
        ),
        "items": itens,
    }


def serializar_breakdown_custos_por_evento_api(breakdown):
    return [
        {
            "category": item.get("category") or "",
            "categoryLabel": item.get("categoryLabel") or item.get("category") or "",
            "plannedAmount": decimal_para_numero(item.get("plannedAmount")),
            "realizedAmount": decimal_para_numero(item.get("realizedAmount")),
            "pendingAmount": decimal_para_numero(item.get("pendingAmount")),
            "items": [
                {
                    "description": detalhe.get("description") or "",
                    "plannedAmount": decimal_para_numero(detalhe.get("plannedAmount")),
                    "realizedAmount": decimal_para_numero(detalhe.get("realizedAmount")),
                    "pendingAmount": decimal_para_numero(detalhe.get("pendingAmount")),
                }
                for detalhe in item.get("items", [])
            ],
        }
        for item in breakdown
    ]


def serializar_item_custos_por_evento_api(grupo, item, index):
    source = source_item_custos_por_evento(item)
    pending_amount = decimal_para_numero(
        item.get("valor_pendente_total", item.get("saldo_total"))
    )
    due_date = grupo["data_inicio"]
    is_overdue = bool(
        pending_amount > 0
        and due_date
        and due_date < timezone.localdate()
    )

    return {
        "id": f"{source}:{grupo['evento_id']}:{index}",
        "source": source,
        "sourceLabel": rotulo_source_custos_por_evento(source),
        "sourceDetailLabel": "",
        "description": item.get("servico__nome") or "Custo do evento",
        "dueDate": serializar_data_iso_custos_evento(due_date),
        "status": "pendente" if pending_amount > 0 else "liquidado",
        "statusLabel": "Pendente" if pending_amount > 0 else "Liquidado",
        "plannedAmount": decimal_para_numero(item["total_geral"]),
        "realizedAmount": decimal_para_numero(item.get("pago_total")),
        "pendingAmount": pending_amount,
        "isOverdue": is_overdue,
    }


def source_item_custos_por_evento(item):
    if item.get("eh_custo_extra"):
        return "custo_extra"

    if item.get("eh_despesa_manual"):
        return "despesa_operacional"

    return "custo_servico"


def rotulo_source_custos_por_evento(source):
    return {
        "custo_servico": "Custo de servico",
        "custo_extra": "Custo extra",
        "despesa_operacional": "Despesa operacional",
    }[source]


def serializar_data_iso_custos_evento(valor):
    if not valor:
        return ""

    if hasattr(valor, "isoformat"):
        return valor.isoformat()

    return str(valor)


def montar_comparativo_dashboard(filtros_dashboard, session):
    periodo_anterior = resolver_periodo_comparacao_anterior(filtros_dashboard)
    if not periodo_anterior:
        return None

    dados_anteriores = montar_dados_dashboard(
        params_periodo_comparacao(periodo_anterior, filtros_dashboard),
        session,
    )
    return {
        "periodo": periodo_anterior,
        **dados_anteriores,
    }


def resolver_periodo_comparacao_anterior(filtros_dashboard):
    data_inicial = parse_date(filtros_dashboard.get("data_inicial"))
    data_final = parse_date(filtros_dashboard.get("data_final"))

    if (
        not data_inicial
        or not data_final
        or filtros_dashboard.get("periodo_rapido") in {"todos", "vencidos"}
    ):
        return None

    data_referencia = data_mais_recente_antes_do_periodo(
        filtros_dashboard,
        data_inicial,
    )
    if not data_referencia:
        return None

    if periodo_e_mes_completo(data_inicial, data_final):
        data_comparacao_inicial = data_referencia.replace(day=1)
        ultimo_dia = calendar.monthrange(data_referencia.year, data_referencia.month)[1]
        data_comparacao_final = data_referencia.replace(day=ultimo_dia)
    else:
        dias_periodo = (data_final - data_inicial).days
        data_comparacao_final = data_referencia
        data_comparacao_inicial = data_referencia - timedelta(days=dias_periodo)

    return {
        "data_inicial": data_comparacao_inicial,
        "data_final": data_comparacao_final,
    }


def periodo_e_mes_completo(data_inicial, data_final):
    if data_inicial.year != data_final.year or data_inicial.month != data_final.month:
        return False
    ultimo_dia = calendar.monthrange(data_inicial.year, data_inicial.month)[1]
    return data_inicial.day == 1 and data_final.day == ultimo_dia


def data_mais_recente_antes_do_periodo(filtros_dashboard, data_inicial):
    filtros_busca = {
        "data_inicial": "",
        "data_final": (data_inicial - timedelta(days=1)).isoformat(),
        "evento_id": filtros_dashboard.get("evento_id", ""),
        "cliente_id": filtros_dashboard.get("cliente_id", ""),
        "contrato_codigo": filtros_dashboard.get("contrato_codigo", ""),
        "status": filtros_dashboard.get("status", ""),
        "periodo_rapido": "",
    }
    querysets = querysets_dashboard_filtrados(filtros_busca)
    datas = [
        maior_data_queryset(querysets["receitas"], "data_vencimento"),
        maior_data_queryset(querysets["despesas"], "data_vencimento"),
        maior_data_queryset(querysets["custos_fixos"], "data_vencimento"),
        maior_data_queryset(querysets["investimentos"], "data_prevista"),
        maior_data_queryset(querysets["parcelas_divida"], "data_vencimento_atual"),
        maior_data_queryset(querysets["financiamentos"], "data_prevista"),
        maior_data_queryset(querysets["custos_evento"], "evento__data_inicio"),
        maior_data_queryset(querysets["custos_extras"], "evento__data_inicio"),
    ]
    datas = [item for item in datas if item]
    return max(datas) if datas else None


def maior_data_queryset(queryset, campo):
    return queryset.aggregate(data=Max(campo))["data"]


def params_periodo_comparacao(periodo_anterior, filtros_dashboard):
    params = {
        "data_inicial": periodo_anterior["data_inicial"].isoformat(),
        "data_final": periodo_anterior["data_final"].isoformat(),
        "evento": filtros_dashboard.get("evento_id", ""),
        "cliente": filtros_dashboard.get("cliente_id", ""),
        "status": filtros_dashboard.get("status", ""),
        "periodo_rapido": "",
    }
    contrato_codigo = filtros_dashboard.get("contrato_codigo", "")
    if contrato_codigo:
        params["contractCode"] = contrato_codigo
    return params


def mapa_receitas_servico_anterior(resumo_servicos_anterior):
    if not resumo_servicos_anterior:
        return {}
    return {
        item["serviceName"]: como_decimal(item["revenueAmount"])
        for item in resumo_servicos_anterior["receitas_servico"]
    }


def serializar_semantica_fluxo_caixa_dashboard():
    return {
        "version": "dashboard-cash-flow-semantics-v1",
        "scope": "dashboardFinancialOverview",
        "currency": "BRL",
        "dateBasis": "selectedPeriod",
        "fields": {
            "initialCashAmount": {
                "businessTerm": "Saldo inicial",
                "meaning": (
                    "Saldo inicial considerado para o card de fluxo de caixa da "
                    "janela filtrada."
                ),
            },
            "inflowAmount": {
                "businessTerm": "Entradas",
                "meaning": "Entradas previstas/projetadas dentro do periodo filtrado.",
            },
            "realizedInflowAmount": {
                "businessTerm": "Entradas recebidas",
                "meaning": (
                    "Entradas efetivamente recebidas dentro do periodo filtrado, "
                    "pela data efetiva de lancamento."
                ),
            },
            "outflowAmount": {
                "businessTerm": "Saidas",
                "meaning": "Saidas previstas/projetadas dentro do periodo filtrado.",
            },
            "realizedOutflowAmount": {
                "businessTerm": "Saidas pagas",
                "meaning": (
                    "Saidas efetivamente pagas dentro do periodo filtrado, "
                    "pela data efetiva de lancamento."
                ),
            },
            "financialResultAmount": {
                "businessTerm": "Resultado financeiro",
                "meaning": (
                    "Resultado consolidado do periodo, somando FCO, FCI e FCF."
                ),
                "formula": "inflowAmount - outflowAmount",
            },
            "periodRealizedAmount": {
                "businessTerm": "Resultado efetivo do periodo",
                "meaning": (
                    "Resultado de caixa do periodo: entradas efetivamente "
                    "recebidas menos saidas efetivamente pagas."
                ),
                "formula": "realizedInflowAmount - realizedOutflowAmount",
            },
            "cashDeficitAmount": {
                "businessTerm": "Déficit de caixa",
                "meaning": (
                    "Falta de caixa projetada no fluxo acumulado da janela, "
                    "considerando a ordem dos vencimentos e a cobertura por entradas."
                ),
            },
            "availableCashAmount": {
                "businessTerm": "Caixa do periodo",
                "meaning": (
                    "Caixa final disponivel do periodo: saldo inicial + "
                    "entradas efetivamente recebidas - saidas efetivamente "
                    "pagas."
                ),
                "formula": (
                    "initialCashAmount + realizedInflowAmount "
                    "- realizedOutflowAmount"
                ),
            },
            "finalCashAmount": {
                "businessTerm": "Caixa final do periodo",
                "meaning": (
                    "Mesmo conceito de availableCashAmount quando o rotulo "
                    "visual for Caixa disponivel."
                ),
                "formula": (
                    "initialCashAmount + realizedInflowAmount "
                    "- realizedOutflowAmount"
                ),
            },
            "currentAvailableCashAmount": {
                "businessTerm": "Caixa disponivel atual",
                "meaning": (
                    "Caixa efetivo disponivel ate hoje, independente do periodo "
                    "filtrado no card."
                ),
                "formula": (
                    "accumulatedEffectiveInflowsUntilToday "
                    "- accumulatedEffectiveOutflowsUntilToday"
                ),
            },
            "accumulatedCashUntilDate": {
                "businessTerm": "Caixa acumulado ate a data",
                "meaning": (
                    "Caixa efetivo acumulado ate a data final efetiva do filtro, "
                    "preservado para validacao e diagnostico."
                ),
                "formula": (
                    "accumulatedEffectiveInflowsUntilDate "
                    "- accumulatedEffectiveOutflowsUntilDate"
                ),
            },
            "accumulatedAvailableCashAmount": {
                "businessTerm": "Caixa acumulado para pagamento",
                "meaning": (
                    "Caixa efetivo acumulado ate a data final do filtro, usado "
                    "pela validacao de cobertura de pagamentos."
                ),
                "formula": "accumulatedEffectiveInflowsUntilDate - accumulatedEffectiveOutflowsUntilDate",
            },
            "pendingAccountsAmount": {
                "businessTerm": "Contas pendentes",
                "meaning": (
                    "Total de obrigacoes do periodo que ainda nao foram liquidadas."
                ),
            },
        },
        "rules": {
            "financialResultFormula": "inflowAmount - outflowAmount",
            "finalCashFormula": (
                "initialCashAmount + realizedInflowAmount "
                "- realizedOutflowAmount"
            ),
            "cashDeficitIsNotPendingAccounts": True,
            "cashDeficitMeaning": (
                "Déficit de caixa mede falta de cobertura no fluxo acumulado; "
                "contas pendentes mede obrigações ainda não liquidadas."
            ),
        },
        "aliases": {
            "saldoInicial": "initialCashAmount",
            "entradas": "inflowAmount",
            "saidas": "outflowAmount",
            "saldoFinal": "financialResultAmount",
            "resultadoFinanceiro": "financialResultAmount",
            "deficitCaixa": "cashDeficitAmount",
            "contasPendentes": "pendingAccountsAmount",
            "caixaDisponivel": "availableCashAmount",
        },
    }


def montar_disponibilidade_caixa_dashboard(
    filtros_dashboard,
    totais_movimentacoes=None,
):
    return montar_posicao_caixa_periodo(
        filtros_dashboard,
        totais_movimentacoes=totais_movimentacoes,
    )


def montar_payload_disponibilidade_caixa_dashboard(
    disponibilidade_caixa,
    totais_movimentacoes,
):
    caixa_disponivel = disponibilidade_caixa["finalCashAmount"]
    caixa_disponivel_acumulado = disponibilidade_caixa["accumulatedCashUntilDate"]
    resultado_realizado_periodo = disponibilidade_caixa["periodRealizedAmount"]
    diferenca_resultado_periodo = disponibilidade_caixa[
        "differenceFromPeriodRealizedAmount"
    ]

    return {
        "initialCashAmount": decimal_para_numero(
            disponibilidade_caixa["initialCashAmount"]
        ),
        "saldoInicial": decimal_para_numero(
            disponibilidade_caixa["initialCashAmount"]
        ),
        "realizedInflowAmount": decimal_para_numero(
            disponibilidade_caixa["realizedInflowAmount"]
        ),
        "realizedOutflowAmount": decimal_para_numero(
            disponibilidade_caixa["realizedOutflowAmount"]
        ),
        "availableCashAmount": decimal_para_numero(caixa_disponivel),
        "cashAvailableAmount": decimal_para_numero(caixa_disponivel),
        "caixaDisponivel": decimal_para_numero(caixa_disponivel),
        "saldoCaixaDisponivel": decimal_para_numero(caixa_disponivel),
        "finalCashAmount": decimal_para_numero(caixa_disponivel),
        "currentAvailableCashAmount": decimal_para_numero(
            disponibilidade_caixa["currentAvailableCashAmount"]
        ),
        "accumulatedCashUntilDate": decimal_para_numero(caixa_disponivel_acumulado),
        "accumulatedAvailableCashAmount": decimal_para_numero(
            caixa_disponivel_acumulado
        ),
        "cashAvailableUntilDate": disponibilidade_caixa["cashAvailableUntilDate"],
        "currentCashAvailableUntilDate": disponibilidade_caixa[
            "currentCashAvailableUntilDate"
        ],
        "periodRealizedAmount": decimal_para_numero(resultado_realizado_periodo),
        "differenceFromPeriodRealizedAmount": decimal_para_numero(
            diferenca_resultado_periodo
        ),
        "formula": (
            "initialCashAmount + realizedInflowAmount - realizedOutflowAmount"
        ),
        "accumulatedFormula": (
            "accumulatedEffectiveInflowsUntilDate "
            "- accumulatedEffectiveOutflowsUntilDate"
        ),
        "periodRealizedFormula": (
            "realizedFcoAmount + realizedFciAmount + realizedFcfAmount"
        ),
        "finalCashFormula": (
            "initialCashAmount + realizedFcoAmount + realizedFciAmount "
            "+ realizedFcfAmount"
        ),
    }


def montar_realized_cash_flow_dashboard(filtros_dashboard, totais_financeiros):
    if filtros_dashboard.get("status"):
        return None

    totais_lancamentos = calcular_totais_lancamentos_financeiros(filtros_dashboard)
    totais_legados = calcular_totais_realizados_legados_dashboard(totais_financeiros)
    diferencas = calcular_diferencas_totais(totais_legados, totais_lancamentos)

    return {
        "rawTotals": totais_lancamentos,
        "totals": serializar_totais(totais_lancamentos),
        "comparison": serializar_comparacao_realized_cash_flow(
            totais_legados,
            diferencas,
        ),
    }


def serializar_comparacao_realized_cash_flow(totais_legados, diferencas):
    return {
        "equivalent": all(valor == Decimal("0.00") for valor in diferencas.values()),
        "legacy": serializar_totais(totais_legados),
        "differences": serializar_diferencas_realized_cash_flow(diferencas),
        "dateBasis": {
            "legacyFcf": "data_vencimento_atual",
            "ledger": "data_lancamento",
        },
    }


def serializar_diferencas_realized_cash_flow(diferencas):
    return {
        "entradas": decimal_para_numero(diferencas["entradas"]),
        "saidas": decimal_para_numero(diferencas["saidas"]),
        "resultadoFinanceiro": decimal_para_numero(
            diferencas["resultado_financeiro"]
        ),
        "resultado_financeiro": decimal_para_numero(
            diferencas["resultado_financeiro"]
        ),
        "cashFlows": {
            fluxo: {
                "entradas": decimal_para_numero(diferencas[f"{fluxo}_entradas"]),
                "saidas": decimal_para_numero(diferencas[f"{fluxo}_saidas"]),
                "resultadoFinanceiro": decimal_para_numero(
                    diferencas[f"{fluxo}_resultado_financeiro"]
                ),
                "resultado_financeiro": decimal_para_numero(
                    diferencas[f"{fluxo}_resultado_financeiro"]
                ),
            }
            for fluxo in ("fco", "fci", "fcf")
        },
    }


def montar_kpis_dashboard(
    totais_basicos,
    totais_financeiros,
    totais_movimentacoes,
    comparativo=None,
):
    valores = valores_kpis_dashboard(
        totais_basicos,
        totais_financeiros,
        totais_movimentacoes,
    )
    valores_anteriores = (
        valores_kpis_dashboard(
            comparativo["totais_basicos"],
            comparativo["totais_financeiros"],
            comparativo["totais_movimentacoes"],
        )
        if comparativo
        else None
    )
    variacoes = variacoes_kpis_dashboard(valores, valores_anteriores)
    rotulo_comparacao = (
        montar_rotulo_comparacao_anterior(comparativo["filtros_dashboard"])
        if comparativo
        else "sem comparação"
    )

    return {
        "receitaTotal": metrica_numero(
            valores["receita_total"],
            variacao=variacoes["receita_total"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "receitaOperacional": metrica_numero(
            valores["receita_operacional"],
            variacao=variacoes["receita_operacional"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "despesasTotais": metrica_numero(
            valores["despesas_totais"],
            variacao=variacoes["despesas_totais"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "lucroLiquido": metrica_numero(
            valores["lucro_liquido"],
            variacao=variacoes["lucro_liquido"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "margemLiquida": {
            **metrica_numero(
                valores["margem_liquida"],
                casas=1,
                variacao=variacoes["margem_liquida"],
                rotulo_variacao=rotulo_comparacao,
            ),
            "unit": "p.p.",
        },
        "custoVariavel": metrica_numero(
            valores["custo_variavel"],
            variacao=variacoes["custo_variavel"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "margemContribuicao": metrica_numero(
            valores["margem_contribuicao"],
            variacao=variacoes["margem_contribuicao"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "margemContribuicaoPercentual": {
            **metrica_numero(
                valores["margem_contribuicao_percentual"],
                casas=1,
                variacao=variacoes["margem_contribuicao_percentual"],
                rotulo_variacao=rotulo_comparacao,
            ),
            "unit": "p.p.",
        },
        "lucroOperacionalEbit": metrica_numero(
            valores["lucro_operacional_ebit"],
            variacao=variacoes["lucro_operacional_ebit"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "resultadoFinanceiro": metrica_numero(
            valores["resultado_financeiro"],
            variacao=variacoes["resultado_financeiro"],
            rotulo_variacao=rotulo_comparacao,
        ),
        "saldoCaixa": metrica_numero(
            valores["resultado_financeiro"],
            variacao=variacoes["resultado_financeiro"],
            rotulo_variacao=rotulo_comparacao,
        ),
    }


def valores_kpis_dashboard(totais_basicos, totais_financeiros, totais_movimentacoes):
    receita_total = totais_basicos["receita_prevista"]
    receita_operacional = totais_movimentacoes["fluxos_caixa"]["fco"][
        "entrada_prevista"
    ]
    despesas_totais = totais_movimentacoes["total_saida_movimentacoes_prevista"]
    resultado_financeiro = totais_movimentacoes["resultado_financeiro_movimentacoes"]
    lucro_liquido = receita_total - despesas_totais
    margem_liquida = percentual(lucro_liquido, receita_total)

    return {
        "receita_total": receita_total,
        "receita_operacional": receita_operacional,
        "despesas_totais": despesas_totais,
        "lucro_liquido": lucro_liquido,
        "margem_liquida": Decimal(str(margem_liquida)),
        "margem_liquida_valida": receita_total > Decimal("0.00"),
        "custo_variavel": totais_financeiros["custo_variavel"],
        "margem_contribuicao": totais_financeiros["margem_contribuicao"],
        "margem_contribuicao_percentual": totais_financeiros[
            "margem_contribuicao_percentual"
        ],
        "margem_contribuicao_percentual_valida": receita_total > Decimal("0.00"),
        "lucro_operacional_ebit": totais_financeiros["lucro_operacional_ebit"],
        "resultado_financeiro": resultado_financeiro,
    }


def variacoes_kpis_dashboard(valores, valores_anteriores):
    if not valores_anteriores:
        return {
            "receita_total": None,
            "receita_operacional": None,
            "despesas_totais": None,
            "lucro_liquido": None,
            "margem_liquida": None,
            "custo_variavel": None,
            "margem_contribuicao": None,
            "margem_contribuicao_percentual": None,
            "lucro_operacional_ebit": None,
            "resultado_financeiro": None,
        }

    return {
        "receita_total": calcular_variacao_percentual(
            valores["receita_total"],
            valores_anteriores["receita_total"],
        ),
        "receita_operacional": calcular_variacao_percentual(
            valores["receita_operacional"],
            valores_anteriores["receita_operacional"],
        ),
        "despesas_totais": calcular_variacao_percentual(
            valores["despesas_totais"],
            valores_anteriores["despesas_totais"],
        ),
        "lucro_liquido": calcular_variacao_percentual(
            valores["lucro_liquido"],
            valores_anteriores["lucro_liquido"],
        ),
        "margem_liquida": calcular_variacao_pontos_percentuais(
            valores["margem_liquida"] if valores["margem_liquida_valida"] else None,
            (
                valores_anteriores["margem_liquida"]
                if valores_anteriores["margem_liquida_valida"]
                else None
            ),
        ),
        "custo_variavel": calcular_variacao_percentual(
            valores["custo_variavel"],
            valores_anteriores["custo_variavel"],
        ),
        "margem_contribuicao": calcular_variacao_percentual(
            valores["margem_contribuicao"],
            valores_anteriores["margem_contribuicao"],
        ),
        "margem_contribuicao_percentual": calcular_variacao_pontos_percentuais(
            (
                valores["margem_contribuicao_percentual"]
                if valores["margem_contribuicao_percentual_valida"]
                else None
            ),
            (
                valores_anteriores["margem_contribuicao_percentual"]
                if valores_anteriores["margem_contribuicao_percentual_valida"]
                else None
            ),
        ),
        "lucro_operacional_ebit": calcular_variacao_percentual(
            valores["lucro_operacional_ebit"],
            valores_anteriores["lucro_operacional_ebit"],
        ),
        "resultado_financeiro": calcular_variacao_percentual(
            valores["resultado_financeiro"],
            valores_anteriores["resultado_financeiro"],
        ),
    }


def montar_resultado_financeiro_api(
    totais_financeiros,
    totais_movimentacoes,
    realized_cash_flow=None,
):
    totais_realizados = totais_realizados_dashboard_api(
        totais_financeiros,
        realized_cash_flow,
    )

    return {
        "projetado": decimal_para_numero(
            totais_movimentacoes["resultado_financeiro_movimentacoes"]
        ),
        "projectedAmount": decimal_para_numero(
            totais_movimentacoes["resultado_financeiro_movimentacoes"]
        ),
        "realizado": decimal_para_numero(
            totais_realizados["resultado_financeiro"]
        ),
        "realizedAmount": decimal_para_numero(
            totais_realizados["resultado_financeiro"]
        ),
        "consolidadoProjetado": decimal_para_numero(
            totais_financeiros["resultado_financeiro_consolidado_projetado"]
        ),
        "consolidatedProjectedAmount": decimal_para_numero(
            totais_financeiros["resultado_financeiro_consolidado_projetado"]
        ),
        "consolidadoRealizado": decimal_para_numero(
            totais_realizados["resultado_financeiro"]
        ),
        "consolidatedRealizedAmount": decimal_para_numero(
            totais_realizados["resultado_financeiro"]
        ),
        "operacionalProjetado": decimal_para_numero(
            totais_financeiros["resultado_financeiro_operacional_projetado"]
        ),
        "operationalProjectedAmount": decimal_para_numero(
            totais_financeiros["resultado_financeiro_operacional_projetado"]
        ),
        "operacionalRealizado": decimal_para_numero(
            totais_realizados["fco"]["resultado_financeiro"]
        ),
        "operationalRealizedAmount": decimal_para_numero(
            totais_realizados["fco"]["resultado_financeiro"]
        ),
        "investimentosRealizado": decimal_para_numero(
            totais_realizados["fci"]["resultado_financeiro"]
        ),
        "investmentRealizedAmount": decimal_para_numero(
            totais_realizados["fci"]["resultado_financeiro"]
        ),
        "financiamentosRealizado": decimal_para_numero(
            totais_realizados["fcf"]["resultado_financeiro"]
        ),
        "financingRealizedAmount": decimal_para_numero(
            totais_realizados["fcf"]["resultado_financeiro"]
        ),
        "realizedSource": totais_realizados["source"],
        "realizadoFonte": totais_realizados["source"],
        "deficitCaixa": decimal_para_numero(totais_movimentacoes["deficit_caixa_movimentacoes"]),
        "cashDeficitAmount": decimal_para_numero(totais_movimentacoes["deficit_caixa_movimentacoes"]),
        "contasPendentes": decimal_para_numero(
            totais_movimentacoes["total_contas_pendentes_movimentacoes"]
        ),
        "pendingAccountsAmount": decimal_para_numero(
            totais_movimentacoes["total_contas_pendentes_movimentacoes"]
        ),
    }


def totais_realizados_dashboard_api(totais_financeiros, realized_cash_flow=None):
    if realized_cash_flow is not None:
        return {
            **realized_cash_flow["rawTotals"],
            "source": "ledger",
        }

    return {
        **calcular_totais_realizados_legados_dashboard(totais_financeiros),
        "source": "legacy",
    }


def montar_receitas_despesas_por_mes(movimentacoes, filtros_dashboard):
    return [
        {
            "month": item["month"],
            "receitas": decimal_para_numero(item["entrada"]),
            "revenueAmount": decimal_para_numero(item["entrada"]),
            "despesas": decimal_para_numero(item["saida"]),
            "expenseAmount": decimal_para_numero(item["saida"]),
        }
        for item in agrupar_entradas_saidas_por_mes(movimentacoes)
    ]


def montar_receitas_despesas_operacionais_por_mes(movimentacoes, filtros_dashboard):
    return [
        {
            "month": item["month"],
            "operationalRevenueAmount": decimal_para_numero(item["entrada"]),
            "operationalExpenseAmount": decimal_para_numero(item["saida"]),
        }
        for item in agrupar_entradas_saidas_por_mes(
            movimentacoes,
            incluir_movimentacao=movimentacao_eh_fluxo_operacional,
        )
    ]


def agrupar_entradas_saidas_por_mes(movimentacoes, incluir_movimentacao=None):
    grupos = defaultdict(lambda: {"entrada": Decimal("0.00"), "saida": Decimal("0.00")})

    for movimentacao in movimentacoes:
        if incluir_movimentacao and not incluir_movimentacao(movimentacao):
            continue

        data_movimento = movimentacao["data"]
        if not data_movimento:
            continue

        chave = (data_movimento.year, data_movimento.month)
        grupos[chave]["entrada"] += decimal_zero(movimentacao.get("entrada"))
        grupos[chave]["saida"] += decimal_zero(movimentacao.get("saida"))

    return [
        {
            "month": formatar_mes_curto(ano, mes),
            "entrada": valores["entrada"],
            "saida": valores["saida"],
        }
        for (ano, mes), valores in sorted(grupos.items())
    ]


def movimentacao_eh_fluxo_operacional(movimentacao):
    fluxo_caixa = normalizar_fluxo_caixa(
        movimentacao.get("fluxo_caixa") or movimentacao.get("origem") or "FCO"
    )
    return fluxo_caixa == "fco"


def montar_evolucao_caixa(movimentacoes, filtros_dashboard):
    receitas_despesas = montar_receitas_despesas_por_mes(movimentacoes, filtros_dashboard)
    saldo = calcular_saldo_inicial_fluxo_caixa(
        filtros_dashboard.get("data_inicial")
    )
    evolucao = []

    for item in receitas_despesas:
        saldo += Decimal(str(item["receitas"]))
        saldo -= Decimal(str(item["despesas"]))
        evolucao.append({
            "month": item["month"],
            "value": decimal_para_numero(saldo),
            "accumulatedFinancialResult": decimal_para_numero(saldo),
            "accumulatedFinancialResultAmount": decimal_para_numero(saldo),
        })

    return evolucao


def montar_despesas_por_categoria(querysets, totais_financeiros):
    grupos = defaultdict(Decimal)
    labels_despesas = dict(DespesaOperacional.CATEGORIA_CHOICES)
    labels_custos_fixos = dict(CustoFixo.CATEGORIA_CHOICES)
    labels_investimentos = dict(Investimento.CATEGORIA_CHOICES)

    for item in querysets["despesas"].values("categoria").annotate(total=Sum("valor_previsto")):
        rotulo = labels_despesas.get(item["categoria"], item["categoria"])
        grupos[rotulo] += decimal_zero(item["total"])

    for item in querysets["custos_fixos"].values("categoria").annotate(total=Sum("valor_previsto")):
        rotulo = labels_custos_fixos.get(item["categoria"], item["categoria"])
        grupos[f"Custo fixo: {rotulo}"] += decimal_zero(item["total"])

    investimentos_saida = querysets["investimentos"].filter(tipo_fluxo="saida")
    for item in investimentos_saida.values("categoria").annotate(total=Sum("valor_previsto")):
        rotulo = labels_investimentos.get(item["categoria"], item["categoria"])
        grupos[f"Investimento: {rotulo}"] += decimal_zero(item["total"])

    if totais_financeiros["total_previsto_saida_fcf"] > Decimal("0.00"):
        grupos["Financiamentos"] += totais_financeiros["total_previsto_saida_fcf"]

    total = sum(grupos.values(), Decimal("0.00"))
    if total <= Decimal("0.00"):
        return []

    return [
        {
            "name": nome,
            "categoryName": nome,
            "value": decimal_para_numero(valor),
            "expenseAmount": decimal_para_numero(valor),
            "percentage": percentual(valor, total),
            "color": CORES_CATEGORIAS[indice % len(CORES_CATEGORIAS)],
        }
        for indice, (nome, valor) in enumerate(
            sorted(grupos.items(), key=lambda item: item[1], reverse=True)
        )
    ]


def montar_resumo_receitas_servico(
    totais_basicos,
    querysets,
    receitas_servico_anterior=None,
):
    receitas_servico_anterior = receitas_servico_anterior or {}
    custos_servico = list(querysets["custos_evento"])
    servicos_por_evento = defaultdict(set)
    receita_por_servico = defaultdict(lambda: Decimal("0.00"))
    eventos_por_servico = defaultdict(set)
    receitas_por_evento = totais_basicos["receitas_por_evento"]

    for custo in custos_servico:
        servicos_por_evento[custo.evento_id].add(custo.servico.nome)

    for custo in custos_servico:
        receita_evento = receitas_por_evento.get(custo.evento_id, Decimal("0.00"))
        quantidade_servicos = len(servicos_por_evento[custo.evento_id]) or 1
        receita_por_servico[custo.servico.nome] += quantizar_moeda(
            receita_evento / Decimal(quantidade_servicos)
        )
        eventos_por_servico[custo.servico.nome].add(custo.evento_id)

    if not receita_por_servico and totais_basicos["receita_prevista"] > Decimal("0.00"):
        receita_por_servico["Serviços operacionais"] = totais_basicos["receita_prevista"]

    total = sum(receita_por_servico.values(), Decimal("0.00"))
    receitas_servico = [
        {
            "service": nome,
            "serviceName": nome,
            "revenue": decimal_para_numero(valor),
            "revenueAmount": decimal_para_numero(valor),
            "percentage": percentual(valor, total),
            "variation": calcular_variacao_percentual_numero(
                valor,
                receitas_servico_anterior.get(nome),
            ),
        }
        for nome, valor in sorted(
            receita_por_servico.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    contratos = [
        {
            "service": nome,
            "serviceName": nome,
            "operationalEventsCount": len(eventos_por_servico[nome]) or 1,
            "contracts": len(eventos_por_servico[nome]) or 1,
            "contractCount": len(eventos_por_servico[nome]) or 1,
            "value": decimal_para_numero(valor),
            "revenueAmount": decimal_para_numero(valor),
        }
        for nome, valor in sorted(
            receita_por_servico.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return {
        "receitas_servico": receitas_servico,
        "contratos": contratos,
        "total": total,
    }


def montar_contas_a_pagar_dashboard(movimentacoes):
    hoje = timezone.localdate()
    contas = [
        movimentacao
        for movimentacao in movimentacoes
        if decimal_zero(movimentacao.get("saida")) > Decimal("0.00")
        and decimal_zero(movimentacao.get("aberto")) > Decimal("0.00")
    ]
    contas.sort(key=lambda item: (item["data"] or date.max, item["descricao"]))

    return {
        "quantidade": len(contas),
        "itens": [
            {
                "description": conta["descricao"],
                "obligationDescription": conta["descricao"],
                "payableDescription": conta["descricao"],
                "contractCode": conta.get("contractCode", ""),
                "contractName": conta.get("contractName", ""),
                "contractLabel": conta.get("contractLabel", ""),
                "eventId": conta.get("eventId"),
                "eventName": conta.get("eventName", ""),
                "eventNumber": conta.get("eventNumber", ""),
                "eventLabel": conta.get("eventLabel", ""),
                "clientId": conta.get("clientId"),
                "clientName": conta.get("clientName", ""),
                "dueDate": formatar_data_br(conta["data"]),
                "value": decimal_para_numero(conta["aberto"]),
                "pendingValue": decimal_para_numero(conta["contas_pendentes"]),
                "plannedAmount": decimal_para_numero(conta["saida"]),
                "paidAmount": decimal_para_numero(conta.get("pago")),
                "pendingAmount": decimal_para_numero(conta["contas_pendentes"]),
                "pendingPaymentAmount": decimal_para_numero(
                    conta["contas_pendentes"]
                ),
                "status": prioridade_conta(conta["data"], hoje),
            }
            for conta in contas
        ],
    }


def montar_contas_a_receber_dashboard(receitas, filtros_dashboard=None):
    hoje = timezone.localdate()
    mostrar_recebidas = (filtros_dashboard or {}).get("status") == "recebido"
    if mostrar_recebidas:
        contas = [
            receita
            for receita in receitas
            if receita.valor_recebido > Decimal("0.00")
        ]
    else:
        contas = [
            receita
            for receita in receitas
            if receita.saldo_a_receber > Decimal("0.00")
        ]
    contas.sort(key=lambda receita: (receita.data_vencimento or date.max, receita.id))

    return {
        "quantidade": len(contas),
        "itens": [
            serializar_conta_a_receber_dashboard(receita, mostrar_recebidas, hoje)
            for receita in contas
        ],
    }


def serializar_conta_a_receber_dashboard(receita, mostrar_recebidas, hoje):
    dimensao = serializar_dimensao_operacional_financeira(receita)
    valor_pendente = (
        Decimal("0.00") if mostrar_recebidas else receita.valor_pendente_recebimento
    )

    return {
        "description": receita.descricao,
        "receivableDescription": receita.descricao,
        "client": dimensao["clientName"],
        "clientName": dimensao["clientName"],
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "contractLabel": dimensao["contractLabel"],
        "eventId": dimensao["eventId"],
        "eventName": dimensao["eventName"],
        "eventNumber": dimensao["eventNumber"],
        "eventLabel": dimensao["eventLabel"],
        "dueDate": formatar_data_br(receita.data_vencimento),
        "value": decimal_para_numero(
            receita.valor_recebido if mostrar_recebidas else receita.saldo_a_receber
        ),
        "pendingValue": decimal_para_numero(valor_pendente),
        "plannedAmount": decimal_para_numero(receita.valor_previsto),
        "receivedAmount": decimal_para_numero(receita.valor_recebido),
        "pendingAmount": decimal_para_numero(valor_pendente),
        "pendingReceivableAmount": decimal_para_numero(valor_pendente),
        "status": (
            "recebido"
            if mostrar_recebidas
            else "atrasado" if receita.data_vencimento < hoje else "pendente"
        ),
    }


def montar_indicadores_financeiros(
    totais_basicos,
    totais_financeiros,
    totais_movimentacoes,
    disponibilidade_caixa=None,
):
    receita_prevista = totais_basicos["receita_prevista"]
    receita_recebida = totais_basicos["receita_recebida"]
    total_saida = totais_movimentacoes["total_saida_movimentacoes_prevista"]
    total_pago = totais_movimentacoes["total_pago_movimentacoes"]
    resultado_liquido = receita_prevista - total_saida
    margem = percentual(resultado_liquido, receita_prevista)
    margem_contribuicao_percentual = float(
        totais_financeiros["margem_contribuicao_percentual"]
    )
    disponibilidade_caixa = disponibilidade_caixa or {}
    caixa_disponivel_periodo = disponibilidade_caixa.get(
        "finalCashAmount",
        disponibilidade_caixa.get(
            "availableCashAmount",
            totais_movimentacoes["caixa_final_mes"],
        ),
    )
    obrigacoes_pendentes_periodo = totais_movimentacoes[
        "total_contas_pendentes_movimentacoes"
    ]
    liquidez = ratio_decimal(
        caixa_disponivel_periodo,
        obrigacoes_pendentes_periodo,
    )

    return [
        {
            "title": "Recebimento",
            "indicatorName": "Recebimento",
            "value": formatar_percentual(percentual(receita_recebida, receita_prevista)),
            "indicatorValue": formatar_percentual(percentual(receita_recebida, receita_prevista)),
            "label": "Recebido no período",
            "indicatorDetail": "Recebido no período",
            "status": status_percentual(percentual(receita_recebida, receita_prevista)),
        },
        {
            "title": "Pagamento",
            "indicatorName": "Pagamento",
            "value": formatar_percentual(percentual(total_pago, total_saida)),
            "indicatorValue": formatar_percentual(percentual(total_pago, total_saida)),
            "label": "Pago no período",
            "indicatorDetail": "Pago no período",
            "status": status_percentual(percentual(total_pago, total_saida)),
        },
        {
            "title": "Margem",
            "indicatorName": "Margem",
            "value": formatar_percentual(margem),
            "indicatorValue": formatar_percentual(margem),
            "label": "Resultado financeiro",
            "indicatorDetail": "Resultado financeiro",
            "status": "good" if margem >= 20 else "warning" if margem >= 10 else "neutral",
        },
        {
            "title": "Margem de Contribuição",
            "indicatorName": "Margem de Contribuição",
            "value": formatar_percentual(margem_contribuicao_percentual),
            "indicatorValue": formatar_percentual(margem_contribuicao_percentual),
            "label": "Receita - custo variável",
            "indicatorDetail": "Receita - custo variável",
            "status": (
                "good"
                if margem_contribuicao_percentual >= 20
                else "warning" if margem_contribuicao_percentual >= 10 else "neutral"
            ),
        },
        {
            "title": "Lucro Operacional / EBIT",
            "indicatorName": "Lucro Operacional / EBIT",
            "value": formatar_moeda_br(totais_financeiros["lucro_operacional_ebit"]),
            "indicatorValue": formatar_moeda_br(
                totais_financeiros["lucro_operacional_ebit"]
            ),
            "label": "Margem - custo fixo",
            "indicatorDetail": "Margem - custo fixo",
            "status": (
                "good"
                if totais_financeiros["lucro_operacional_ebit"] >= Decimal("0.00")
                else "warning"
            ),
        },
        {
            "title": "Liquidez do Período",
            "indicatorName": "Liquidez do Período",
            "value": formatar_decimal_br(liquidez),
            "indicatorValue": formatar_decimal_br(liquidez),
            "label": "Caixa do período / obrigações pendentes",
            "indicatorDetail": "Caixa do período / obrigações pendentes",
            "status": "good" if liquidez >= Decimal("1.00") else "warning",
        },
    ]


def montar_metas_financeiras(totais_basicos, totais_movimentacoes):
    receita_prevista = totais_basicos["receita_prevista"]
    receita_recebida = totais_basicos["receita_recebida"]
    resultado_liquido = receita_prevista - totais_movimentacoes["total_saida_movimentacoes_prevista"]
    margem = Decimal(str(percentual(resultado_liquido, receita_prevista)))
    meta_margem = Decimal("25.0")

    return [
        {
            "title": "Receita recebida",
            "goalName": "Receita recebida",
            "current": decimal_para_numero(receita_recebida),
            "currentValue": decimal_para_numero(receita_recebida),
            "target": decimal_para_numero(receita_prevista),
            "targetValue": decimal_para_numero(receita_prevista),
            "percentage": percentual(receita_recebida, receita_prevista),
            "status": status_meta(percentual(receita_recebida, receita_prevista)),
        },
        {
            "title": "Margem liquida",
            "goalName": "Margem liquida",
            "current": float(margem),
            "currentValue": float(margem),
            "target": float(meta_margem),
            "targetValue": float(meta_margem),
            "percentage": percentual(margem, meta_margem),
            "status": status_meta(percentual(margem, meta_margem)),
        },
    ]


def montar_fluxo_caixa(totais_movimentacoes, disponibilidade_caixa=None):
    disponibilidade_caixa = disponibilidade_caixa or {}
    entradas = totais_movimentacoes["total_entrada_movimentacoes_prevista"]
    saidas = totais_movimentacoes["total_saida_movimentacoes_prevista"]
    resultado_financeiro = entradas - saidas
    caixa_final_realizado = disponibilidade_caixa.get(
        "finalCashAmount",
        totais_movimentacoes["caixa_final_mes"],
    )
    saldo_inicial = disponibilidade_caixa.get(
        "initialCashAmount",
        totais_movimentacoes["saldo_inicial"],
    )
    entradas_efetivas = disponibilidade_caixa.get(
        "realizedInflowAmount",
        totais_movimentacoes["total_recebido_movimentacoes"],
    )
    saidas_efetivas = disponibilidade_caixa.get(
        "realizedOutflowAmount",
        totais_movimentacoes["total_pago_movimentacoes"],
    )
    resultado_efetivo_periodo = disponibilidade_caixa.get(
        "periodRealizedAmount",
        totais_movimentacoes["resultado_realizado_periodo"],
    )
    caixa_disponivel_acumulado = disponibilidade_caixa.get(
        "accumulatedCashUntilDate"
    )

    return {
        "saldoInicial": decimal_para_numero(saldo_inicial),
        "initialCashAmount": decimal_para_numero(saldo_inicial),
        "entradas": decimal_para_numero(entradas),
        "inflowAmount": decimal_para_numero(entradas),
        "realizedInflowAmount": decimal_para_numero(entradas_efetivas),
        "saidas": decimal_para_numero(saidas),
        "outflowAmount": decimal_para_numero(saidas),
        "realizedOutflowAmount": decimal_para_numero(saidas_efetivas),
        "contasPendentes": decimal_para_numero(
            totais_movimentacoes["total_contas_pendentes_movimentacoes"]
        ),
        "pendingAccountsAmount": decimal_para_numero(
            totais_movimentacoes["total_contas_pendentes_movimentacoes"]
        ),
        "saldoFinal": decimal_para_numero(resultado_financeiro),
        "resultadoFinanceiro": decimal_para_numero(resultado_financeiro),
        "financialResultAmount": decimal_para_numero(resultado_financeiro),
        "deficitCaixa": decimal_para_numero(totais_movimentacoes["deficit_caixa_movimentacoes"]),
        "cashDeficitAmount": decimal_para_numero(totais_movimentacoes["deficit_caixa_movimentacoes"]),
        "availableCashAmount": decimal_para_numero(caixa_final_realizado),
        "cashAvailableAmount": decimal_para_numero(caixa_final_realizado),
        "caixaDisponivel": decimal_para_numero(caixa_final_realizado),
        "saldoCaixaDisponivel": decimal_para_numero(caixa_final_realizado),
        "finalCashAmount": decimal_para_numero(caixa_final_realizado),
        "realizedFinalCashAmount": decimal_para_numero(caixa_final_realizado),
        "currentAvailableCashAmount": decimal_para_numero(
            disponibilidade_caixa.get("currentAvailableCashAmount")
        ),
        "currentCashAvailableUntilDate": disponibilidade_caixa.get(
            "currentCashAvailableUntilDate"
        ),
        "projectedFinalCashAmount": decimal_para_numero(
            totais_movimentacoes["caixa_final_previsto"]
        ),
        "periodRealizedAmount": decimal_para_numero(
            resultado_efetivo_periodo
        ),
        "periodProjectedAmount": decimal_para_numero(
            totais_movimentacoes["resultado_previsto_periodo"]
        ),
        "accumulatedCashUntilDate": decimal_para_numero(
            caixa_disponivel_acumulado
        ),
        "accumulatedAvailableCashAmount": decimal_para_numero(
            caixa_disponivel_acumulado
        ),
        "cashAvailableUntilDate": disponibilidade_caixa.get("cashAvailableUntilDate"),
        "cashFlows": serializar_fluxos_caixa_dashboard(totais_movimentacoes),
        "fluxosCaixa": serializar_fluxos_caixa_dashboard(totais_movimentacoes),
    }


def serializar_fluxos_caixa_dashboard(totais_movimentacoes):
    return {
        chave: serializar_fluxo_caixa_dashboard(fluxo)
        for chave, fluxo in totais_movimentacoes["fluxos_caixa"].items()
    }


def serializar_fluxo_caixa_dashboard(fluxo):
    return {
        "code": fluxo["codigo"],
        "codigo": fluxo["codigo"],
        "inflowAmount": decimal_para_numero(fluxo["entrada_prevista"]),
        "outflowAmount": decimal_para_numero(fluxo["saida_prevista"]),
        "financialResultAmount": decimal_para_numero(fluxo["resultado_previsto"]),
        "realizedInflowAmount": decimal_para_numero(fluxo["entrada_realizada"]),
        "realizedOutflowAmount": decimal_para_numero(fluxo["saida_realizada"]),
        "realizedFinancialResultAmount": decimal_para_numero(
            fluxo["resultado_realizado"]
        ),
        "entradas": decimal_para_numero(fluxo["entrada_prevista"]),
        "saidas": decimal_para_numero(fluxo["saida_prevista"]),
        "resultadoFinanceiro": decimal_para_numero(fluxo["resultado_previsto"]),
    }


def montar_opcoes_filtros_dashboard_api():
    opcoes = montar_opcoes_eventos_clientes_filtro()
    opcoes_dimensoes = serializar_opcoes_entidades_operacionais(
        opcoes,
        incluir_clientes=True,
        limite_contratos=80,
        limite_eventos=80,
        limite_clientes=120,
    )

    return {
        **opcoes_dimensoes,
        "statuses": [
            {
                "value": valor,
                "label": rotulo,
            }
            for valor, rotulo in STATUS_DASHBOARD_FILTRO
        ],
    }


def metrica_numero(valor, casas=2, variacao=None, rotulo_variacao="sem comparação"):
    metric_value = numero_decimal(valor, casas=casas)
    change_value = numero_variacao(variacao)
    change_label = rotulo_variacao if change_value is not None else "sem comparação"
    return {
        "value": metric_value,
        "metricValue": metric_value,
        "change": change_value,
        "changePercent": change_value,
        "changeLabel": change_label,
        "changeDescription": change_label,
    }


def numero_variacao(valor):
    if valor is None:
        return None
    return float(como_decimal(valor).quantize(Decimal("0.1")))


def numero_decimal(valor, casas=2):
    decimal = como_decimal(valor)
    if casas == 1:
        return float(decimal.quantize(Decimal("0.1")))
    return decimal_para_numero(decimal)


def decimal_para_numero(valor):
    return float(quantizar_moeda(como_decimal(valor)))


def percentual(parte, total):
    parte = como_decimal(parte)
    total = como_decimal(total)
    if total <= Decimal("0.00"):
        return 0.0
    return float(((parte / total) * Decimal("100")).quantize(Decimal("0.1")))


def calcular_variacao_percentual(atual, anterior):
    if anterior is None:
        return None
    atual = como_decimal(atual)
    anterior = como_decimal(anterior)
    if anterior == Decimal("0.00"):
        return None
    return ((atual - anterior) / abs(anterior) * Decimal("100")).quantize(
        Decimal("0.1")
    )


def calcular_variacao_percentual_numero(atual, anterior):
    variacao = calcular_variacao_percentual(atual, anterior)
    return numero_variacao(variacao)


def calcular_variacao_pontos_percentuais(atual, anterior):
    if atual is None or anterior is None:
        return None
    return (como_decimal(atual) - como_decimal(anterior)).quantize(Decimal("0.1"))


def ratio_decimal(parte, total):
    parte = como_decimal(parte)
    total = como_decimal(total)
    if total <= Decimal("0.00"):
        return Decimal("0.00")
    return (parte / total).quantize(Decimal("0.01"))


def como_decimal(valor):
    if isinstance(valor, Decimal):
        return valor
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def status_percentual(valor):
    if valor >= 80:
        return "good"
    if valor >= 50:
        return "warning"
    return "neutral"


def status_meta(valor):
    if valor >= 90:
        return "on-track"
    if valor >= 60:
        return "attention"
    return "behind"


def prioridade_conta(data_vencimento, hoje):
    if not data_vencimento or data_vencimento < hoje:
        return "alta"
    if (data_vencimento - hoje).days <= 7:
        return "media"
    return "baixa"


def montar_rotulo_periodo(filtros_dashboard):
    data_inicial = parse_date(filtros_dashboard.get("data_inicial"))
    data_final = parse_date(filtros_dashboard.get("data_final"))

    if data_inicial and data_final and data_inicial.month == data_final.month and data_inicial.year == data_final.year:
        return f"{MESES_COMPLETOS[data_inicial.month - 1]} de {data_inicial.year}"

    if data_inicial and data_final:
        return f"{formatar_data_br(data_inicial)} a {formatar_data_br(data_final)}"

    return "Período completo"


def montar_rotulo_comparacao_anterior(filtros_dashboard):
    data_inicial = parse_date(filtros_dashboard.get("data_inicial"))
    data_final = parse_date(filtros_dashboard.get("data_final"))

    if data_inicial and data_final and data_inicial.month == data_final.month and data_inicial.year == data_final.year:
        return f"vs {formatar_mes_curto(data_inicial.year, data_inicial.month)}"

    if data_inicial and data_final:
        return f"vs {formatar_data_br(data_inicial)} a {formatar_data_br(data_final)}"

    return "sem comparação"


def formatar_mes_curto(ano, mes):
    return f"{MESES_CURTOS[mes - 1]}/{str(ano)[-2:]}"


def formatar_data_br(valor):
    if not valor:
        return ""
    return valor.strftime("%d/%m/%Y")


def formatar_percentual(valor):
    return f"{valor:.1f}%".replace(".", ",")


def formatar_decimal_br(valor):
    return str(valor).replace(".", ",")


def parse_date(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None
