from .selectors_financiamentos import montar_contexto_financiamentos
from .serializers_dimensoes_operacionais import (
    serializar_opcoes_entidades_operacionais,
    serializar_dimensao_operacional,
    serializar_opcoes_dimensoes_operacionais,
)
from .serializers_utils import (
    serializar_choices,
    serializar_choices_value_label,
    serializar_valor,
)
from .services_dimensoes_operacionais import relacao_carregada


CAMPOS_TOTAIS_FINANCIAMENTOS = (
    "total_previsto_entrada",
    "total_previsto_saida",
    "total_realizado_entrada",
    "total_realizado_saida",
    "saldo_previsto_fcf",
    "saldo_realizado_fcf",
    "resultado_financeiro_fcf_projetado",
    "resultado_financeiro_fcf_realizado",
    "total_contas_pendentes",
    "total_em_aberto",
    "total_contas_vencidas",
    "total_vencido",
    "contas_pendentes",
    "contas_vencidas",
    "total_parcelas_previsto_saida",
    "total_parcelas_realizado_saida",
    "total_parcelas_contas_pendentes",
    "total_movimentacoes_financiamento_previsto_entrada",
    "total_movimentacoes_financiamento_previsto_saida",
    "total_movimentacoes_financiamento_realizado_entrada",
    "total_movimentacoes_financiamento_realizado_saida",
    "total_movimentacoes_financiamento_contas_pendentes",
)

CAMPOS_ESTATISTICAS_FINANCIAMENTOS = (
    "quantidade_dividas",
    "quantidade_dividas_pendentes",
    "quantidade_dividas_listadas",
    "quantidade_parcelas",
    "quantidade_parcelas_vencidas",
    "quantidade_movimentacoes_financiamento",
    "quantidade_movimentacoes_financiamento_vencidas",
    "quantidade_movimentacoes_financiamento_automaticas",
    "quantidade_movimentacoes_financiamento_manuais",
)


