from .selectors_mes_financeiro import montar_contexto_mes_financeiro
from .serializers_utils import (
    serializar_choices,
    serializar_choices_value_label,
    serializar_valor,
)
from .serializers_dimensoes_operacionais import (
    serializar_cliente_operacional_opcao,
    serializar_contrato_visual_opcao,
    serializar_evento_operacional_opcao,
)
from .services_dimensoes_operacionais import serializar_dimensao_operacional_financeira
from .utils_financeiros import quantizar_moeda


CAMPOS_TOTAIS_MES_FINANCEIRO = (
    "receita_prevista",
    "receita_recebida",
    "receita_aberta",
    "receita_pendente_recebimento",
    "divida_prevista",
    "divida_paga",
    "divida_pendente_pagamento",
    "divida_aberta",
    "divida_vencida",
    "contas_previstas",
    "contas_pagas",
    "contas_pendentes",
    "contas_vencidas",
    "custo_variavel",
    "margem_contribuicao",
    "margem_contribuicao_percentual",
    "lucro_operacional_ebit",
    "saldo_inicial",
    "saldo_inicial_caixa",
    "saldo_previsto",
    "saldo_realizado",
    "saldo_aberto",
    "falta_cobrir",
    "resultado_financeiro",
    "resultado_financeiro_previsto",
    "resultado_financeiro_projetado",
    "resultado_financeiro_realizado",
    "resultado_financeiro_pendente",
    "deficit_caixa",
    "caixa_disponivel",
    "saldo_caixa_disponivel",
    "caixa_disponivel_acumulado",
    "saldo_caixa_disponivel_acumulado",
    "entrada_prevista_fco",
    "saida_prevista_fco",
    "entrada_realizada_fco",
    "saida_realizada_fco",
    "resultado_fco_previsto",
    "resultado_fco_realizado",
    "entrada_prevista_fci",
    "saida_prevista_fci",
    "entrada_realizada_fci",
    "saida_realizada_fci",
    "resultado_fci_previsto",
    "resultado_fci_realizado",
    "entrada_prevista_fcf",
    "saida_prevista_fcf",
    "entrada_realizada_fcf",
    "saida_realizada_fcf",
    "resultado_fcf_previsto",
    "resultado_fcf_realizado",
    "resultado_previsto_periodo",
    "resultado_realizado_periodo",
    "caixa_final_previsto",
    "caixa_final_realizado",
    "caixa_final_mes",
    "finalCashAmount",
    "projectedFinalCashAmount",
    "realizedFinalCashAmount",
)


