from decimal import Decimal
from datetime import date, timedelta

from .utils_financeiros import decimal_zero, quantizar_moeda


FLUXOS_CAIXA = (
    ("fco", "FCO"),
    ("fci", "FCI"),
    ("fcf", "FCF"),
)


def calcular_totais_fluxos_caixa(movimentacoes, saldo_inicial=Decimal("0.00")):
    saldo_inicial = quantizar_moeda(decimal_zero(saldo_inicial))
    totais_por_fluxo = {
        chave: {
            "codigo": rotulo,
            "entrada_prevista": Decimal("0.00"),
            "saida_prevista": Decimal("0.00"),
            "entrada_realizada": Decimal("0.00"),
            "saida_realizada": Decimal("0.00"),
            "resultado_previsto": Decimal("0.00"),
            "resultado_realizado": Decimal("0.00"),
        }
        for chave, rotulo in FLUXOS_CAIXA
    }

    for movimento in movimentacoes:
        chave_fluxo = normalizar_fluxo_caixa(
            movimento.get("fluxo_caixa") or movimento.get("origem") or "FCO"
        )
        if chave_fluxo not in totais_por_fluxo:
            continue

        fluxo = totais_por_fluxo[chave_fluxo]
        fluxo["entrada_prevista"] += decimal_zero(movimento.get("entrada"))
        fluxo["saida_prevista"] += decimal_zero(movimento.get("saida"))
        fluxo["entrada_realizada"] += decimal_zero(movimento.get("recebido"))
        fluxo["saida_realizada"] += decimal_zero(movimento.get("pago"))

    resultado_previsto_periodo = Decimal("0.00")
    resultado_realizado_periodo = Decimal("0.00")
    for fluxo in totais_por_fluxo.values():
        fluxo["entrada_prevista"] = quantizar_moeda(fluxo["entrada_prevista"])
        fluxo["saida_prevista"] = quantizar_moeda(fluxo["saida_prevista"])
        fluxo["entrada_realizada"] = quantizar_moeda(fluxo["entrada_realizada"])
        fluxo["saida_realizada"] = quantizar_moeda(fluxo["saida_realizada"])
        fluxo["resultado_previsto"] = quantizar_moeda(
            fluxo["entrada_prevista"] - fluxo["saida_prevista"]
        )
        fluxo["resultado_realizado"] = quantizar_moeda(
            fluxo["entrada_realizada"] - fluxo["saida_realizada"]
        )
        resultado_previsto_periodo += fluxo["resultado_previsto"]
        resultado_realizado_periodo += fluxo["resultado_realizado"]

    resultado_previsto_periodo = quantizar_moeda(resultado_previsto_periodo)
    resultado_realizado_periodo = quantizar_moeda(resultado_realizado_periodo)
    caixa_final_previsto = quantizar_moeda(
        saldo_inicial + resultado_previsto_periodo
    )
    caixa_final_realizado = quantizar_moeda(
        saldo_inicial + resultado_realizado_periodo
    )

    return {
        "fluxos_caixa": totais_por_fluxo,
        "saldo_inicial": saldo_inicial,
        "saldo_inicial_caixa": saldo_inicial,
        "initialCashAmount": saldo_inicial,
        "resultado_previsto_periodo": resultado_previsto_periodo,
        "resultado_realizado_periodo": resultado_realizado_periodo,
        "projectedPeriodFinancialResultAmount": resultado_previsto_periodo,
        "realizedPeriodFinancialResultAmount": resultado_realizado_periodo,
        "entrada_prevista_fco": totais_por_fluxo["fco"]["entrada_prevista"],
        "saida_prevista_fco": totais_por_fluxo["fco"]["saida_prevista"],
        "entrada_realizada_fco": totais_por_fluxo["fco"]["entrada_realizada"],
        "saida_realizada_fco": totais_por_fluxo["fco"]["saida_realizada"],
        "resultado_fco_previsto": totais_por_fluxo["fco"]["resultado_previsto"],
        "resultado_fco_realizado": totais_por_fluxo["fco"]["resultado_realizado"],
        "entrada_prevista_fci": totais_por_fluxo["fci"]["entrada_prevista"],
        "saida_prevista_fci": totais_por_fluxo["fci"]["saida_prevista"],
        "entrada_realizada_fci": totais_por_fluxo["fci"]["entrada_realizada"],
        "saida_realizada_fci": totais_por_fluxo["fci"]["saida_realizada"],
        "resultado_fci_previsto": totais_por_fluxo["fci"]["resultado_previsto"],
        "resultado_fci_realizado": totais_por_fluxo["fci"]["resultado_realizado"],
        "entrada_prevista_fcf": totais_por_fluxo["fcf"]["entrada_prevista"],
        "saida_prevista_fcf": totais_por_fluxo["fcf"]["saida_prevista"],
        "entrada_realizada_fcf": totais_por_fluxo["fcf"]["entrada_realizada"],
        "saida_realizada_fcf": totais_por_fluxo["fcf"]["saida_realizada"],
        "resultado_fcf_previsto": totais_por_fluxo["fcf"]["resultado_previsto"],
        "resultado_fcf_realizado": totais_por_fluxo["fcf"]["resultado_realizado"],
        "caixa_final_previsto": caixa_final_previsto,
        "caixa_final_realizado": caixa_final_realizado,
        "caixa_final_mes": caixa_final_realizado,
        "finalCashAmount": caixa_final_realizado,
        "projectedFinalCashAmount": caixa_final_previsto,
        "realizedFinalCashAmount": caixa_final_realizado,
    }


def calcular_saldo_inicial_fluxo_caixa(data_inicial, saldo_inicial_configurado=None):
    if saldo_inicial_configurado is not None:
        return quantizar_moeda(decimal_zero(saldo_inicial_configurado))

    data_periodo = normalizar_data_fluxo_caixa(data_inicial)
    if data_periodo is None:
        return Decimal("0.00")

    from .services_validacao_pagamentos import saldo_caixa_disponivel

    return saldo_caixa_disponivel(data_periodo - timedelta(days=1))


def normalizar_data_fluxo_caixa(valor):
    if isinstance(valor, date):
        return valor

    try:
        return date.fromisoformat(str(valor or ""))
    except ValueError:
        return None


def normalizar_fluxo_caixa(valor):
    valor = str(valor or "").strip().lower()
    if valor in {"fci", "investimento", "investimentos"}:
        return "fci"
    if valor in {"fcf", "financiamento", "financiamentos", "parcela financeira"}:
        return "fcf"
    return "fco"
