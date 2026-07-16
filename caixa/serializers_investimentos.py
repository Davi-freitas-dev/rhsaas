from .demo_policy import demo_object_flags
from .selectors_investimentos import montar_contexto_investimentos
from .serializers_dimensoes_operacionais import (
    serializar_dimensao_operacional,
    serializar_opcoes_entidades_operacionais,
)
from .serializers_utils import (
    serializar_choices,
    serializar_choices_value_label,
    serializar_valor,
)


CAMPOS_TOTAIS_INVESTIMENTOS = (
    "total_previsto_entrada",
    "total_previsto_saida",
    "total_realizado_entrada",
    "total_realizado_saida",
    "saldo_previsto_fci",
    "saldo_realizado_fci",
    "resultado_financeiro_fci_previsto",
    "resultado_financeiro_fci_projetado",
    "resultado_financeiro_fci_realizado",
    "entradas_investimento_projetadas",
    "saidas_investimento_projetadas",
    "entradas_investimento_realizadas",
    "saidas_investimento_realizadas",
    "resultado_financeiro_investimentos_projetado",
    "resultado_financeiro_investimentos_realizado",
)


def montar_payload_investimentos_api(filtros, session):
    contexto = montar_contexto_investimentos(filtros, session)
    investimentos = [
        serializar_investimento(investimento)
        for investimento in contexto["investimentos"]
    ]
    grupos_categoria = [
        serializar_grupo_categoria_investimento(grupo)
        for grupo in contexto["grupos_categoria"]
    ]
    filtros_payload = {
        **contexto["filtros"],
        "periodo_rapido": contexto["periodo_rapido"],
    }
    opcoes_payload = serializar_opcoes_investimentos(contexto)
    totais_payload = {
        campo: serializar_valor(contexto[campo])
        for campo in CAMPOS_TOTAIS_INVESTIMENTOS
    }
    totais_payload.update({
        "plannedInflowAmount": totais_payload["total_previsto_entrada"],
        "plannedOutflowAmount": totais_payload["total_previsto_saida"],
        "realizedInflowAmount": totais_payload["total_realizado_entrada"],
        "realizedOutflowAmount": totais_payload["total_realizado_saida"],
        "projectedInflowAmount": totais_payload["entradas_investimento_projetadas"],
        "projectedOutflowAmount": totais_payload["saidas_investimento_projetadas"],
        "plannedFinancialResultAmount": totais_payload["resultado_financeiro_fci_previsto"],
        "projectedFinancialResultAmount": totais_payload[
            "resultado_financeiro_investimentos_projetado"
        ],
        "realizedFinancialResultAmount": totais_payload[
            "resultado_financeiro_investimentos_realizado"
        ],
    })

    return {
        "filters": filtros_payload,
        "filtros": filtros_payload,
        "filterOptions": opcoes_payload,
        "opcoes": opcoes_payload,
        "totals": totais_payload,
        "totais": totais_payload,
        "projectedInvestmentFlow": serializar_fluxo_investimento(
            contexto["total_previsto_entrada"],
            contexto["total_previsto_saida"],
            contexto["resultado_financeiro_fci_projetado"],
        ),
        "realizedInvestmentFlow": serializar_fluxo_investimento(
            contexto["total_realizado_entrada"],
            contexto["total_realizado_saida"],
            contexto["resultado_financeiro_fci_realizado"],
        ),
        "dateBasis": {
            "filters": "data_prevista",
            "projected": "data_prevista",
            "realized": "data_realizacao",
        },
        "investments": investimentos,
        "investimentos": investimentos,
        "categoryGroups": grupos_categoria,
        "grupos_categoria": grupos_categoria,
    }


def serializar_fluxo_investimento(entradas, saidas, resultado_financeiro):
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


def serializar_opcoes_investimentos(contexto):
    opcoes_operacionais = serializar_opcoes_entidades_operacionais(
        contexto,
        incluir_clientes=True,
    )

    return {
        "categories": serializar_choices_value_label(contexto["categorias_investimento"]),
        "categorias": serializar_choices(contexto["categorias_investimento"]),
        "flowTypes": serializar_choices_value_label(contexto["tipos_fluxo_investimento"]),
        "tipos_fluxo": serializar_choices(contexto["tipos_fluxo_investimento"]),
        "statuses": serializar_choices_value_label(contexto["status_investimento"]),
        "status": serializar_choices(contexto["status_investimento"]),
        "contracts": opcoes_operacionais["contracts"],
        "contratos": opcoes_operacionais["contracts"],
        "events": opcoes_operacionais["events"],
        "eventos": opcoes_operacionais["events"],
        "clients": opcoes_operacionais["clients"],
        "clientes": opcoes_operacionais["clients"],
    }