def montar_payload_financiamentos_api(filtros, session, usuario=None):
    contexto = montar_contexto_financiamentos(filtros, session)
    pode_pagar_parcela = bool(
        usuario and usuario.has_perm("caixa.add_pagamentoparceladivida")
    )
    dividas = [
        serializar_divida_financiamento(divida)
        for divida in contexto["dividas"]
    ]
    parcelas = [
        serializar_parcela_financiamento(
            parcela,
            pode_pagar_parcela=pode_pagar_parcela,
        )
        for parcela in contexto["parcelas"]
    ]
    movimentacoes_financiamento = [
        serializar_movimentacao_financiamento(movimentacao)
        for movimentacao in contexto["movimentacoes_financiamento"]
    ]
    grupos_credor = [
        serializar_grupo_credor_financiamento(
            grupo,
            pode_pagar_parcela=pode_pagar_parcela,
        )
        for grupo in contexto["grupos_credor"]
    ]
    filtros_payload = {
        **contexto["filtros"],
        "periodo_rapido": contexto["periodo_rapido"],
    }
    opcoes_payload = serializar_opcoes_financiamentos(contexto)
    totais_payload = {
        campo: serializar_valor(contexto[campo])
        for campo in CAMPOS_TOTAIS_FINANCIAMENTOS
    }
    totais_payload.update({
        "plannedInflowAmount": totais_payload["total_previsto_entrada"],
        "plannedOutflowAmount": totais_payload["total_previsto_saida"],
        "realizedInflowAmount": totais_payload["total_realizado_entrada"],
        "realizedOutflowAmount": totais_payload["total_realizado_saida"],
        "projectedFinancialResultAmount": totais_payload[
            "resultado_financeiro_fcf_projetado"
        ],
        "realizedFinancialResultAmount": totais_payload[
            "resultado_financeiro_fcf_realizado"
        ],
        "pendingAccountsAmount": totais_payload["total_contas_pendentes"],
        "pendingPaymentAmount": totais_payload["total_contas_pendentes"],
        "overdueAccountsAmount": totais_payload["total_contas_vencidas"],
    })
    estatisticas_payload = {
        campo: contexto[campo]
        for campo in CAMPOS_ESTATISTICAS_FINANCIAMENTOS
    }
    estatisticas_payload.update({
        "pendingDebtsCount": contexto["quantidade_dividas_pendentes"],
        "listedDebtsCount": contexto["quantidade_dividas_listadas"],
        "debtsCount": contexto["quantidade_dividas"],
        "installmentsCount": contexto["quantidade_parcelas"],
        "overdueInstallmentsCount": contexto["quantidade_parcelas_vencidas"],
        "financingMovementsCount": contexto[
            "quantidade_movimentacoes_financiamento"
        ],
        "overdueFinancingMovementsCount": contexto[
            "quantidade_movimentacoes_financiamento_vencidas"
        ],
        "automaticFinancingMovementsCount": contexto[
            "quantidade_movimentacoes_financiamento_automaticas"
        ],
        "manualFinancingMovementsCount": contexto[
            "quantidade_movimentacoes_financiamento_manuais"
        ],
    })

    return {
        "filters": filtros_payload,
        "filtros": filtros_payload,
        "filterOptions": opcoes_payload,
        "opcoes": opcoes_payload,
        "totals": totais_payload,
        "totais": totais_payload,
        "statistics": estatisticas_payload,
        "estatisticas": estatisticas_payload,
        "projectedFinancingFlow": serializar_fluxo_financiamento(
            contexto["total_previsto_entrada"],
            contexto["total_previsto_saida"],
            contexto["resultado_financeiro_fcf_projetado"],
        ),
        "realizedFinancingFlow": serializar_fluxo_financiamento(
            contexto["total_realizado_entrada"],
            contexto["total_realizado_saida"],
            contexto["resultado_financeiro_fcf_realizado"],
        ),
        "dateBasis": {
            "filters": "data_vencimento_atual/data_prevista",
            "debtInstallments": "data_vencimento_atual",
            "financingMovements": "data_prevista",
            "realized": "data_pagamento/data_realizacao",
        },
        "debts": dividas,
        "dividas": dividas,
        "installments": parcelas,
        "parcelas": parcelas,
        "financingMovements": movimentacoes_financiamento,
        "movimentacoes_financiamento": movimentacoes_financiamento,
        "creditorGroups": grupos_credor,
        "grupos_credor": grupos_credor,
    }


def serializar_fluxo_financiamento(entradas, saidas, resultado_financeiro):
    entradas_serializadas = serializar_valor(entradas)
    saidas_serializadas = serializar_valor(saidas)
    resultado_serializado = serializar_valor(resultado_financeiro)

    return {
        "entradas": entradas_serializadas,
        "inflowAmount": entradas_serializadas,
        "saidas": saidas_serializadas,
        "outflowAmount": saidas_serializadas,
        "resultadoFinanceiro": resultado_serializado,
        "financialResultAmount": resultado_serializado,
        "resultado_financeiro": resultado_serializado,
    }