def montar_payload_mes_financeiro_api(filtros):
    contexto = montar_contexto_mes_financeiro(filtros)
    receitas = [
        serializar_receita_mes(receita)
        for receita in contexto["receitas"]
    ]
    contas_a_pagar = [
        serializar_conta_mes(conta)
        for conta in contexto["contas_a_pagar"]
    ]
    movimentacoes = [
        serializar_movimentacao_mes(movimentacao)
        for movimentacao in contexto["movimentacoes"]
    ]
    totais_payload = {
        campo: serializar_valor(contexto[campo])
        for campo in CAMPOS_TOTAIS_MES_FINANCEIRO
    }
    totais_payload.update({
        "plannedRevenueAmount": totais_payload["receita_prevista"],
        "receivedRevenueAmount": totais_payload["receita_recebida"],
        "pendingReceivableAmount": totais_payload[
            "receita_pendente_recebimento"
        ],
        "plannedPayablesAmount": totais_payload["contas_previstas"],
        "paidPayablesAmount": totais_payload["contas_pagas"],
        "pendingAccountsAmount": totais_payload["contas_pendentes"],
        "overdueAccountsAmount": totais_payload["contas_vencidas"],
        "financialResultAmount": totais_payload["resultado_financeiro"],
        "plannedFinancialResultAmount": totais_payload[
            "resultado_financeiro_previsto"
        ],
        "projectedFinancialResultAmount": totais_payload[
            "resultado_financeiro_projetado"
        ],
        "realizedFinancialResultAmount": totais_payload[
            "resultado_financeiro_realizado"
        ],
        "pendingFinancialResultAmount": totais_payload[
            "resultado_financeiro_pendente"
        ],
        "cashDeficitAmount": totais_payload["deficit_caixa"],
        "variableCostAmount": totais_payload["custo_variavel"],
        "contributionMarginAmount": totais_payload["margem_contribuicao"],
        "contributionMarginPercent": totais_payload[
            "margem_contribuicao_percentual"
        ],
        "operatingProfitEbitAmount": totais_payload["lucro_operacional_ebit"],
        "plannedVariableCostAmount": totais_payload["custo_variavel"],
        "plannedContributionMarginAmount": totais_payload["margem_contribuicao"],
        "plannedContributionMarginPercent": totais_payload[
            "margem_contribuicao_percentual"
        ],
        "plannedOperatingProfitEbitAmount": totais_payload[
            "lucro_operacional_ebit"
        ],
        "initialCashAmount": totais_payload["saldo_inicial"],
        "saldoInicial": totais_payload["saldo_inicial"],
        "availableCashAmount": totais_payload["caixa_disponivel"],
        "cashAvailableAmount": totais_payload["caixa_disponivel"],
        "accumulatedAvailableCashAmount": totais_payload[
            "caixa_disponivel_acumulado"
        ],
    })
    opcoes_payload = serializar_opcoes_mes_financeiro(contexto)
    fluxos_caixa_payload = serializar_fluxos_caixa_mes(contexto)

    return {
        "filters": contexto["filtros"],
        "filtros": contexto["filtros"],
        "filterOptions": opcoes_payload,
        "opcoes": opcoes_payload,
        "totals": totais_payload,
        "totais": totais_payload,
        "financialResult": serializar_resultado_financeiro_mes(contexto),
        "cashAvailability": serializar_disponibilidade_caixa_mes(contexto),
        "cashFlows": fluxos_caixa_payload,
        "fluxos_caixa": fluxos_caixa_payload,
        "dateBasis": {
            "filters": "data_vencimento",
            "receivables": "data_vencimento",
            "payables": "data_vencimento_atual/data_vencimento",
            "realized": "data_recebimento/data_pagamento",
            "availableCash": (
                "saldo inicial + resultado realizado do periodo por FCO + FCI + FCF"
            ),
            "accumulatedAvailableCash": (
                "data_recebimento/data_pagamento acumulado ate data_final"
            ),
            "initialCash": (
                "caixa final realizado consolidado ate o dia anterior a data_inicial"
            ),
        },
        "receivables": receitas,
        "receitas": receitas,
        "payables": contas_a_pagar,
        "contas_a_pagar": contas_a_pagar,
        "movements": movimentacoes,
        "movimentacoes": movimentacoes,
    }


def serializar_resultado_financeiro_mes(contexto):
    return {
        "projectedAmount": serializar_valor(contexto["resultado_financeiro_projetado"]),
        "plannedAmount": serializar_valor(contexto["resultado_financeiro_previsto"]),
        "realizedAmount": serializar_valor(contexto["resultado_financeiro_realizado"]),
        "pendingAmount": serializar_valor(contexto["resultado_financeiro_pendente"]),
        "cashDeficitAmount": serializar_valor(contexto["deficit_caixa"]),
        "availableCashAmount": serializar_valor(contexto["caixa_disponivel"]),
        "cashAvailableAmount": serializar_valor(contexto["caixa_disponivel"]),
        "resultadoFinanceiro": serializar_valor(contexto["resultado_financeiro"]),
        "resultadoFinanceiroProjetado": serializar_valor(
            contexto["resultado_financeiro_projetado"]
        ),
        "resultadoFinanceiroRealizado": serializar_valor(
            contexto["resultado_financeiro_realizado"]
        ),
        "deficitCaixa": serializar_valor(contexto["deficit_caixa"]),
        "caixaDisponivel": serializar_valor(contexto["caixa_disponivel"]),
        "saldoCaixaDisponivel": serializar_valor(contexto["saldo_caixa_disponivel"]),
    }