def serializar_investimento(investimento):
    data_prevista = serializar_valor(investimento.data_prevista)
    data_realizacao = serializar_valor(investimento.data_realizacao)
    valor_previsto = serializar_valor(investimento.valor_previsto)
    valor_realizado = serializar_valor(investimento.valor_realizado)
    valor_pendente = serializar_valor(investimento.valor_pendente_realizacao)

    return {
        "id": investimento.id,
        "date": data_prevista,
        "plannedDate": data_prevista,
        "realizedDate": data_realizacao,
        "data_prevista": data_prevista,
        "data_realizacao": data_realizacao,
        "description": investimento.descricao,
        "investmentDescription": investimento.descricao,
        "descricao": investimento.descricao,
        "category": investimento.categoria,
        "categoryLabel": investimento.get_categoria_display(),
        "categoria": investimento.categoria,
        "categoria_display": investimento.get_categoria_display(),
        "flowType": investimento.tipo_fluxo,
        "flowTypeLabel": investimento.get_tipo_fluxo_display(),
        "tipo_fluxo": investimento.tipo_fluxo,
        "tipo_fluxo_display": investimento.get_tipo_fluxo_display(),
        "plannedAmount": valor_previsto,
        "realizedAmount": valor_realizado,
        "pendingAmount": valor_pendente,
        "pendingRealizationAmount": valor_pendente,
        "valor_previsto": valor_previsto,
        "valor_realizado": valor_realizado,
        "saldo_restante": serializar_valor(investimento.saldo_restante),
        "valor_pendente_realizacao": valor_pendente,
        "status": investimento.status,
        "statusLabel": investimento.get_status_display(),
        "status_display": investimento.get_status_display(),
        "baixado_manualmente": investimento.baixado_manualmente,
        "manuallySettled": investimento.baixado_manualmente,
        "notes": investimento.observacao,
        "observacao": investimento.observacao,
        **demo_object_flags(investimento),
        **serializar_dimensao_operacional(investimento),
    }


def serializar_grupo_categoria_investimento(grupo):
    itens = [
        serializar_investimento(investimento)
        for investimento in grupo["itens"]
    ]
    subtotal_previsto_entrada = serializar_valor(
        grupo["subtotal_previsto_entrada"]
    )
    subtotal_previsto_saida = serializar_valor(
        grupo["subtotal_previsto_saida"]
    )
    subtotal_realizado_entrada = serializar_valor(
        grupo["subtotal_realizado_entrada"]
    )
    subtotal_realizado_saida = serializar_valor(
        grupo["subtotal_realizado_saida"]
    )
    subtotal_saldo_previsto = serializar_valor(
        grupo["subtotal_saldo_previsto"]
    )
    subtotal_saldo_realizado = serializar_valor(
        grupo["subtotal_saldo_realizado"]
    )
    subtotal_resultado_financeiro_previsto = serializar_valor(
        grupo["subtotal_resultado_financeiro_previsto"]
    )
    subtotal_resultado_financeiro_projetado = serializar_valor(
        grupo["subtotal_resultado_financeiro_projetado"]
    )
    subtotal_resultado_financeiro_realizado = serializar_valor(
        grupo["subtotal_resultado_financeiro_realizado"]
    )

    return {
        "categoria": grupo["categoria"],
        "category": grupo["categoria"],
        "categoria_nome": grupo["categoria_nome"],
        "categoryLabel": grupo["categoria_nome"],
        "quantidade": grupo["quantidade"],
        "quantity": grupo["quantidade"],
        "subtotal_previsto_entrada": subtotal_previsto_entrada,
        "subtotalPlannedInflowAmount": subtotal_previsto_entrada,
        "subtotal_previsto_saida": subtotal_previsto_saida,
        "subtotalPlannedOutflowAmount": subtotal_previsto_saida,
        "subtotal_realizado_entrada": subtotal_realizado_entrada,
        "subtotalRealizedInflowAmount": subtotal_realizado_entrada,
        "subtotal_realizado_saida": subtotal_realizado_saida,
        "subtotalRealizedOutflowAmount": subtotal_realizado_saida,
        "subtotal_saldo_previsto": subtotal_saldo_previsto,
        "subtotal_saldo_realizado": subtotal_saldo_realizado,
        "subtotal_resultado_financeiro_previsto": subtotal_resultado_financeiro_previsto,
        "subtotalPlannedFinancialResult": subtotal_resultado_financeiro_previsto,
        "subtotalPlannedFinancialResultAmount": subtotal_resultado_financeiro_previsto,
        "subtotal_resultado_financeiro_projetado": subtotal_resultado_financeiro_projetado,
        "subtotalProjectedFinancialResult": subtotal_resultado_financeiro_projetado,
        "subtotalProjectedFinancialResultAmount": subtotal_resultado_financeiro_projetado,
        "subtotal_resultado_financeiro_realizado": subtotal_resultado_financeiro_realizado,
        "subtotalRealizedFinancialResult": subtotal_resultado_financeiro_realizado,
        "subtotalRealizedFinancialResultAmount": subtotal_resultado_financeiro_realizado,
        "projectedInvestmentFlow": serializar_fluxo_investimento(
            grupo["subtotal_previsto_entrada"],
            grupo["subtotal_previsto_saida"],
            grupo["subtotal_resultado_financeiro_projetado"],
        ),
        "realizedInvestmentFlow": serializar_fluxo_investimento(
            grupo["subtotal_realizado_entrada"],
            grupo["subtotal_realizado_saida"],
            grupo["subtotal_resultado_financeiro_realizado"],
        ),
        "items": itens,
        "itens": itens,
    }