def serializar_opcoes_financiamentos(contexto):
    credores = list(contexto["credores_filtro"])
    credores_cadastrados = list(contexto.get("credores_cadastrados_filtro", []))
    clientes = serializar_opcoes_entidades_operacionais(
        contexto,
        incluir_clientes=True,
    )["clients"]

    return {
        "creditors": [
            serializar_credor_financiamento(credor)
            for credor in credores_cadastrados
        ],
        "credores": credores,
        "debtTypes": serializar_choices_value_label(contexto["tipos_divida"]),
        "tipos_divida": serializar_choices(contexto["tipos_divida"]),
        "installmentStatuses": serializar_choices_value_label(contexto["status_parcelas"]),
        "status_parcelas": serializar_choices(contexto["status_parcelas"]),
        "financingCategories": serializar_choices_value_label(contexto["categorias_financiamento"]),
        "categorias_financiamento": serializar_choices(contexto["categorias_financiamento"]),
        "financingFlowTypes": serializar_choices_value_label(contexto["tipos_fluxo_financiamento"]),
        "tipos_fluxo_financiamento": serializar_choices(contexto["tipos_fluxo_financiamento"]),
        "financingStatuses": serializar_choices_value_label(contexto["status_financiamento"]),
        "status_financiamento": serializar_choices(contexto["status_financiamento"]),
        "financingMovementSourceTypes": serializar_choices_value_label(
            contexto["tipos_origem_movimentacao_financiamento"]
        ),
        "movementSourceTypes": serializar_choices_value_label(
            contexto["tipos_origem_movimentacao_financiamento"]
        ),
        "origens_movimentacao_financiamento": serializar_choices(
            contexto["tipos_origem_movimentacao_financiamento"]
        ),
        **serializar_opcoes_dimensoes_operacionais(contexto),
        "clients": clientes,
        "clientes": clientes,
    }


def serializar_credor_financiamento(credor):
    creditor_id = str(credor.id)
    criado_em = serializar_valor(credor.criado_em)
    atualizado_em = serializar_valor(credor.atualizado_em)

    return {
        "id": creditor_id,
        "value": creditor_id,
        "label": credor.nome,
        "name": credor.nome,
        "credor_id": credor.id,
        "creditorId": credor.id,
        "credor_nome": credor.nome,
        "creditorName": credor.nome,
        "document": credor.documento,
        "isActive": credor.ativo,
        "notes": credor.observacao,
        "observacao": credor.observacao,
        "createdAt": criado_em,
        "criado_em": criado_em,
        "updatedAt": atualizado_em,
        "atualizado_em": atualizado_em,
    }


def montar_payload_credores_financiamentos_api(credores, *, only_active=True):
    opcoes = [serializar_credor_financiamento(credor) for credor in credores]

    return {
        "creditors": opcoes,
        "credores": [opcao["label"] for opcao in opcoes],
        "meta": {
            "count": len(opcoes),
            "onlyActive": only_active,
            "source": "cadastro_credor",
        },
    }


def id_credor_divida(divida):
    return divida.credor_cadastro_id


def nome_credor_divida(divida):
    credor_cadastro = relacao_carregada(divida, "credor_cadastro")
    if credor_cadastro:
        return credor_cadastro.nome

    return divida.credor


def serializar_divida_financiamento(divida):
    tipo_display = divida.get_tipo_display()
    status_display = divida.get_status_display()
    data_contratacao = serializar_valor(divida.data_contratacao)
    valor_contratado = serializar_valor(divida.valor_contratado)
    creditor_id = id_credor_divida(divida)
    creditor_name = nome_credor_divida(divida)

    return {
        "id": divida.id,
        "debtId": divida.id,
        "descricao": divida.descricao,
        "description": divida.descricao,
        "debtDescription": divida.descricao,
        "credor_id": creditor_id,
        "creditorId": creditor_id,
        "credor_nome": creditor_name,
        "creditorName": creditor_name,
        "credor": creditor_name,
        "creditor": creditor_name,
        "tipo": divida.tipo,
        "type": divida.tipo,
        "tipo_display": tipo_display,
        "typeLabel": tipo_display,
        "status": divida.status,
        "status_display": status_display,
        "statusLabel": status_display,
        "data_contratacao": data_contratacao,
        "contractedDate": data_contratacao,
        "valor_contratado": valor_contratado,
        "contractedAmount": valor_contratado,
        "quantidade_parcelas": divida.quantidade_parcelas,
        "installmentsCount": divida.quantidade_parcelas,
        **serializar_dimensao_operacional(divida),
    }


