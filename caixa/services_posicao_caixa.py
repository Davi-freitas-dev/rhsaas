from datetime import timedelta

from django.utils import timezone

from .constants_financeiros import STATUS_REALIZADO
from .selectors_lancamentos import calcular_totais_lancamentos_financeiros
from .utils_financeiros import quantizar_moeda
from .utils_fluxos_caixa import normalizar_data_fluxo_caixa


def montar_posicao_caixa_periodo(filtros, totais_movimentacoes=None):
    filtros_dashboard = normalizar_filtros_posicao_caixa(filtros)

    data_atual = timezone.localdate()
    data_inicial = normalizar_data_fluxo_caixa(filtros_dashboard.get("data_inicial"))
    data_final = normalizar_data_fluxo_caixa(filtros_dashboard.get("data_final"))
    data_final_efetiva = _data_final_efetiva(data_final, data_atual)
    data_referencia = data_final_efetiva.isoformat() if data_final_efetiva else None
    data_saldo_inicial = _data_saldo_inicial(data_inicial, data_atual)
    saldo_inicial = (
        _saldo_efetivo_lancamentos_ate(data_saldo_inicial)
        if data_saldo_inicial
        else quantizar_moeda(0)
    )
    totais_efetivos_periodo = calcular_totais_lancamentos_financeiros(
        _filtros_lancamentos_periodo(
            filtros_dashboard,
            data_inicial,
            data_final_efetiva,
        )
    )
    entradas_efetivas = quantizar_moeda(totais_efetivos_periodo["entradas"])
    saidas_efetivas = quantizar_moeda(totais_efetivos_periodo["saidas"])
    resultado_realizado_periodo = quantizar_moeda(
        entradas_efetivas - saidas_efetivas
    )
    caixa_final = quantizar_moeda(saldo_inicial + resultado_realizado_periodo)
    caixa_acumulado_ate_data = _saldo_efetivo_lancamentos_ate(data_final_efetiva)
    caixa_disponivel_atual = _saldo_efetivo_lancamentos_ate(data_atual)

    return {
        "initialCashAmount": saldo_inicial,
        "realizedInflowAmount": entradas_efetivas,
        "realizedOutflowAmount": saidas_efetivas,
        "periodRealizedAmount": resultado_realizado_periodo,
        "availableCashAmount": caixa_final,
        "finalCashAmount": caixa_final,
        "currentAvailableCashAmount": caixa_disponivel_atual,
        "accumulatedCashUntilDate": caixa_acumulado_ate_data,
        "accumulatedAvailableCashAmount": caixa_acumulado_ate_data,
        "cashAvailableUntilDate": data_referencia,
        "currentCashAvailableUntilDate": data_atual.isoformat(),
        "differenceFromPeriodRealizedAmount": quantizar_moeda(
            caixa_final - resultado_realizado_periodo
        ),
    }


def _data_final_efetiva(data_final, data_atual):
    if data_final is None:
        return data_atual
    if data_final > data_atual:
        return data_atual
    return data_final


def _data_saldo_inicial(data_inicial, data_atual):
    if data_inicial is None:
        return None

    data_saldo = data_inicial - timedelta(days=1)
    if data_saldo > data_atual:
        return data_atual
    return data_saldo


def _filtros_lancamentos_periodo(filtros, data_inicial, data_final_efetiva):
    filtros_lancamentos = {
        "status": STATUS_REALIZADO,
        "eventId": filtros.get("evento_id"),
        "clientId": filtros.get("cliente_id"),
        "contractCode": filtros.get("contrato_codigo"),
    }

    if data_inicial:
        filtros_lancamentos["data_inicial"] = data_inicial.isoformat()

    if data_final_efetiva:
        filtros_lancamentos["data_final"] = data_final_efetiva.isoformat()

    return {
        chave: valor
        for chave, valor in filtros_lancamentos.items()
        if valor not in (None, "")
    }


def _saldo_efetivo_lancamentos_ate(data_limite):
    filtros = {"status": STATUS_REALIZADO}
    if data_limite:
        filtros["data_final"] = data_limite.isoformat()

    totais = calcular_totais_lancamentos_financeiros(filtros)
    return quantizar_moeda(totais["entradas"] - totais["saidas"])


def normalizar_filtros_posicao_caixa(filtros):
    filtros = filtros or {}

    return {
        "data_inicial": _primeiro_valor(filtros, "data_inicial", "startDate"),
        "data_final": _primeiro_valor(filtros, "data_final", "endDate"),
        "evento_id": _primeiro_valor(filtros, "evento_id", "eventId", "evento"),
        "cliente_id": _primeiro_valor(filtros, "cliente_id", "clientId", "cliente"),
        "contrato_codigo": _primeiro_valor(
            filtros,
            "contrato_codigo",
            "contractCode",
        ),
        "status": _primeiro_valor(filtros, "status", "settlementStatus"),
        "periodo_rapido": _primeiro_valor(
            filtros,
            "periodo_rapido",
            "quickPeriod",
        ),
    }


def _primeiro_valor(filtros, *chaves):
    for chave in chaves:
        valor = filtros.get(chave)
        if valor not in (None, ""):
            return valor
    return ""