def serializar_disponibilidade_caixa_mes(contexto):
    diferenca_resultado_periodo = quantizar_moeda(
        contexto["caixa_final_mes"]
        - contexto["resultado_financeiro_realizado"]
    )

    return {
        "initialCashAmount": serializar_valor(contexto["saldo_inicial"]),
        "saldoInicial": serializar_valor(contexto["saldo_inicial"]),
        "availableCashAmount": serializar_valor(
            contexto["caixa_disponivel_acumulado"]
        ),
        "cashAvailableAmount": serializar_valor(
            contexto["caixa_disponivel_acumulado"]
        ),
        "caixaDisponivel": serializar_valor(
            contexto["caixa_disponivel_acumulado"]
        ),
        "saldoCaixaDisponivel": serializar_valor(
            contexto["saldo_caixa_disponivel_acumulado"]
        ),
        "finalCashAmount": serializar_valor(contexto["caixa_final_mes"]),
        "accumulatedAvailableCashAmount": serializar_valor(
            contexto["caixa_disponivel_acumulado"]
        ),
        "cashAvailableUntilDate": serializar_valor(
            contexto["caixa_disponivel_data_referencia"]
        ),
        "periodRealizedAmount": serializar_valor(
            contexto["resultado_financeiro_realizado"]
        ),
        "differenceFromPeriodRealizedAmount": serializar_valor(
            diferenca_resultado_periodo
        ),
        "formula": (
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


def serializar_fluxos_caixa_mes(contexto):
    return {
        chave: serializar_fluxo_caixa_mes(fluxo)
        for chave, fluxo in contexto["fluxos_caixa"].items()
    }


def serializar_fluxo_caixa_mes(fluxo):
    return {
        "code": fluxo["codigo"],
        "codigo": fluxo["codigo"],
        "inflowAmount": serializar_valor(fluxo["entrada_prevista"]),
        "outflowAmount": serializar_valor(fluxo["saida_prevista"]),
        "financialResultAmount": serializar_valor(fluxo["resultado_previsto"]),
        "plannedInflowAmount": serializar_valor(fluxo["entrada_prevista"]),
        "plannedOutflowAmount": serializar_valor(fluxo["saida_prevista"]),
        "realizedInflowAmount": serializar_valor(fluxo["entrada_realizada"]),
        "realizedOutflowAmount": serializar_valor(fluxo["saida_realizada"]),
        "projectedFinancialResultAmount": serializar_valor(fluxo["resultado_previsto"]),
        "realizedFinancialResultAmount": serializar_valor(fluxo["resultado_realizado"]),
        "entrada_prevista": serializar_valor(fluxo["entrada_prevista"]),
        "saida_prevista": serializar_valor(fluxo["saida_prevista"]),
        "entrada_realizada": serializar_valor(fluxo["entrada_realizada"]),
        "saida_realizada": serializar_valor(fluxo["saida_realizada"]),
        "resultado_previsto": serializar_valor(fluxo["resultado_previsto"]),
        "resultado_realizado": serializar_valor(fluxo["resultado_realizado"]),
    }


def serializar_opcoes_mes_financeiro(contexto):
    contratos = [
        serializar_contrato_opcao_mes(contrato)
        for contrato in contexto["contratos_filtro"]
    ]
    eventos = [
        serializar_evento_opcao_mes(evento)
        for evento in contexto["eventos_filtro"]
    ]
    clientes = [
        serializar_cliente_opcao_mes(cliente)
        for cliente in contexto["clientes_filtro"]
    ]
    origens = serializar_choices(contexto["origens_mes_financeiro"])
    status = serializar_choices(contexto["status_mes_financeiro"])

    return {
        "contracts": contratos,
        "contratos": contratos,
        "events": eventos,
        "eventos": eventos,
        "clients": clientes,
        "clientes": clientes,
        "sources": serializar_choices_value_label(contexto["origens_mes_financeiro"]),
        "origens": origens,
        "statuses": serializar_choices_value_label(contexto["status_mes_financeiro"]),
        "status": status,
    }


def serializar_contrato_opcao_mes(contrato):
    opcao = serializar_contrato_visual_opcao(contrato)

    return {
        "id": opcao["id"],
        "value": opcao["value"],
        "label": opcao["label"],
        "codigo": opcao["contractCode"],
        "nome": opcao["contractName"],
        "name": opcao["name"],
        "contractName": opcao["contractName"],
        "cliente": opcao["clientName"],
        "clientName": opcao["clientName"],
        "contractDescription": opcao["contractDescription"],
        "contractCode": opcao["contractCode"],
    }


def serializar_evento_opcao_mes(evento):
    opcao = serializar_evento_operacional_opcao(
        evento,
        event_description_format="iso",
    )

    return {
        "id": evento.id,
        "value": opcao["value"],
        "label": opcao["label"],
        "eventId": opcao["eventId"],
        "eventNumber": opcao["eventNumber"],
        "numero": opcao["eventNumber"],
        "contrato": opcao["contractCode"],
        "contractCode": opcao["contractCode"],
        "contractName": opcao["contractName"],
        "clientId": opcao["clientId"],
        "clientName": opcao["clientName"],
        "eventName": opcao["eventName"],
        "nome": opcao["eventName"],
        "startDate": opcao["startDate"],
        "data_inicio": opcao["dataInicio"],
        "eventDateLabel": opcao["eventDateLabel"],
    }


def serializar_cliente_opcao_mes(cliente):
    opcao = serializar_cliente_operacional_opcao(cliente)

    return {
        "id": cliente.id,
        "value": opcao["value"],
        "label": opcao["label"],
        "clientId": opcao["clientId"],
        "clientName": opcao["clientName"],
        "name": opcao["name"],
        "nome": opcao["name"],
    }


def formatar_data_br(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""


def serializar_receita_mes(receita):
    data_vencimento = serializar_valor(receita.data_vencimento)
    valor_previsto = serializar_valor(receita.valor_previsto)
    valor_recebido = serializar_valor(receita.valor_recebido)
    valor_pendente_recebimento = serializar_valor(
        receita.valor_pendente_recebimento
    )
    status_display = receita.get_status_display()
    dimensao = serializar_dimensao_operacional_financeira(receita)

    return {
        "id": receita.id,
        "data": data_vencimento,
        "dueDate": data_vencimento,
        "description": receita.descricao,
        "receivableDescription": receita.descricao,
        "descricao": receita.descricao,
        "cliente": {
            "id": dimensao["clientId"] or receita.cliente_id,
            "name": dimensao["clientName"],
            "nome": dimensao["clientName"],
        },
        "evento": {
            "id": dimensao["eventId"] or receita.evento_id,
            "contrato": dimensao["contractCode"],
            "contractCode": dimensao["contractCode"],
            "eventNumber": dimensao["eventNumber"],
            "numero": dimensao["eventNumber"],
            "name": dimensao["eventName"],
            "nome": dimensao["eventName"],
        },
        "plannedAmount": valor_previsto,
        "valor_previsto": valor_previsto,
        "receivedAmount": valor_recebido,
        "valor_recebido": valor_recebido,
        "saldo_a_receber": serializar_valor(receita.saldo_a_receber),
        "pendingReceivableAmount": valor_pendente_recebimento,
        "valor_pendente_recebimento": valor_pendente_recebimento,
        "status": receita.status,
        "statusLabel": status_display,
        "status_display": status_display,
    }


def serializar_conta_mes(conta):
    data = serializar_valor(conta["data"])
    previsto = serializar_valor(conta["previsto"])
    pago = serializar_valor(conta["pago"])
    aberto = serializar_valor(conta["aberto"])
    valor_previsto = serializar_valor(conta["valor_previsto"])
    valor_pago = serializar_valor(conta["valor_pago"])
    contas_pendentes = serializar_valor(conta["contas_pendentes"])
    valor_pendente_pagamento = serializar_valor(
        conta["valor_pendente_pagamento"]
    )

    return {
        "id": conta["objeto"].id,
        "data": data,
        "dueDate": data,
        "type": conta["tipo"],
        "tipo": conta["tipo"],
        "description": conta["descricao"],
        "payableDescription": conta["descricao"],
        "descricao": conta["descricao"],
        "reference": conta["referencia"],
        "referencia": conta["referencia"],
        "contractCode": conta["contractCode"],
        "contractName": conta["contractName"],
        "contractLabel": conta["contractLabel"],
        "eventId": conta["eventId"],
        "eventName": conta["eventName"],
        "eventNumber": conta["eventNumber"],
        "eventLabel": conta["eventLabel"],
        "clientId": conta["clientId"],
        "clientName": conta["clientName"],
        "previsto": previsto,
        "pago": pago,
        "aberto": aberto,
        "plannedAmount": valor_previsto,
        "valor_previsto": valor_previsto,
        "paidAmount": valor_pago,
        "valor_pago": valor_pago,
        "pendingAmount": contas_pendentes,
        "contas_pendentes": contas_pendentes,
        "pendingPaymentAmount": valor_pendente_pagamento,
        "valor_pendente_pagamento": valor_pendente_pagamento,
        "status": conta["status"],
        "statusLabel": conta["status_display"],
        "status_display": conta["status_display"],
        "overdueDays": conta["dias_atraso"],
        "dias_atraso": conta["dias_atraso"],
    }


def serializar_movimentacao_mes(movimentacao):
    data = serializar_valor(movimentacao["data"])
    entrada = serializar_valor(movimentacao["entrada"])
    saida = serializar_valor(movimentacao["saida"])
    recebido = serializar_valor(movimentacao["recebido"])
    pago = serializar_valor(movimentacao["pago"])
    aberto = serializar_valor(movimentacao["aberto"])
    entrada_prevista = serializar_valor(movimentacao["entrada_prevista"])
    saida_prevista = serializar_valor(movimentacao["saida_prevista"])
    valor_recebido = serializar_valor(movimentacao["valor_recebido"])
    valor_pago = serializar_valor(movimentacao["valor_pago"])
    contas_pendentes = serializar_valor(movimentacao["contas_pendentes"])
    resultado_financeiro_acumulado = serializar_valor(
        movimentacao["resultado_financeiro_acumulado"]
    )
    resultado_financeiro_previsto_acumulado = serializar_valor(
        movimentacao["resultado_financeiro_previsto_acumulado"]
    )
    resultado_financeiro_realizado_acumulado = serializar_valor(
        movimentacao["resultado_financeiro_realizado_acumulado"]
    )
    deficit_caixa_acumulado = serializar_valor(
        movimentacao["deficit_caixa_acumulado"]
    )

    return {
        "data": data,
        "date": data,
        "type": movimentacao["tipo"],
        "tipo": movimentacao["tipo"],
        "cashFlowGroup": movimentacao.get("fluxo_caixa", movimentacao.get("origem", "")),
        "fluxo_caixa": movimentacao.get("fluxo_caixa", movimentacao.get("origem", "")),
        "origem": movimentacao.get("origem", movimentacao.get("fluxo_caixa", "")),
        "description": movimentacao["descricao"],
        "movementDescription": movimentacao["descricao"],
        "descricao": movimentacao["descricao"],
        "reference": movimentacao["referencia"],
        "referencia": movimentacao["referencia"],
        "contractCode": movimentacao.get("contractCode", ""),
        "contractName": movimentacao.get("contractName", ""),
        "contractLabel": movimentacao.get("contractLabel", ""),
        "eventId": movimentacao.get("eventId"),
        "eventName": movimentacao.get("eventName", ""),
        "eventNumber": movimentacao.get("eventNumber", ""),
        "eventLabel": movimentacao.get("eventLabel", ""),
        "clientId": movimentacao.get("clientId"),
        "clientName": movimentacao.get("clientName", ""),
        "inflowAmount": entrada,
        "entrada": entrada,
        "outflowAmount": saida,
        "saida": saida,
        "receivedAmount": recebido,
        "recebido": recebido,
        "paidAmount": pago,
        "pago": pago,
        "pendingAmount": aberto,
        "aberto": aberto,
        "plannedInflowAmount": entrada_prevista,
        "entrada_prevista": entrada_prevista,
        "plannedOutflowAmount": saida_prevista,
        "saida_prevista": saida_prevista,
        "receivedValue": valor_recebido,
        "valor_recebido": valor_recebido,
        "paidValue": valor_pago,
        "valor_pago": valor_pago,
        "pendingAccountsAmount": contas_pendentes,
        "contas_pendentes": contas_pendentes,
        "status": movimentacao["status"],
        "saldo_previsto_acumulado": serializar_valor(
            movimentacao["saldo_previsto_acumulado"]
        ),
        "saldo_realizado_acumulado": serializar_valor(
            movimentacao["saldo_realizado_acumulado"]
        ),
        "falta_cobrir_acumulada": serializar_valor(
            movimentacao["falta_cobrir_acumulada"]
        ),
        "accumulatedFinancialResult": resultado_financeiro_acumulado,
        "accumulatedFinancialResultAmount": resultado_financeiro_acumulado,
        "resultado_financeiro_acumulado": resultado_financeiro_acumulado,
        "accumulatedProjectedFinancialResult": resultado_financeiro_previsto_acumulado,
        "accumulatedProjectedFinancialResultAmount": resultado_financeiro_previsto_acumulado,
        "resultado_financeiro_previsto_acumulado": resultado_financeiro_previsto_acumulado,
        "accumulatedRealizedFinancialResult": resultado_financeiro_realizado_acumulado,
        "accumulatedRealizedFinancialResultAmount": resultado_financeiro_realizado_acumulado,
        "resultado_financeiro_realizado_acumulado": resultado_financeiro_realizado_acumulado,
        "accumulatedCashDeficit": deficit_caixa_acumulado,
        "accumulatedCashDeficitAmount": deficit_caixa_acumulado,
        "deficit_caixa_acumulado": deficit_caixa_acumulado,
    }