def serializar_parcela_financiamento(parcela, *, pode_pagar_parcela=False):
    data_vencimento_original = serializar_valor(
        parcela.data_vencimento_original
    )
    data_vencimento_atual = serializar_valor(parcela.data_vencimento_atual)
    valor_total_devido = serializar_valor(parcela.valor_total_devido)
    valor_pago = serializar_valor(parcela.valor_pago)
    valor_pendente_pagamento = serializar_valor(
        parcela.valor_pendente_pagamento
    )
    status_display = parcela.get_status_display()
    divida = relacao_carregada(parcela, "divida")
    creditor_id = id_credor_divida(divida) if divida else None
    creditor_name = nome_credor_divida(divida) if divida else ""
    debt_description = divida.descricao if divida else ""
    installment_label = (
        f"{parcela.numero_parcela}/{divida.quantidade_parcelas or parcela.numero_parcela}"
        if divida
        else str(parcela.numero_parcela)
    )

    return {
        "id": parcela.id,
        "divida_id": parcela.divida_id,
        "debtId": parcela.divida_id,
        "credor_id": creditor_id,
        "creditorId": creditor_id,
        "credor_nome": creditor_name,
        "creditorName": creditor_name,
        "credor": creditor_name,
        "creditor": creditor_name,
        "descricao_divida": debt_description,
        "debtDescription": debt_description,
        "numero_parcela": parcela.numero_parcela,
        "installmentNumber": parcela.numero_parcela,
        "rotulo_parcela": installment_label,
        "installmentLabel": installment_label,
        "data_vencimento_original": data_vencimento_original,
        "originalDueDate": data_vencimento_original,
        "data_vencimento_atual": data_vencimento_atual,
        "dueDate": data_vencimento_atual,
        "valor_total_devido": valor_total_devido,
        "totalDueAmount": valor_total_devido,
        "valor_pago": valor_pago,
        "paidAmount": valor_pago,
        "valor_pendente_pagamento": valor_pendente_pagamento,
        "pendingPaymentAmount": valor_pendente_pagamento,
        "contas_pendentes": valor_pendente_pagamento,
        "pendingAccountsAmount": valor_pendente_pagamento,
        "saldo_em_aberto": serializar_valor(parcela.saldo_em_aberto),
        "disponivel_para_pagamento": parcela.disponivel_para_pagamento,
        "availableForPayment": parcela.disponivel_para_pagamento,
        "status": parcela.status,
        "status_display": status_display,
        "statusLabel": status_display,
        "dias_atraso": parcela.dias_atraso,
        "overdueDays": parcela.dias_atraso,
        "baixado_manualmente": parcela.baixado_manualmente,
        "manuallySettled": parcela.baixado_manualmente,
        "actionHints": serializar_action_hints_parcela_financiamento(
            parcela,
            pode_pagar_parcela=pode_pagar_parcela,
        ),
        **serializar_dimensao_operacional(divida),
    }


def serializar_action_hints_parcela_financiamento(parcela, *, pode_pagar_parcela=False):
    acao_pagamento = None
    if parcela.disponivel_para_pagamento and pode_pagar_parcela:
        acao_pagamento = montar_action_hint_financiamento(
            "legacyPayment",
            "Pagar parcela FCF",
            f"/fcf/parcelas/{parcela.id}/pagar/",
        )

    acoes = [acao for acao in (acao_pagamento,) if acao]

    return {
        "primary": acao_pagamento,
        "admin": None,
        "actions": acoes,
    }


def montar_action_hint_financiamento(tipo, label, path, query=None):
    return {
        "type": tipo,
        "label": label,
        "target": "backend",
        "path": path,
        "query": limpar_query_action_hint_financiamento(query or {}),
    }


def limpar_query_action_hint_financiamento(query):
    return {
        chave: valor
        for chave, valor in query.items()
        if valor not in (None, "")
    }


