from decimal import Decimal

from .constants_financeiros import STATUS_CANCELADO, STATUS_PAGO
from .selectors_dashboard_urls import (
    montar_url_com_params,
    params_periodo_com_sessao,
    params_periodo_dashboard,
    params_vencidos_dashboard,
)
from .utils_moeda import formatar_moeda_br


def montar_alertas_dashboard(
    total_vencido_fcf,
    contas_a_receber,
    despesas_a_pagar,
    custos_fixos_a_pagar,
    custos_fixos,
    filtros_dashboard,
    hoje,
):
    alertas = []
    params_periodo = params_periodo_dashboard(filtros_dashboard)
    params_periodo_sessao = params_periodo_com_sessao(filtros_dashboard)
    params_vencidos = params_vencidos_dashboard(filtros_dashboard)

    if total_vencido_fcf > Decimal("0.00"):
        alertas.append({
            "texto": f"Ha parcelas financeiras vencidas no total de {formatar_moeda_br(total_vencido_fcf)}.",
            "url": montar_url_com_params("caixa:lista_financiamentos", params_vencidos),
            "acao": "Ver FCF",
        })

    if contas_a_receber > Decimal("0.00"):
        alertas.append({
            "texto": f"Ha contas a receber pendentes no total de {formatar_moeda_br(contas_a_receber)}.",
            "url": montar_url_com_params("caixa:receitas_lista", params_periodo),
            "acao": "Ver receitas",
        })

    if despesas_a_pagar > Decimal("0.00"):
        alertas.append({
            "texto": f"Ha despesas operacionais pendentes no total de {formatar_moeda_br(despesas_a_pagar)}.",
            "url": montar_url_com_params("caixa:despesas_lista", params_periodo),
            "acao": "Ver despesas",
        })

    if custos_fixos_a_pagar > Decimal("0.00"):
        alertas.append({
            "texto": f"Ha custos fixos pendentes no total de {formatar_moeda_br(custos_fixos_a_pagar)}.",
            "url": montar_url_com_params("caixa:custos_fixos_lista", params_periodo_sessao),
            "acao": "Ver custos fixos",
        })

    custos_fixos_vencidos = custos_fixos.filter(
        data_vencimento__lt=hoje
    ).exclude(status__in=[STATUS_PAGO, STATUS_CANCELADO]).count()

    if custos_fixos_vencidos > 0:
        alertas.append({
            "texto": f"Existem {custos_fixos_vencidos} custo(s) fixo(s) vencido(s).",
            "url": montar_url_com_params("caixa:custos_fixos_lista", params_vencidos),
            "acao": "Ver custos fixos",
        })

    return alertas
