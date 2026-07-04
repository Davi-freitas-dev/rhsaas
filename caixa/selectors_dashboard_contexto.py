from decimal import Decimal

from .selectors_lancamentos import calcular_totais_lancamentos_financeiros
from .selectors_opcoes_filtros import montar_opcoes_eventos_clientes_filtro
from .selectors_dashboard_urls import (
    montar_url_com_params,
    params_despesas_pessoal_dashboard,
    params_mes_financeiro_dashboard,
    params_receitas_dashboard,
)


ZERO = Decimal("0.00")
FONTE_REALIZADO_LEDGER = "ledger"
FONTE_REALIZADO_LEGADO = "legacy"

CAMPOS_TOTAIS_BASICOS_CONTEXT = (
    "receita_prevista",
    "receita_recebida",
    "despesa_prevista",
    "despesa_paga",
    "despesas_pessoal_previstas",
    "total_custo_fixo_previsto",
    "total_custo_fixo_pago",
    "total_diarias",
    "total_alimentacao",
    "total_transporte",
    "total_custos_extras",
)
CAMPOS_TOTAIS_FINANCEIROS_CONTEXT = (
    "total_eventos",
    "eventos_operacionais_ativos",
    "eventos_abertos",
    "contratos_ativos",
    "contas_a_receber",
    "contas_a_pagar",
    "contas_pendentes",
    "despesas_a_pagar",
    "custos_fixos_a_pagar",
    "contas_a_pagar_periodo",
    "contas_pendentes_periodo",
    "total_entrada_fco_prevista",
    "total_saida_fco_prevista",
    "total_entrada_fco_realizada",
    "total_saida_fco_realizada",
    "total_custos_operacionais",
    "total_imposto_previsto",
    "total_imposto_pago",
    "total_pagar_operacional",
    "total_pago_operacional",
    "custo_variavel",
    "margem_contribuicao",
    "margem_contribuicao_percentual",
    "lucro_operacional_ebit",
    "resultado_operacional_previsto",
    "resultado_operacional_realizado",
    "resultado_financeiro_operacional_projetado",
    "resultado_financeiro_operacional_realizado",
    "total_previsto_entrada_fci",
    "total_previsto_saida_fci",
    "total_realizado_entrada_fci",
    "total_realizado_saida_fci",
    "resultado_investimentos_previsto",
    "resultado_investimentos_realizado",
    "resultado_financeiro_fci_projetado",
    "resultado_financeiro_fci_realizado",
    "total_previsto_entrada_fcf",
    "total_previsto_saida_fcf",
    "total_realizado_entrada_fcf",
    "total_realizado_saida_fcf",
    "resultado_financiamentos_previsto",
    "resultado_financiamentos_realizado",
    "resultado_financeiro_fcf_projetado",
    "resultado_financeiro_fcf_realizado",
    "total_contas_pendentes_fcf",
    "total_em_aberto_fcf",
    "contas_pendentes_fcf",
    "total_contas_vencidas_fcf",
    "total_vencido_fcf",
    "contas_vencidas_fcf",
    "resultado_consolidado_previsto",
    "resultado_consolidado_realizado",
    "resultado_financeiro_consolidado_projetado",
    "resultado_financeiro_consolidado_realizado",
)

STATUS_DASHBOARD_FILTRO = (
    ("pendente", "Pendente"),
    ("parcial", "Parcial"),
    ("recebido", "Recebido"),
    ("pago", "Pago"),
    ("vencido", "Vencido"),
    ("cancelado", "Cancelado"),
    ("planejado", "Planejado"),
    ("realizado", "Realizado"),
)


def selecionar_campos_contexto(dados, campos):
    return {
        chave: dados[chave]
        for chave in campos
    }


def montar_filtros_visiveis_dashboard(filtros_dashboard):
    filtros = {
        "data_inicial": filtros_dashboard["data_inicial"],
        "data_final": filtros_dashboard["data_final"],
        "evento": filtros_dashboard["evento_id"],
        "cliente": filtros_dashboard["cliente_id"],
        "status": filtros_dashboard["status"],
    }
    if filtros_dashboard.get("contrato_codigo"):
        filtros["contractCode"] = filtros_dashboard["contrato_codigo"]
        filtros["contrato_codigo"] = filtros_dashboard["contrato_codigo"]
    return filtros


def montar_opcoes_filtros_dashboard():
    return {
        **montar_opcoes_eventos_clientes_filtro(),
        "status_dashboard": STATUS_DASHBOARD_FILTRO,
    }


def montar_contexto_base_dashboard(filtros_dashboard):
    return {
        **montar_opcoes_filtros_dashboard(),
        "periodo_rapido": filtros_dashboard["periodo_rapido"],
        "filtros": montar_filtros_visiveis_dashboard(filtros_dashboard),
    }


def deve_usar_lancamentos_realizados_dashboard(filtros_dashboard):
    return bool(filtros_dashboard) and not filtros_dashboard.get("status")


