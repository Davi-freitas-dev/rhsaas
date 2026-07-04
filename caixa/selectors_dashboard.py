from .selectors_dashboard_alertas import montar_alertas_dashboard
from .selectors_dashboard_contexto import (
    CAMPOS_TOTAIS_BASICOS_CONTEXT,
    CAMPOS_TOTAIS_FINANCEIROS_CONTEXT,
    montar_contexto_base_dashboard,
    montar_resumo_dashboard,
    selecionar_campos_contexto,
)
from .selectors_dashboard_custos_evento import (
    montar_custos_por_evento_dashboard,
    resumir_pagamentos_custos_extras_por_evento,
    resumir_pagamentos_custos_servico_por_item,
)
from .selectors_dashboard_filtros import (
    querysets_dashboard_filtrados,
    resolver_filtros_dashboard,
)
from .selectors_dashboard_movimentacoes import montar_movimentacoes_dashboard
from .selectors_dashboard_totais import (
    calcular_totais_basicos_dashboard,
    calcular_totais_financeiros_dashboard,
)
from .utils_fluxos_caixa import calcular_saldo_inicial_fluxo_caixa


def montar_dados_dashboard(params, session):
    filtros_dashboard = resolver_filtros_dashboard(params, session)
    querysets = querysets_dashboard_filtrados(filtros_dashboard)

    totais_basicos = calcular_totais_basicos_dashboard(
        querysets["receitas"],
        querysets["despesas"],
        querysets["custos_fixos"],
        querysets["custos_evento"],
        querysets["custos_extras"],
    )
    totais_financeiros = calcular_totais_financeiros_dashboard(
        filtros_dashboard,
        querysets["receitas"],
        querysets["despesas"],
        querysets["custos_fixos"],
        querysets["investimentos"],
        querysets["parcelas_divida"],
        totais_basicos,
        financiamentos=querysets["financiamentos"],
    )

    alertas_dashboard = montar_alertas_dashboard(
        totais_financeiros["total_vencido_fcf"],
        totais_financeiros["contas_a_receber"],
        totais_financeiros["despesas_a_pagar"],
        totais_financeiros["custos_fixos_a_pagar"],
        querysets["custos_fixos"],
        filtros_dashboard,
        totais_financeiros["hoje"],
    )
    saldo_inicial = calcular_saldo_inicial_fluxo_caixa(
        filtros_dashboard.get("data_inicial")
    )
    totais_movimentacoes = montar_movimentacoes_dashboard(
        querysets["receitas"],
        querysets["despesas"],
        querysets["custos_fixos"],
        querysets["investimentos"],
        totais_financeiros["lista_parcelas_divida"],
        totais_financeiros["lista_financiamentos"],
        saldo_inicial=saldo_inicial,
    )

    return {
        "filtros_dashboard": filtros_dashboard,
        "querysets": querysets,
        "totais_basicos": totais_basicos,
        "totais_financeiros": totais_financeiros,
        "totais_movimentacoes": totais_movimentacoes,
        "alertas_dashboard": alertas_dashboard,
    }


def montar_contexto_dashboard(params, session):
    dados_dashboard = montar_dados_dashboard(params, session)
    filtros_dashboard = dados_dashboard["filtros_dashboard"]
    totais_basicos = dados_dashboard["totais_basicos"]
    totais_financeiros = dados_dashboard["totais_financeiros"]
    totais_movimentacoes = dados_dashboard["totais_movimentacoes"]

    return {
        **selecionar_campos_contexto(totais_basicos, CAMPOS_TOTAIS_BASICOS_CONTEXT),
        **selecionar_campos_contexto(totais_financeiros, CAMPOS_TOTAIS_FINANCEIROS_CONTEXT),
        **totais_movimentacoes,
        **montar_resumo_dashboard(totais_financeiros, totais_movimentacoes, filtros_dashboard),
        **montar_contexto_base_dashboard(filtros_dashboard),
        "alertas_dashboard": dados_dashboard["alertas_dashboard"],
    }


def montar_contexto_custos_por_evento(params, session):
    filtros_dashboard = resolver_filtros_dashboard(params, session)
    querysets = querysets_dashboard_filtrados(filtros_dashboard)

    totais_basicos = calcular_totais_basicos_dashboard(
        querysets["receitas"],
        querysets["despesas"],
        querysets["custos_fixos"],
        querysets["custos_evento"],
        querysets["custos_extras"],
    )

    custos_eventos_contexto = montar_custos_por_evento_dashboard(
        querysets["custos_evento"],
        querysets["custos_extras"],
        querysets["despesas"],
        totais_basicos["receitas_por_evento"],
        totais_basicos["receitas_recebidas_por_evento"],
        totais_basicos["despesas_pagas_por_evento"],
    )

    return {
        **custos_eventos_contexto,
        **montar_contexto_base_dashboard(filtros_dashboard),
    }
