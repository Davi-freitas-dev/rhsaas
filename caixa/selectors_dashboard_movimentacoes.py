from decimal import Decimal

from .constants_financeiros import TIPO_FLUXO_ENTRADA, TIPO_FLUXO_SAIDA
from .selectors_dashboard_urls import limpar_classe_css
from .services_dimensoes_operacionais import (
    dados_parcela_divida_sem_lazy,
    serializar_dimensao_operacional_financeira,
)
from .utils_financeiros import decimal_zero, quantizar_moeda
from .utils_fluxos_caixa import calcular_totais_fluxos_caixa


def _referencia_receita_sem_lazy(receita):
    dimensao = serializar_dimensao_operacional_financeira(receita)
    cliente_label = dimensao["clientDisplayName"] or dimensao["clientName"]
    evento_nome = dimensao["eventName"]
    if cliente_label and evento_nome:
        return f"{cliente_label} / {evento_nome}"
    return cliente_label or evento_nome


def _nome_evento_sem_lazy(objeto):
    return serializar_dimensao_operacional_financeira(objeto)["eventName"]


def montar_movimentacoes_dashboard(
    receitas,
    despesas,
    custos_fixos,
    investimentos,
    lista_parcelas_divida,
    financiamentos=None,
    saldo_inicial=Decimal("0.00"),
):
    movimentacoes = []
    financiamentos = [] if financiamentos is None else financiamentos
    saldo_inicial = quantizar_moeda(saldo_inicial)

    for receita in receitas:
        movimentacoes.append({
            "data": receita.data_vencimento,
            "tipo": "Receita",
            "descricao": receita.descricao,
            "referencia": _referencia_receita_sem_lazy(receita),
            "entrada": receita.valor_previsto,
            "saida": Decimal("0.00"),
            "recebido": receita.valor_recebido,
            "pago": Decimal("0.00"),
            "aberto": Decimal("0.00"),
            "status": receita.status,
            "status_classe": limpar_classe_css(receita.status),
            "origem": "FCO",
            **serializar_dimensao_operacional_financeira(receita),
        })

    for despesa in despesas:
        movimentacoes.append({
            "data": despesa.data_vencimento,
            "tipo": "Despesa",
            "descricao": despesa.descricao,
            "referencia": _nome_evento_sem_lazy(despesa),
            "entrada": Decimal("0.00"),
            "saida": despesa.valor_previsto,
            "recebido": Decimal("0.00"),
            "pago": despesa.valor_pago,
            "aberto": despesa.saldo_a_pagar,
            "status": despesa.status,
            "status_classe": limpar_classe_css(despesa.status),
            "origem": "FCO",
            **serializar_dimensao_operacional_financeira(despesa),
        })

    for custo_fixo in custos_fixos:
        movimentacoes.append({
            "data": custo_fixo.data_vencimento,
            "tipo": "Custo fixo",
            "descricao": custo_fixo.descricao,
            "referencia": (
                custo_fixo.get_categoria_display()
                if hasattr(custo_fixo, "get_categoria_display")
                else custo_fixo.categoria
            ),
            "entrada": Decimal("0.00"),
            "saida": custo_fixo.valor_previsto,
            "recebido": Decimal("0.00"),
            "pago": custo_fixo.valor_pago,
            "aberto": custo_fixo.valor_pendente_pagamento,
            "status": custo_fixo.status,
            "status_classe": limpar_classe_css(custo_fixo.status),
            "origem": "FCO",
            **serializar_dimensao_operacional_financeira(None),
        })

    for investimento in investimentos:
        movimentacoes.append({
            "data": investimento.data_prevista,
            "tipo": "Investimento",
            "descricao": investimento.descricao,
            "referencia": investimento.get_categoria_display(),
            "entrada": investimento.valor_previsto if investimento.tipo_fluxo == "entrada" else Decimal("0.00"),
            "saida": investimento.valor_previsto if investimento.tipo_fluxo == "saida" else Decimal("0.00"),
            "recebido": investimento.valor_realizado if investimento.tipo_fluxo == "entrada" else Decimal("0.00"),
            "pago": investimento.valor_realizado if investimento.tipo_fluxo == "saida" else Decimal("0.00"),
            "aberto": investimento.saldo_restante if investimento.tipo_fluxo == "saida" else Decimal("0.00"),
            "status": investimento.status,
            "status_classe": limpar_classe_css(investimento.status),
            "origem": "FCI",
            **serializar_dimensao_operacional_financeira(investimento),
        })

    for financiamento in financiamentos:
        is_entrada = financiamento.tipo_fluxo == TIPO_FLUXO_ENTRADA
        is_saida = financiamento.tipo_fluxo == TIPO_FLUXO_SAIDA
        movimentacoes.append({
            "data": financiamento.data_prevista,
            "tipo": "Movimentação de financiamento",
            "descricao": financiamento.descricao,
            "referencia": financiamento.get_categoria_display(),
            "entrada": financiamento.valor_previsto if is_entrada else Decimal("0.00"),
            "saida": financiamento.valor_previsto if is_saida else Decimal("0.00"),
            "recebido": financiamento.valor_realizado if is_entrada else Decimal("0.00"),
            "pago": financiamento.valor_realizado if is_saida else Decimal("0.00"),
            "aberto": financiamento.saldo_restante if is_saida else Decimal("0.00"),
            "status": financiamento.status,
            "status_classe": limpar_classe_css(financiamento.status),
            "origem": "FCF",
            **serializar_dimensao_operacional_financeira(financiamento),
        })

    for parcela in lista_parcelas_divida:
        dados_divida = dados_parcela_divida_sem_lazy(parcela)
        movimentacoes.append({
            "data": parcela.data_vencimento_atual,
            "tipo": "Parcela Financeira",
            "descricao": dados_divida["descricao"],
            "referencia": dados_divida["referencia"],
            "entrada": Decimal("0.00"),
            "saida": parcela.valor_total_devido,
            "recebido": Decimal("0.00"),
            "pago": parcela.valor_pago,
            "aberto": parcela.valor_pendente_pagamento,
            "status": parcela.status,
            "status_classe": limpar_classe_css(parcela.status),
            "origem": "FCF",
            **serializar_dimensao_operacional_financeira(dados_divida["divida"]),
        })

    movimentacoes.sort(key=lambda item: (item["data"] or "", item["tipo"]))

    resultado_financeiro_previsto_acumulado = saldo_inicial
    resultado_financeiro_realizado_acumulado = saldo_inicial
    contas_pendentes_acumuladas = Decimal("0.00")
    for mov in movimentacoes:
        entrada = decimal_zero(mov.get("entrada"))
        saida = decimal_zero(mov.get("saida"))
        recebido = decimal_zero(mov.get("recebido"))
        pago = decimal_zero(mov.get("pago"))
        contas_pendentes = decimal_zero(mov.get("aberto"))

        resultado_financeiro_previsto_acumulado += entrada
        resultado_financeiro_previsto_acumulado -= saida
        resultado_financeiro_realizado_acumulado += recebido
        resultado_financeiro_realizado_acumulado -= pago
        contas_pendentes_acumuladas += contas_pendentes

        caixa_realizado_disponivel = (
            resultado_financeiro_realizado_acumulado
            if resultado_financeiro_realizado_acumulado > Decimal("0.00")
            else Decimal("0.00")
        )
        deficit_caixa_base = contas_pendentes_acumuladas - caixa_realizado_disponivel

        resultado_financeiro_acumulado = quantizar_moeda(
            resultado_financeiro_previsto_acumulado
        )
        resultado_financeiro_realizado = quantizar_moeda(
            resultado_financeiro_realizado_acumulado
        )
        deficit_caixa_acumulado = quantizar_moeda(
            deficit_caixa_base
            if deficit_caixa_base > Decimal("0.00")
            else Decimal("0.00")
        )

        mov["entrada_prevista"] = quantizar_moeda(entrada)
        mov["saida_prevista"] = quantizar_moeda(saida)
        mov["valor_recebido"] = quantizar_moeda(recebido)
        mov["valor_pago"] = quantizar_moeda(pago)
        mov["contas_pendentes"] = quantizar_moeda(contas_pendentes)
        mov["saldo_acumulado"] = resultado_financeiro_acumulado
        mov["saldo_previsto_acumulado"] = resultado_financeiro_acumulado
        mov["saldo_realizado_acumulado"] = resultado_financeiro_realizado
        mov["falta_cobrir_acumulada"] = deficit_caixa_acumulado
        mov["resultado_financeiro_acumulado"] = resultado_financeiro_acumulado
        mov["resultado_financeiro_previsto_acumulado"] = resultado_financeiro_acumulado
        mov["resultado_financeiro_realizado_acumulado"] = resultado_financeiro_realizado
        mov["deficit_caixa_acumulado"] = deficit_caixa_acumulado

    totais_fluxos_caixa = calcular_totais_fluxos_caixa(
        movimentacoes,
        saldo_inicial=saldo_inicial,
    )

    total_entrada = sum(
        (decimal_zero(mov.get("entrada")) for mov in movimentacoes),
        Decimal("0.00"),
    )
    total_saida = sum(
        (decimal_zero(mov.get("saida")) for mov in movimentacoes),
        Decimal("0.00"),
    )
    total_recebido = sum(
        (decimal_zero(mov.get("recebido")) for mov in movimentacoes),
        Decimal("0.00"),
    )
    total_pago = sum(
        (decimal_zero(mov.get("pago")) for mov in movimentacoes),
        Decimal("0.00"),
    )
    total_contas_pendentes = sum(
        (decimal_zero(mov.get("aberto")) for mov in movimentacoes),
        Decimal("0.00"),
    )
    total_entrada = quantizar_moeda(total_entrada)
    total_saida = quantizar_moeda(total_saida)
    total_recebido = quantizar_moeda(total_recebido)
    total_pago = quantizar_moeda(total_pago)
    total_contas_pendentes = quantizar_moeda(total_contas_pendentes)
    resultado_financeiro_realizado = quantizar_moeda(total_recebido - total_pago)
    caixa_final_realizado = quantizar_moeda(
        saldo_inicial + resultado_financeiro_realizado
    )
    caixa_realizado_disponivel = (
        caixa_final_realizado
        if caixa_final_realizado > Decimal("0.00")
        else Decimal("0.00")
    )
    deficit_caixa_base = total_contas_pendentes - caixa_realizado_disponivel
    resultado_financeiro = quantizar_moeda(total_entrada - total_saida)
    deficit_caixa = quantizar_moeda(
        deficit_caixa_base if deficit_caixa_base > Decimal("0.00") else Decimal("0.00")
    )

    return {
        "movimentacoes": movimentacoes,
        "total_entrada_movimentacoes_prevista": total_entrada,
        "total_saida_movimentacoes_prevista": total_saida,
        "saldo_movimentacoes_previsto": resultado_financeiro,
        "total_recebido_movimentacoes": total_recebido,
        "total_pago_movimentacoes": total_pago,
        "total_aberto_movimentacoes": total_contas_pendentes,
        "saldo_movimentacoes_realizado": resultado_financeiro_realizado,
        "falta_cobrir_movimentacoes": deficit_caixa,
        "total_entradas_previstas": total_entrada,
        "total_saidas_previstas": total_saida,
        "total_valor_recebido": total_recebido,
        "total_valor_pago": total_pago,
        "total_contas_pendentes": total_contas_pendentes,
        "total_contas_pendentes_movimentacoes": total_contas_pendentes,
        "resultado_financeiro": resultado_financeiro,
        "resultado_financeiro_movimentacoes": resultado_financeiro,
        "resultado_financeiro_realizado": resultado_financeiro_realizado,
        "resultado_financeiro_realizado_movimentacoes": resultado_financeiro_realizado,
        "deficit_caixa": deficit_caixa,
        "deficit_caixa_movimentacoes": deficit_caixa,
        **totais_fluxos_caixa,
    }