def montar_totais_realizados_legacy_dashboard(totais_financeiros):
    resultado_operacional = totais_financeiros["resultado_operacional_realizado"]
    resultado_fci = totais_financeiros.get("resultado_financeiro_fci_realizado", ZERO)
    resultado_fcf = totais_financeiros.get("resultado_financeiro_fcf_realizado", ZERO)
    resultado_consolidado = totais_financeiros.get(
        "resultado_financeiro_consolidado_realizado",
        resultado_operacional,
    )

    return {
        "fonte": FONTE_REALIZADO_LEGADO,
        "entradas": totais_financeiros.get("total_entrada_fco_realizada", ZERO),
        "saidas": totais_financeiros.get("total_saida_fco_realizada", ZERO),
        "resultado": resultado_consolidado,
        "fco": {
            "entradas": totais_financeiros.get("total_entrada_fco_realizada", ZERO),
            "saidas": totais_financeiros.get("total_saida_fco_realizada", ZERO),
            "resultado_financeiro": totais_financeiros.get(
                "resultado_financeiro_operacional_realizado",
                resultado_operacional,
            ),
        },
        "fci": {
            "entradas": totais_financeiros.get("total_realizado_entrada_fci", ZERO),
            "saidas": totais_financeiros.get("total_realizado_saida_fci", ZERO),
            "resultado_financeiro": resultado_fci,
        },
        "fcf": {
            "entradas": totais_financeiros.get("total_realizado_entrada_fcf", ZERO),
            "saidas": totais_financeiros.get("total_realizado_saida_fcf", ZERO),
            "resultado_financeiro": resultado_fcf,
        },
    }


def montar_totais_realizados_dashboard(totais_financeiros, filtros_dashboard=None):
    if deve_usar_lancamentos_realizados_dashboard(filtros_dashboard):
        totais_lancamentos = calcular_totais_lancamentos_financeiros(filtros_dashboard)
        return {
            "fonte": FONTE_REALIZADO_LEDGER,
            "entradas": totais_lancamentos["entradas"],
            "saidas": totais_lancamentos["saidas"],
            "resultado": totais_lancamentos["resultado_financeiro"],
            "fco": totais_lancamentos["fco"],
            "fci": totais_lancamentos["fci"],
            "fcf": totais_lancamentos["fcf"],
        }

    return montar_totais_realizados_legacy_dashboard(totais_financeiros)


def montar_aliases_realizados_dashboard(totais_realizados):
    return {
        "resultado_realizado": totais_realizados["resultado"],
        "resultado_financeiro_realizado": totais_realizados["resultado"],
        "realizedFinancialResultAmount": totais_realizados["resultado"],
        "resultado_financeiro_consolidado_realizado": totais_realizados["resultado"],
        "resultado_financeiro_operacional_realizado": totais_realizados["fco"][
            "resultado_financeiro"
        ],
        "resultado_financeiro_fci_realizado": totais_realizados["fci"][
            "resultado_financeiro"
        ],
        "resultado_financeiro_fcf_realizado": totais_realizados["fcf"][
            "resultado_financeiro"
        ],
        "resultado_investimentos_realizado": totais_realizados["fci"][
            "resultado_financeiro"
        ],
        "resultado_financiamentos_realizado": totais_realizados["fcf"][
            "resultado_financeiro"
        ],
        "total_entrada_realizada": totais_realizados["entradas"],
        "total_saida_realizada": totais_realizados["saidas"],
        "realizedInflowAmount": totais_realizados["entradas"],
        "realizedOutflowAmount": totais_realizados["saidas"],
        "total_entrada_fco_realizada": totais_realizados["fco"]["entradas"],
        "total_saida_fco_realizada": totais_realizados["fco"]["saidas"],
        "total_realizado_entrada_fci": totais_realizados["fci"]["entradas"],
        "total_realizado_saida_fci": totais_realizados["fci"]["saidas"],
        "total_realizado_entrada_fcf": totais_realizados["fcf"]["entradas"],
        "total_realizado_saida_fcf": totais_realizados["fcf"]["saidas"],
        "resultado_financeiro_realizado_source": totais_realizados["fonte"],
        "resultado_financeiro_realizado_fonte": totais_realizados["fonte"],
        "totais_realizados_dashboard": totais_realizados,
    }


def montar_resultado_resumo_dashboard(
    totais_financeiros,
    totais_movimentacoes,
    filtros_dashboard=None,
):
    total_despesa_prevista = totais_movimentacoes["total_saida_movimentacoes_prevista"]
    resultado_financeiro_projetado = totais_financeiros.get(
        "resultado_financeiro_consolidado_projetado",
        totais_financeiros["resultado_operacional_previsto"],
    )
    totais_realizados = montar_totais_realizados_dashboard(
        totais_financeiros,
        filtros_dashboard,
    )

    return {
        "resultado_previsto": resultado_financeiro_projetado,
        "resultado_total": resultado_financeiro_projetado,
        "resultado_financeiro": resultado_financeiro_projetado,
        "resultado_financeiro_projetado": resultado_financeiro_projetado,
        "financialResultAmount": resultado_financeiro_projetado,
        "plannedFinancialResultAmount": resultado_financeiro_projetado,
        "projectedFinancialResultAmount": resultado_financeiro_projetado,
        "total_despesa_prevista": total_despesa_prevista,
        "custo_total_previsto": total_despesa_prevista,
        **montar_aliases_realizados_dashboard(totais_realizados),
    }


def montar_urls_resumo_dashboard(filtros_dashboard):
    return {
        "url_mes_financeiro_custo_mensal": montar_url_com_params(
            "caixa:mes_financeiro",
            params_mes_financeiro_dashboard(filtros_dashboard),
        ),
        "url_receitas_resumo": montar_url_com_params(
            "caixa:receitas_lista",
            params_receitas_dashboard(filtros_dashboard),
        ),
        "url_despesas_pessoal_resumo": montar_url_com_params(
            "caixa:despesas_lista",
            params_despesas_pessoal_dashboard(filtros_dashboard),
        ),
    }


def montar_resumo_dashboard(totais_financeiros, totais_movimentacoes, filtros_dashboard):
    return {
        **montar_resultado_resumo_dashboard(
            totais_financeiros,
            totais_movimentacoes,
            filtros_dashboard,
        ),
        **montar_urls_resumo_dashboard(filtros_dashboard),
    }