def serializar_movimentacao_financiamento(movimentacao):
    categoria_display = movimentacao.get_categoria_display()
    tipo_fluxo_display = movimentacao.get_tipo_fluxo_display()
    divida_origem = relacao_carregada(movimentacao, "divida_financeira")
    origem_automatica = divida_origem is not None
    origem_movimentacao = "divida_automatica" if origem_automatica else "manual"
    origem_movimentacao_display = (
        "Entrada automatica da divida"
        if origem_automatica
        else "Movimentacao FCF manual"
    )
    valor_previsto = serializar_valor(movimentacao.valor_previsto)
    valor_realizado = serializar_valor(movimentacao.valor_realizado)
    valor_pendente = serializar_valor(
        movimentacao.valor_pendente_realizacao
    )
    data_prevista = serializar_valor(movimentacao.data_prevista)
    data_realizacao = serializar_valor(movimentacao.data_realizacao)
    status_display = movimentacao.get_status_display()
    debt_creditor_id = id_credor_divida(divida_origem) if divida_origem else None
    debt_creditor_name = nome_credor_divida(divida_origem) if divida_origem else ""
    dias_atraso = getattr(movimentacao, "dias_atraso", 0)

    return {
        "id": movimentacao.id,
        "description": movimentacao.descricao,
        "financingMovementDescription": movimentacao.descricao,
        "descricao": movimentacao.descricao,
        "category": movimentacao.categoria,
        "categoria": movimentacao.categoria,
        "categoryLabel": categoria_display,
        "categoria_display": categoria_display,
        "flowType": movimentacao.tipo_fluxo,
        "tipo_fluxo": movimentacao.tipo_fluxo,
        "flowTypeLabel": tipo_fluxo_display,
        "tipo_fluxo_display": tipo_fluxo_display,
        "plannedAmount": valor_previsto,
        "valor_previsto": valor_previsto,
        "realizedAmount": valor_realizado,
        "valor_realizado": valor_realizado,
        "pendingAmount": valor_pendente,
        "pendingRealizationAmount": valor_pendente,
        "valor_pendente_realizacao": valor_pendente,
        "plannedDate": data_prevista,
        "data_prevista": data_prevista,
        "realizedDate": data_realizacao,
        "data_realizacao": data_realizacao,
        "status": movimentacao.status,
        "statusLabel": status_display,
        "status_display": status_display,
        "sourceType": origem_movimentacao,
        "movementSourceType": origem_movimentacao,
        "origem_movimentacao": origem_movimentacao,
        "sourceTypeLabel": origem_movimentacao_display,
        "movementSourceTypeLabel": origem_movimentacao_display,
        "origem_movimentacao_display": origem_movimentacao_display,
        "automaticFromDebt": origem_automatica,
        "isAutomaticFromDebt": origem_automatica,
        "entrada_automatica_divida": origem_automatica,
        "debtId": divida_origem.id if divida_origem else None,
        "divida_id": divida_origem.id if divida_origem else None,
        "debtCreditorId": debt_creditor_id,
        "credor_divida_id": debt_creditor_id,
        "debtCreditor": debt_creditor_name,
        "credor_divida": debt_creditor_name,
        "debtCreditorName": debt_creditor_name,
        "nome_credor_divida": debt_creditor_name,
        "debtDescription": divida_origem.descricao if divida_origem else "",
        "descricao_divida": divida_origem.descricao if divida_origem else "",
        "dias_atraso": dias_atraso,
        "overdueDays": dias_atraso,
        **serializar_dimensao_operacional(movimentacao),
    }


def serializar_grupo_credor_financiamento(grupo, *, pode_pagar_parcela=False):
    subtotal_devido = serializar_valor(grupo["subtotal_devido"])
    subtotal_pago = serializar_valor(grupo["subtotal_pago"])
    subtotal_contas_pendentes = serializar_valor(
        grupo["subtotal_contas_pendentes"]
    )
    dividas = [
        serializar_grupo_divida_financiamento(
            grupo_divida,
            pode_pagar_parcela=pode_pagar_parcela,
        )
        for grupo_divida in grupo["dividas"]
    ]

    return {
        "credor_id": grupo["credor_id"],
        "creditorId": grupo["creditorId"],
        "credor_nome": grupo["credor_nome"],
        "creditorName": grupo["creditorName"],
        "credor": grupo["credor"],
        "creditor": grupo["credor"],
        "subtotal_devido": subtotal_devido,
        "subtotalDueAmount": subtotal_devido,
        "subtotal_pago": subtotal_pago,
        "subtotalPaidAmount": subtotal_pago,
        "subtotal_contas_pendentes": subtotal_contas_pendentes,
        "subtotalPendingAccountsAmount": subtotal_contas_pendentes,
        "subtotalPendingPaymentAmount": subtotal_contas_pendentes,
        "subtotal_em_aberto": serializar_valor(grupo["subtotal_em_aberto"]),
        "quantidade_parcelas_pendentes": grupo["quantidade_parcelas_pendentes"],
        "pendingInstallmentsCount": grupo["quantidade_parcelas_pendentes"],
        "quantidade_parcelas_abertas": grupo["quantidade_parcelas_abertas"],
        "openInstallmentsCount": grupo["quantidade_parcelas_abertas"],
        "quantidade_parcelas_vencidas": grupo["quantidade_parcelas_vencidas"],
        "overdueInstallmentsCount": grupo["quantidade_parcelas_vencidas"],
        "debts": dividas,
        "dividas": dividas,
    }


def serializar_grupo_divida_financiamento(grupo_divida, *, pode_pagar_parcela=False):
    subtotal_devido = serializar_valor(grupo_divida["subtotal_devido"])
    subtotal_pago = serializar_valor(grupo_divida["subtotal_pago"])
    subtotal_contas_pendentes = serializar_valor(
        grupo_divida["subtotal_contas_pendentes"]
    )
    parcelas = [
        serializar_parcela_financiamento(
            parcela,
            pode_pagar_parcela=pode_pagar_parcela,
        )
        for parcela in grupo_divida["parcelas"]
    ]

    return {
        "divida_id": grupo_divida["divida_id"],
        "debtId": grupo_divida["divida_id"],
        "credor_id": grupo_divida["credor_id"],
        "creditorId": grupo_divida["creditorId"],
        "credor_nome": grupo_divida["credor_nome"],
        "creditorName": grupo_divida["creditorName"],
        "descricao": grupo_divida["descricao"],
        "description": grupo_divida["descricao"],
        "debtDescription": grupo_divida["descricao"],
        **serializar_dimensao_operacional(grupo_divida["divida"]),
        "subtotal_devido": subtotal_devido,
        "subtotalDueAmount": subtotal_devido,
        "subtotal_pago": subtotal_pago,
        "subtotalPaidAmount": subtotal_pago,
        "subtotal_contas_pendentes": subtotal_contas_pendentes,
        "subtotalPendingAccountsAmount": subtotal_contas_pendentes,
        "subtotalPendingPaymentAmount": subtotal_contas_pendentes,
        "subtotal_em_aberto": serializar_valor(grupo_divida["subtotal_em_aberto"]),
        "quantidade_parcelas": grupo_divida["quantidade_parcelas"],
        "installmentsCount": grupo_divida["quantidade_parcelas"],
        "quantidade_parcelas_pendentes": grupo_divida[
            "quantidade_parcelas_pendentes"
        ],
        "pendingInstallmentsCount": grupo_divida[
            "quantidade_parcelas_pendentes"
        ],
        "quantidade_parcelas_abertas": grupo_divida[
            "quantidade_parcelas_abertas"
        ],
        "openInstallmentsCount": grupo_divida[
            "quantidade_parcelas_abertas"
        ],
        "quantidade_parcelas_vencidas": grupo_divida[
            "quantidade_parcelas_vencidas"
        ],
        "overdueInstallmentsCount": grupo_divida[
            "quantidade_parcelas_vencidas"
        ],
        "installments": parcelas,
        "parcelas": parcelas,
    }
