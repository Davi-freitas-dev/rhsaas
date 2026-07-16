import csv
import json
from io import StringIO
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils import timezone

from .contracts_obrigacoes import serializar_contrato_baixa_obrigacoes_usuario
from .constants_nomenclatura import montar_metadados_nomenclatura_financeira
from .models import Cliente, Evento
from .selectors_opcoes_filtros import montar_opcoes_eventos_clientes_filtro
from .selectors_obrigacoes import (
    FONTES_OBRIGACOES,
    RECONCILIACAO_DIAGNOSTICOS,
    RECONCILIACAO_ORIENTACOES,
    STATUS_VENCIDO,
    listar_obrigacoes_financeiras,
    montar_overview_obrigacoes_financeiras,
    resumir_obrigacoes_financeiras,
)
from .selectors_obrigacoes_canonicas import (
    contar_obrigacoes_financeiras_canonicas,
    listar_obrigacoes_financeiras_canonicas,
)
from .services_modelagem_canonica import (
    verificar_paridade_modelagem_financeira_canonica,
)
from .services_posicao_caixa import montar_posicao_caixa_periodo
from .utils_contratos import normalizar_codigo_contrato_visual
from .utils_financeiros import quantizar_moeda
from .utils_periodos import resolver_intervalo_periodo_canonico
from .serializers_dimensoes_operacionais import (
    serializar_cliente_operacional_opcao,
    serializar_dimensao_operacional,
    serializar_opcoes_entidades_operacionais,
)


LIMITE_PADRAO = 100
LIMITE_MAXIMO = 300
PAYMENT_QUEUE_CONTRACT_VERSION = "financial-payments-queue-v1"
PAYMENT_QUEUE_PERMISSION_SCOPE = "payments"
OVERDUE_SCOPE_ALL = "all"
PAYMENT_QUEUE_URGENCY_ORDER = ("overdue", "today", "next7", "later")
PAYMENT_QUEUE_FILTERS = {"all", "overdue", "next7", "blocked"}
PAYMENT_QUEUE_URGENCY_LABELS = {
    "overdue": "Vencido",
    "today": "Hoje",
    "next7": "Proximos 7 dias",
    "later": "Depois de 7 dias",
}
PAYMENT_QUEUE_BLOCK_REASON_LABELS = {
    "native_settlement_unavailable": "Origem sem baixa nativa",
    "unsupported_obligation_type": "Tipo nao suportado",
    "missing_source_detail": "Detalhe de origem ausente",
    "no_pending_amount": "Sem pendencia",
    "settled": "Pago",
    "cancelled": "Cancelado",
    "demo_seed_read_only": "Dado de exemplo somente leitura",
}
PAYMENT_QUEUE_CAPABILITY_FIELDS = (
    ("supportsPaymentMethod", "Aceita forma de pagamento"),
    ("supportsPaymentDescription", "Aceita descricao de pagamento"),
    ("supportsAdjustments", "Aceita ajustes"),
    ("supportsWriteOff", "Aceita baixa de saldo"),
)
PAYMENT_QUEUE_READINESS_RULES = (
    {
        "key": "native_settlement_available",
        "label": "Origem possui baixa nativa e o usuario pode executar a baixa.",
        "blockedReason": "native_settlement_unavailable",
    },
    {
        "key": "supported_obligation_type",
        "label": "Origem aceita obrigacao do tipo pagar.",
        "blockedReason": "unsupported_obligation_type",
    },
    {
        "key": "source_detail_present",
        "label": "Detalhe de origem esta presente quando a origem exige detalhe.",
        "blockedReason": "missing_source_detail",
    },
    {
        "key": "has_pending_amount",
        "label": "Obrigacao possui pendencia de origem maior que zero.",
        "blockedReason": "no_pending_amount",
    },
    {
        "key": "not_settled_or_cancelled",
        "label": "Obrigacao nao esta liquidada nem cancelada.",
        "blockedReason": "settled|cancelled",
    },
)
EXPORT_SCOPES_OBRIGACOES = {
    "obligations",
    "revenues",
    "expenses",
    "payments",
}
OPCOES_FLUXO_CAIXA_OBRIGACOES = (
    {"value": "fco", "label": "FCO"},
    {"value": "fci", "label": "FCI"},
    {"value": "fcf", "label": "FCF"},
)
OPCOES_STATUS_LIQUIDACAO_OBRIGACOES = (
    {"value": "pendente", "label": "Pendente"},
    {"value": "parcial", "label": "Parcial"},
    {"value": "vencido", "label": "Vencido"},
    {"value": "liquidado", "label": "Liquidado"},
    {"value": "cancelado", "label": "Cancelado"},
)
STATUS_LIQUIDACAO_OBRIGACOES = {
    opcao["value"] for opcao in OPCOES_STATUS_LIQUIDACAO_OBRIGACOES
}
OPCOES_STATUS_CONCILIACAO_OBRIGACOES = (
    {"value": "conciliado", "label": "Conciliado"},
    {"value": "divergente", "label": "Divergente"},
)
OPCOES_BASE_REALIZADO_OBRIGACOES = (
    {"value": "originState", "label": "Estado da origem"},
    {"value": "ledger", "label": "Lançamento financeiro"},
)
OPCOES_EXCEDENTE_REALIZADO_OBRIGACOES = (
    {"value": "with", "label": "Com realizado acima do previsto"},
    {"value": "without", "label": "Sem realizado acima do previsto"},
)
OPCOES_TIPO_OBRIGACAO = (
    {"value": "pagar", "label": "A pagar"},
    {"value": "receber", "label": "A receber"},
)
OPCOES_FONTE_DADOS_OBRIGACOES = (
    {"value": "legacy", "label": "Origem/ledger legado"},
    {"value": "canonical", "label": "Modelagem canônica com leitura legada segura"},
)
ROTULOS_FONTE_LEITURA_OBRIGACOES = {
    "canonical": "Modelagem canônica",
    "legacy": "Origem/ledger legado",
}
DETALHES_LEITURA_LEGADA_CANONICA_OBRIGACOES = {
    "missing_canonical_records": "modelagem canônica incompleta",
    "divergent_canonical_records": "modelagem canônica divergente",
    "extra_canonical_records": "registros canônicos extras",
    "legacy_reconciliation_divergent": "conciliação origem/ledger divergente",
    "canonical_parity_not_ready": "paridade canônica pendente",
}

ADMIN_MODELS_OBRIGACOES = {
    "receita_operacional": "receitaoperacional",
    "despesa_operacional": "despesaoperacional",
    "custo_fixo": "custofixo",
    "custo_servico": "eventocustoservico",
    "custo_extra": "eventocustoextra",
    "parcela_divida": "parceladivida",
    "investimento": "investimento",
    "financiamento_movimentacao": "financiamentomovimentacao",
}
PERMISSOES_ACAO_PAGAMENTO_OBRIGACOES = {
    "custo_servico": "caixa.add_pagamentoeventocustoservico",
    "custo_extra": "caixa.add_pagamentoeventocustoextra",
    "parcela_divida": "caixa.add_pagamentoparceladivida",
}


def montar_payload_obrigacoes_financeiras_api(params, usuario=None):
    filtros = normalizar_filtros_obrigacoes(params)
    itens, fonte_dados = listar_obrigacoes_com_fonte(filtros)
    status_leitura = serializar_read_model_status_obrigacoes(fonte_dados)
    total_registros = len(itens)
    limit = normalizar_inteiro(filtros.get("limit"), LIMITE_PADRAO, 1, LIMITE_MAXIMO)
    offset = normalizar_inteiro(filtros.get("offset"), 0, 0, total_registros)
    itens_paginados = itens[offset:offset + limit]
    contrato_baixa = serializar_contrato_baixa_obrigacoes_usuario(usuario)
    resumo = resumir_obrigacoes_financeiras(itens)
    overview = montar_overview_obrigacoes_financeiras(itens, filtros)
    permissoes_action_hints = permissoes_action_hints_obrigacoes(usuario)
    payment_queue = montar_payment_queue_obrigacoes(
        itens,
        filtros,
        contrato_baixa,
    )

    data = {
        "items": [
            serializar_obrigacao_financeira(
                item,
                permissoes_action_hints=permissoes_action_hints,
            )
            for item in itens_paginados
        ],
        "summary": serializar_resumo_obrigacoes(resumo, overview=overview),
        "cashAvailability": serializar_disponibilidade_caixa_obrigacoes(
            filtros,
            resumo,
        ),
        "filters": serializar_filtros_obrigacoes(filtros),
        "filterOptions": serializar_opcoes_obrigacoes(filtros),
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total_registros,
            "hasMore": offset + limit < total_registros,
        },
        "meta": {
            "generatedAt": timezone.now().isoformat(),
            "source": "backend",
            "currency": "BRL",
            "dateBasis": "dueDate",
            "realizedAmountBasis": filtros.get("realizedAmountBasis") or "originState",
            "availableRealizedAmountBases": ["originState", "ledger"],
            "ledgerReconciliation": "itemLevel",
            "settlementCapabilities": contrato_baixa,
            "availableObligationTypes": ["pagar", "receber"],
            "obligationTypeScope": [filtros.get("obligationType") or "pagar"],
            "dataSourceRequested": fonte_dados["requested"],
            "dataSourceActual": fonte_dados["actual"],
            "canonicalFallbackReason": status_leitura["reason"],
            "readModelStatusReason": status_leitura["reason"],
            "readModelStatusLabel": status_leitura["label"],
            "readModelStatusDetail": status_leitura["detail"],
            "readModelStatusTone": status_leitura["tone"],
            "readModelStatus": status_leitura,
            "readModelStatusDiagnostics": status_leitura["diagnostics"],
            "canonicalReadiness": fonte_dados["canonicalReadiness"],
            "nomenclature": montar_metadados_nomenclatura_financeira(),
            "amountSemantics": serializar_semantica_valores_obrigacoes(
                filtros,
                fonte_dados,
                status_leitura,
            ),
            "filterSemantics": serializar_semantica_filtros_obrigacoes(filtros),
        },
    }
    if payment_queue is not None:
        data["paymentQueue"] = payment_queue

    return {"data": data}


def serializar_semantica_valores_obrigacoes(filtros, fonte_dados, status_leitura):
    realized_amount_basis = filtros.get("realizedAmountBasis") or "originState"
    return {
        "version": "financial-obligations-amount-semantics-v1",
        "scope": "financialObligations",
        "currency": "BRL",
        "dateBasis": "dueDate",
        "realizedAmountBasis": realized_amount_basis,
        "readModel": {
            "dataSourceRequested": fonte_dados["requested"],
            "dataSourceActual": fonte_dados["actual"],
            "canonicalReady": status_leitura["canonicalReady"],
            "fallbackReason": status_leitura["reason"],
        },
        "fields": {
            "plannedAmount": {
                "businessTerm": "Valor previsto",
                "meaning": (
                    "Valor projetado ou contratado da obrigacao financeira antes "
                    "das baixas."
                ),
            },
            "realizedAmount": {
                "businessTerm": "Valor realizado",
                "meaning": (
                    "Valor efetivamente realizado conforme a base selecionada em "
                    "realizedAmountBasis."
                ),
                "basisField": "realizedAmountBasis",
            },
            "originRealizedAmount": {
                "businessTerm": "Realizado origem",
                "meaning": "Valor realizado no proprio registro de origem.",
            },
            "ledgerRealizedAmount": {
                "businessTerm": "Realizado ledger",
                "meaning": "Valor realizado pelos lancamentos financeiros conciliados.",
            },
            "realizedAmountDifference": {
                "businessTerm": "Diferenca realizada",
                "meaning": (
                    "Diferenca entre realizado de origem e realizado do ledger para "
                    "auditoria."
                ),
            },
            "pendingAmount": {
                "businessTerm": "Contas pendentes",
                "meaning": (
                    "Parte do valor previsto que ainda nao foi liquidada, sem gerar "
                    "valor negativo quando houver pagamento acima do previsto."
                ),
            },
            "pendingPaymentAmount": {
                "businessTerm": "Valor pendente de pagamento",
                "meaning": "Mesmo valor de pendingAmount quando a obrigacao e a pagar.",
            },
            "pendingReceivableAmount": {
                "businessTerm": "Valor pendente de recebimento",
                "meaning": "Mesmo valor de pendingAmount quando a obrigacao e a receber.",
            },
            "overRealizedAmount": {
                "businessTerm": "Acima do previsto",
                "meaning": (
                    "Valor realizado acima do previsto, separado de pendingAmount para "
                    "nao criar contas pendentes negativas."
                ),
            },
            "availableCashAmount": {
                "businessTerm": "Caixa do periodo",
                "meaning": (
                    "Caixa final disponivel do periodo filtrado: saldo inicial "
                    "+ entradas efetivamente recebidas - saidas efetivamente pagas."
                ),
                "dateBasis": "data_lancamento efetiva dentro do periodo",
                "formula": "initialCashAmount + realizedInflowAmount - realizedOutflowAmount",
            },
            "finalCashAmount": {
                "businessTerm": "Caixa final do periodo",
                "meaning": (
                    "Mesmo conceito de availableCashAmount quando o rotulo "
                    "visual for Caixa disponivel."
                ),
                "formula": "initialCashAmount + realizedInflowAmount - realizedOutflowAmount",
            },
            "currentAvailableCashAmount": {
                "businessTerm": "Caixa disponivel atual",
                "meaning": (
                    "Caixa efetivo disponivel ate hoje, independente do periodo "
                    "filtrado na tela."
                ),
                "dateBasis": "data_recebimento/data_pagamento ate hoje",
                "formula": (
                    "accumulatedEffectiveInflowsUntilToday "
                    "- accumulatedEffectiveOutflowsUntilToday"
                ),
            },
            "accumulatedCashUntilDate": {
                "businessTerm": "Caixa acumulado ate a data",
                "meaning": (
                    "Saldo acumulado efetivo ate a data final do filtro, "
                    "preservado para validacoes e diagnostico."
                ),
                "dateBasis": "data_recebimento/data_pagamento",
                "formula": "accumulatedEffectiveInflowsUntilDate - accumulatedEffectiveOutflowsUntilDate",
            },
            "pendingPayablesAmount": {
                "businessTerm": "Contas a pagar pendentes",
                "meaning": "Contas a pagar ainda não liquidadas no escopo da tela.",
            },
            "cashCoverageAfterPendingAmount": {
                "businessTerm": "Cobertura de caixa apos pendencias",
                "meaning": (
                    "Caixa disponivel do periodo menos contas a pagar pendentes "
                    "no escopo da tela."
                ),
                "formula": "finalCashAmount - pendingPayablesAmount",
            },
            "availableAfterPendingAmount": {
                "businessTerm": "Caixa após pendências",
                "meaning": (
                    "Caixa disponível menos contas a pagar pendentes no escopo "
                    "da tela."
                ),
                "formula": "finalCashAmount - pendingPayablesAmount",
            },
            "cashCoverageDeficitAmount": {
                "businessTerm": "Déficit de cobertura",
                "meaning": (
                    "Valor que falta para cobrir as contas a pagar pendentes com "
                    "o caixa disponível."
                ),
            },
            "settlementStatus": {
                "businessTerm": "Status de liquidacao",
                "meaning": (
                    "Situacao da obrigacao: pendente, parcial, vencido, liquidado "
                    "ou cancelado."
                ),
            },
            "reconciliationDiagnosis": {
                "businessTerm": "Diagnostico de conciliacao",
                "meaning": "Diagnostico entre origem e ledger usado para auditoria operacional.",
            },
            "obligationType": {
                "businessTerm": "Tipo da obrigacao",
                "meaning": "Define se a obrigacao representa conta a pagar ou conta a receber.",
            },
            "cashFlowGroup": {
                "businessTerm": "Grupo de fluxo de caixa",
                "meaning": "Classificacao financeira FCO, FCI ou FCF.",
            },
            "readModelStatus": {
                "businessTerm": "Status da fonte de leitura",
                "meaning": "Informa se a API leu da modelagem canonica ou do legado seguro.",
            },
        },
        "aliases": {
            "valor_previsto": "plannedAmount",
            "valor_realizado": "realizedAmount",
            "valor_pago": "realizedAmount",
            "contas_pendentes": "pendingAmount",
            "valor_pendente_pagamento": "pendingPaymentAmount",
            "valor_realizado_origem": "originRealizedAmount",
            "valor_realizado_ledger": "ledgerRealizedAmount",
            "valor_excedente_realizado": "overRealizedAmount",
            "caixaDisponivel": "availableCashAmount",
            "contasAPagarPendentes": "pendingPayablesAmount",
            "caixaAposPendencias": "availableAfterPendingAmount",
            "deficitCobertura": "cashCoverageDeficitAmount",
            "tipo_obrigacao": "obligationType",
            "fluxo": "cashFlowGroup",
            "diagnosticoConciliacao": "reconciliationDiagnosis",
        },
    }


def serializar_semantica_filtros_obrigacoes(filtros):
    return {
        "version": "financial-obligations-filter-semantics-v1",
        "scope": "financialObligations",
        "combinationRule": "intersection",
        "combinationMeaning": (
            "Todos os filtros ativos sao combinados por E logico; o resultado "
            "deve atender ao periodo, status, origem, contrato, evento, cliente "
            "e demais filtros informados."
        ),
        "dateBasis": "dueDate",
        "dateRange": {
            "startDate": filtros.get("startDate") or "",
            "endDate": filtros.get("endDate") or "",
            "inclusive": True,
        },
        "activeFilters": serializar_filtros_ativos_semantica_obrigacoes(filtros),
        "fields": {
            "startDate": {
                "businessTerm": "Data inicial",
                "meaning": "Inicio inclusivo da janela de vencimento.",
                "dateBasis": "dueDate",
            },
            "endDate": {
                "businessTerm": "Data final",
                "meaning": "Fim inclusivo da janela de vencimento.",
                "dateBasis": "dueDate",
            },
            "settlementStatus": {
                "businessTerm": "Status de liquidacao",
                "meaning": (
                    "Filtra pela situacao da obrigacao dentro da janela de data "
                    "quando periodo tambem estiver ativo."
                ),
            },
            "overdueScope": {
                "businessTerm": "Escopo de vencidas",
                "meaning": (
                    "Quando informado como all, lista vencidas ate hoje ignorando "
                    "periodo e preservando filtros operacionais."
                ),
            },
            "obligationType": {
                "businessTerm": "Tipo da obrigacao",
                "meaning": (
                    "Define se a consulta retorna contas a pagar ou contas a "
                    "receber e tambem controla as origens disponiveis."
                ),
            },
            "source": {
                "businessTerm": "Origem da obrigacao",
                "meaning": "Filtra pelo model de origem financeira da obrigacao.",
            },
            "contractCode": {
                "businessTerm": "Contrato",
                "meaning": (
                    "Filtra obrigacoes pelo numero visual do contrato/orcamento "
                    "associado ao evento."
                ),
            },
            "eventId": {
                "businessTerm": "Evento",
                "meaning": "Filtra obrigacoes vinculadas a um evento especifico.",
            },
            "clientId": {
                "businessTerm": "Cliente",
                "meaning": "Filtra obrigacoes vinculadas a um cliente especifico.",
            },
            "cashFlowGroup": {
                "businessTerm": "Grupo de fluxo de caixa",
                "meaning": "Filtra por FCO, FCI ou FCF.",
            },
            "reconciliationStatus": {
                "businessTerm": "Status de conciliacao",
                "meaning": "Filtra se origem e ledger estao conciliados ou divergentes.",
            },
            "reconciliationDiagnosis": {
                "businessTerm": "Diagnostico de conciliacao",
                "meaning": "Filtra pelo tipo de divergencia entre origem e ledger.",
            },
            "realizedAbovePlanned": {
                "businessTerm": "Realizado acima do previsto",
                "meaning": (
                    "Filtra obrigacoes em que o valor realizado ultrapassou o valor "
                    "previsto, separando excedente de contas pendentes."
                ),
            },
            "search": {
                "businessTerm": "Busca textual",
                "meaning": "Filtra por contrato, evento, cliente ou descricao da obrigacao.",
            },
            "realizedAmountBasis": {
                "businessTerm": "Base do valor realizado",
                "meaning": (
                    "Define se os valores realizados usam estado da origem ou "
                    "ledger; nao muda a janela de data."
                ),
            },
            "dataSource": {
                "businessTerm": "Fonte de leitura",
                "meaning": (
                    "Solicita leitura pela modelagem canonica ou pelo legado "
                    "seguro; a fonte efetiva aparece em meta.dataSourceActual."
                ),
            },
        },
        "rules": {
            "periodAndSettlementStatusAreCombined": True,
            "overdueWithPeriodMeansOverdueInsidePeriod": True,
            "overdueScopeAllIgnoresPeriod": filtros.get("overdueScope") == OVERDUE_SCOPE_ALL,
            "overdueScopeAllKeepsOperationalFilters": filtros.get("overdueScope") == OVERDUE_SCOPE_ALL,
            "dateRangeIsInclusive": True,
            "obligationTypeControlsAvailableSources": True,
        },
        "aliases": {
            "data_inicial": "startDate",
            "data_final": "endDate",
            "situacao": "settlementStatus",
            "status": "settlementStatus",
            "overdue_scope": "overdueScope",
            "origem": "source",
            "fluxo": "cashFlowGroup",
            "tipo_obrigacao": "obligationType",
            "fonteDados": "dataSource",
            "baseRealizado": "realizedAmountBasis",
            "statusConciliacao": "reconciliationStatus",
            "diagnosticoConciliacao": "reconciliationDiagnosis",
            "overRealized": "realizedAbovePlanned",
            "over_realized": "realizedAbovePlanned",
            "excedenteRealizado": "realizedAbovePlanned",
            "excedente_realizado": "realizedAbovePlanned",
            "busca": "search",
        },
    }


def serializar_filtros_ativos_semantica_obrigacoes(filtros):
    campos = (
        "startDate",
        "endDate",
        "contractCode",
        "eventId",
        "clientId",
        "source",
        "cashFlowGroup",
        "nature",
        "overdueScope",
        "settlementStatus",
        "reconciliationStatus",
        "reconciliationDiagnosis",
        "realizedAmountBasis",
        "realizedAbovePlanned",
        "dataSource",
        "obligationType",
        "search",
    )
    ativos = []
    for campo in campos:
        valor = filtros.get(campo)
        if valor not in (None, ""):
            ativos.append({"field": campo, "value": valor})
    return ativos


def listar_obrigacoes_com_fonte(filtros):
    fonte_requisitada = filtros.get("dataSource") or "canonical"
    if fonte_requisitada != "canonical":
        return listar_obrigacoes_financeiras(filtros), {
            "requested": "legacy",
            "actual": "legacy",
            "legacyReadReason": "",
            "canonicalReadiness": None,
        }

    prontidao = avaliar_prontidao_canonica_obrigacoes(filtros)
    if prontidao["readyForCanonicalReads"]:
        return listar_obrigacoes_financeiras_canonicas(filtros), {
            "requested": "canonical",
            "actual": "canonical",
            "legacyReadReason": "",
            "canonicalReadiness": prontidao,
        }

    return listar_obrigacoes_financeiras(filtros), {
        "requested": "canonical",
        "actual": "legacy",
        "legacyReadReason": prontidao["reason"],
        "canonicalReadiness": prontidao,
    }


def listar_obrigacoes_com_fonte_leitura_visual(filtros):
    fonte_requisitada = filtros.get("dataSource") or "canonical"
    if fonte_requisitada != "canonical":
        return listar_obrigacoes_financeiras(filtros), {
            "requested": "legacy",
            "actual": "legacy",
            "legacyReadReason": "",
            "canonicalReadiness": None,
        }

    prontidao = avaliar_prontidao_canonica_visual_obrigacoes(filtros)
    if prontidao["readyForCanonicalReads"]:
        return listar_obrigacoes_financeiras_canonicas(filtros), {
            "requested": "canonical",
            "actual": "canonical",
            "legacyReadReason": "",
            "canonicalReadiness": prontidao,
        }

    return listar_obrigacoes_financeiras(filtros), {
        "requested": "canonical",
        "actual": "legacy",
        "legacyReadReason": prontidao["reason"],
        "canonicalReadiness": prontidao,
    }


def serializar_status_fonte_leitura_obrigacoes(fonte_dados):
    requested = fonte_dados.get("requested") or "legacy"
    actual = fonte_dados.get("actual") or requested
    legacy_read_reason = obter_motivo_leitura_legada(fonte_dados)

    if requested == "canonical" and actual == "legacy":
        detalhe = DETALHES_LEITURA_LEGADA_CANONICA_OBRIGACOES.get(
            legacy_read_reason,
            legacy_read_reason,
        )
        return {
            "readModelStatusLabel": "Leitura legada",
            "readModelStatusDetail": detalhe,
            "readModelStatusTone": "warning",
        }

    return {
        "readModelStatusLabel": f"Leitura: {ROTULOS_FONTE_LEITURA_OBRIGACOES.get(actual, actual)}",
        "readModelStatusDetail": "",
        "readModelStatusTone": "neutral",
    }


def serializar_read_model_status_obrigacoes(fonte_dados):
    status = serializar_status_fonte_leitura_obrigacoes(fonte_dados)
    diagnostico = serializar_diagnostico_fonte_leitura_obrigacoes(fonte_dados)

    return {
        "label": status["readModelStatusLabel"],
        "detail": status["readModelStatusDetail"],
        "tone": status["readModelStatusTone"],
        "reason": diagnostico["legacyReadReason"],
        "requested": diagnostico["requested"],
        "actual": diagnostico["actual"],
        "dataSourceRequested": diagnostico["requested"],
        "dataSourceActual": diagnostico["actual"],
        "canonicalReady": diagnostico["canonicalReady"],
        "expected": diagnostico["expected"],
        "existing": diagnostico["existing"],
        "missing": diagnostico["missing"],
        "divergent": diagnostico["divergent"],
        "extra": diagnostico["extra"],
        "diagnostics": diagnostico,
    }


def obter_motivo_leitura_legada(fonte_dados):
    return fonte_dados.get("legacyReadReason") or fonte_dados.get("fallbackReason") or ""


def serializar_diagnostico_fonte_leitura_obrigacoes(fonte_dados):
    prontidao = fonte_dados.get("canonicalReadiness") or {}
    totais = prontidao.get("totals") or {}
    legacy_read_reason = obter_motivo_leitura_legada(fonte_dados)

    return {
        "requested": fonte_dados.get("requested") or "",
        "actual": fonte_dados.get("actual") or "",
        "legacyReadReason": legacy_read_reason,
        "fallbackReason": legacy_read_reason,
        "canonicalReady": bool(prontidao.get("readyForCanonicalReads")),
        "expected": totais.get("expected", 0),
        "existing": totais.get("existing", 0),
        "missing": totais.get("missing", 0),
        "divergent": totais.get("divergent", 0),
        "extra": totais.get("extra", 0),
    }


def resumir_status_leitura_obrigacoes_meta(meta):
    diagnostico = meta.get("readModelStatusDiagnostics") or {}
    status = meta.get("readModelStatus") or {}
    if status:
        return {
            "label": status.get("label", ""),
            "detail": status.get("detail", ""),
            "tone": status.get("tone", "neutral"),
            "reason": status.get("reason", ""),
            "dataSourceRequested": (
                status.get("dataSourceRequested") or status.get("requested") or ""
            ),
            "dataSourceActual": (
                status.get("dataSourceActual") or status.get("actual") or ""
            ),
            "canonicalReady": bool(status.get("canonicalReady")),
            "expected": status.get("expected", diagnostico.get("expected", 0)),
            "existing": status.get("existing", diagnostico.get("existing", 0)),
            "missing": status.get("missing", diagnostico.get("missing", 0)),
            "divergent": status.get("divergent", diagnostico.get("divergent", 0)),
            "extra": status.get("extra", diagnostico.get("extra", 0)),
        }

    return {
        "label": meta.get("readModelStatusLabel", ""),
        "detail": meta.get("readModelStatusDetail", ""),
        "tone": meta.get("readModelStatusTone", "neutral"),
        "reason": meta.get("readModelStatusReason", ""),
        "dataSourceRequested": meta.get("dataSourceRequested", ""),
        "dataSourceActual": meta.get("dataSourceActual", ""),
        "canonicalReady": bool(diagnostico.get("canonicalReady")),
        "expected": diagnostico.get("expected", 0),
        "existing": diagnostico.get("existing", 0),
        "missing": diagnostico.get("missing", 0),
        "divergent": diagnostico.get("divergent", 0),
        "extra": diagnostico.get("extra", 0),
    }


def formatar_status_leitura_obrigacoes(status):
    detalhe = f": {status['detail']}" if status.get("detail") else ""
    return (
        "Leitura de obrigacoes: "
        f"{status.get('label', '')}{detalhe}; "
        f"solicitada={status.get('dataSourceRequested', '')}; "
        f"efetiva={status.get('dataSourceActual', '')}; "
        f"canonicaPronta={'sim' if status.get('canonicalReady') else 'nao'}"
    )


def normalizar_filtros_obrigacoes(params):
    params = dict(params.items()) if hasattr(params, "items") else dict(params or {})
    periodo = resolver_intervalo_periodo_canonico(params)
    overdue_scope = normalizar_overdue_scope(params.get("overdueScope"))
    if overdue_scope == OVERDUE_SCOPE_ALL:
        periodo = {
            **periodo,
            "period": "",
            "quickPeriod": "",
            "startDate": "",
            "endDate": "",
        }

    filtros = {
        "period": periodo["period"],
        "quickPeriod": periodo["quickPeriod"],
        "startDate": periodo["startDate"],
        "data_inicial": periodo["startDate"],
        "endDate": periodo["endDate"],
        "data_final": periodo["endDate"],
        "limit": params.get("limit"),
        "offset": params.get("offset"),
        "queueLimit": params.get("queueLimit"),
        "queueOffset": params.get("queueOffset"),
        "permissionScope": params.get("permissionScope") or "",
        "overdueScope": overdue_scope,
        "queueFilter": normalizar_payment_queue_filter(params.get("queueFilter")),
    }
    filtros["contractCode"] = normalizar_codigo_contrato_visual(params.get("contractCode"))
    filtros["contrato_codigo"] = filtros["contractCode"]
    filtros["eventId"] = normalizar_id(params.get("eventId"))
    filtros["clientId"] = normalizar_id(params.get("clientId"))
    filtros["reconciliationStatus"] = normalizar_reconciliation_status(
        params.get("reconciliationStatus")
    )
    filtros["realizedAmountBasis"] = normalizar_realized_amount_basis(
        params.get("realizedAmountBasis")
    )
    filtros["reconciliationDiagnosis"] = normalizar_reconciliation_diagnosis(
        params.get("reconciliationDiagnosis")
    )
    filtros["realizedAbovePlanned"] = normalizar_realized_above_planned_filter(
        params.get("realizedAbovePlanned")
    )
    filtros["dataSource"] = normalizar_data_source_obrigacoes(
        params.get("dataSource")
    )
    filtros["obligationType"] = normalizar_tipo_obrigacao(
        params.get("obligationType")
    ) or "pagar"
    source = normalizar_source_obrigacoes(params.get("source"))
    sources = normalizar_sources_obrigacoes(params.get("sources"))
    if source:
        sources = [source]
    filtros["source"] = source
    filtros["origin"] = source
    filtros["origem"] = source
    filtros["sources"] = sources
    filtros["cashFlowGroup"] = params.get("cashFlowGroup") or ""
    filtros["fluxo"] = filtros["cashFlowGroup"]
    filtros["nature"] = params.get("nature") or ""
    filtros["natureza"] = filtros["nature"]
    filtros["search"] = params.get("search") or ""
    filtros["busca"] = filtros["search"]
    filtros["tipoObrigacao"] = filtros["obligationType"]
    filtros["tipo_obrigacao"] = filtros["obligationType"]
    if overdue_scope == OVERDUE_SCOPE_ALL:
        status_liquidacao = STATUS_VENCIDO
    else:
        status_liquidacao = normalizar_status_liquidacao_obrigacao(
            params.get("settlementStatus") or params.get("status"),
            filtros["obligationType"],
        )
    filtros["status"] = status_liquidacao
    filtros["settlementStatus"] = status_liquidacao
    filtros["settlement_status"] = status_liquidacao
    filtros["situacao"] = status_liquidacao
    return filtros


def normalizar_overdue_scope(valor):
    valor = str(valor or "").strip()
    return OVERDUE_SCOPE_ALL if valor == OVERDUE_SCOPE_ALL else ""


def normalizar_payment_queue_filter(valor):
    valor = str(valor or "all").strip()
    if valor == "overdueAll":
        return "overdue"
    return valor if valor in PAYMENT_QUEUE_FILTERS else "all"


def normalizar_source_obrigacoes(valor):
    valor = str(valor or "").strip()
    return valor if valor in FONTES_OBRIGACOES else ""


def normalizar_sources_obrigacoes(valor):
    if isinstance(valor, (list, tuple, set)):
        candidatos = valor
    else:
        candidatos = str(valor or "").replace(";", ",").split(",")

    sources = []
    for candidato in candidatos:
        source = normalizar_source_obrigacoes(candidato)
        if source and source not in sources:
            sources.append(source)
    return sources


def serializar_obrigacao_financeira(item, *, permissoes_action_hints=None):
    due_date = serializar_data(item["due_date"])
    payment_date = serializar_data(item["payment_date"])
    obligation_type = item.get("obligation_type", "pagar")
    pending_amount = decimal_para_numero(item["pending_amount"])
    origin_realized = item.get("origin_realized_amount", item["realized_amount"])
    origin_pending = item.get("origin_pending_amount", item["pending_amount"])
    origin_over_realized = item.get(
        "origin_over_realized_amount",
        item.get("over_realized_amount", 0),
    )
    orientacao_conciliacao = serializar_orientacao_conciliacao(
        item.get("reconciliation_diagnosis")
    )

    return {
        "id": item["id"],
        "obligationType": obligation_type,
        "tipoObrigacao": obligation_type,
        "tipo_obrigacao": obligation_type,
        "source": item["source"],
        "origin": item["source"],
        "origem": item["source"],
        "sourceId": item["source_id"],
        "originId": item["source_id"],
        "sourceLabel": item["source_label"],
        "sourceDetail": item["source_detail"],
        "sourceDetailLabel": item["source_detail_label"],
        "description": item["description"],
        "obligationDescription": item["description"],
        "descricao": item["description"],
        "reference": item["reference"],
        "referencia": item["reference"],
        "dueDate": due_date,
        "date": due_date,
        "data": due_date,
        "data_vencimento": due_date,
        "paymentDate": payment_date,
        "data_pagamento": payment_date,
        "plannedAmount": decimal_para_numero(item["planned_amount"]),
        "valor_previsto": decimal_para_numero(item["planned_amount"]),
        "realizedAmount": decimal_para_numero(item["realized_amount"]),
        "paidAmount": decimal_para_numero(item["realized_amount"]),
        "valor_realizado": decimal_para_numero(item["realized_amount"]),
        "valor_pago": decimal_para_numero(item["realized_amount"]),
        "overRealizedAmount": decimal_para_numero(item.get("over_realized_amount", 0)),
        "realizedAbovePlannedAmount": decimal_para_numero(
            item.get("over_realized_amount", 0)
        ),
        "excedenteRealizado": decimal_para_numero(item.get("over_realized_amount", 0)),
        "valor_excedente_realizado": decimal_para_numero(
            item.get("over_realized_amount", 0)
        ),
        "realizedAmountSource": item.get("realized_amount_source", "origin"),
        "originRealizedAmount": decimal_para_numero(origin_realized),
        "originPendingAmount": decimal_para_numero(origin_pending),
        "originOverRealizedAmount": decimal_para_numero(origin_over_realized),
        "ledgerRealizedAmount": decimal_para_numero(item.get("ledger_realized_amount", 0)),
        "ledgerPendingAmount": decimal_para_numero(item.get("ledger_pending_amount", 0)),
        "ledgerOverRealizedAmount": decimal_para_numero(
            item.get("ledger_over_realized_amount", 0)
        ),
        "ledgerSettlementStatus": item.get("ledger_settlement_status", ""),
        "ledgerSettlementStatusLabel": item.get("ledger_settlement_status_label", ""),
        "ledgerIsOverdue": item.get("ledger_is_overdue", False),
        "ledgerDaysOverdue": item.get("ledger_days_overdue", 0),
        "ledgerEntryCount": item.get("ledger_entry_count", 0),
        "realizedAmountDifference": decimal_para_numero(
            item.get("realized_amount_difference", 0)
        ),
        "isLedgerReconciled": item.get("is_ledger_reconciled", True),
        "reconciliationStatus": item.get("reconciliation_status", "conciliado"),
        "reconciliationDiagnosis": item.get("reconciliation_diagnosis", "conciliado"),
        "reconciliationDiagnosisLabel": item.get(
            "reconciliation_diagnosis_label",
            "Origem e ledger conciliados",
        ),
        "diagnosticoConciliacao": item.get("reconciliation_diagnosis", "conciliado"),
        "diagnosticoConciliacaoLabel": item.get(
            "reconciliation_diagnosis_label",
            "Origem e ledger conciliados",
        ),
        "reconciliationGuidance": orientacao_conciliacao,
        "orientacaoConciliacao": orientacao_conciliacao,
        "valor_realizado_origem": decimal_para_numero(origin_realized),
        "valor_pendente_origem": decimal_para_numero(origin_pending),
        "valor_excedente_origem": decimal_para_numero(origin_over_realized),
        "valor_realizado_ledger": decimal_para_numero(item.get("ledger_realized_amount", 0)),
        "valor_pendente_ledger": decimal_para_numero(item.get("ledger_pending_amount", 0)),
        "valor_excedente_ledger": decimal_para_numero(
            item.get("ledger_over_realized_amount", 0)
        ),
        "diferenca_realizado_ledger": decimal_para_numero(
            item.get("realized_amount_difference", 0)
        ),
        "conciliado_ledger": item.get("is_ledger_reconciled", True),
        "pendingAmount": pending_amount,
        "pendingPaymentAmount": pending_amount if obligation_type == "pagar" else None,
        "pendingReceivableAmount": pending_amount if obligation_type == "receber" else None,
        "pendingValue": pending_amount,
        "valor_pendente_pagamento": pending_amount,
        "contas_pendentes": pending_amount,
        "cashFlowGroup": item["cash_flow_group"],
        "fluxo": item["cash_flow_group"],
        "nature": item["nature"],
        "natureza": item["nature"],
        "status": item["status"],
        "statusLabel": item["status_label"],
        "status_display": item["status_label"],
        "settlementStatus": item["settlement_status"],
        "settlementStatusLabel": item["settlement_status_label"],
        "isOverdue": item["is_overdue"],
        "daysOverdue": item["days_overdue"],
        "clientId": item["client_id"],
        "clientName": item["client_name"],
        "contractCode": item["contract_code"],
        "contractName": item.get("contract_name", ""),
        "contractLabel": item.get("contract_label", item["contract_code"]),
        "contract": item["contract_code"],
        "contrato_codigo": item["contract_code"],
        "eventId": item["event_id"],
        "eventName": item["event_name"],
        "eventNumber": item["event_number"],
        "eventLabel": item.get("event_label", item["event_name"]),
        "evento_id": item["event_id"],
        "evento_nome": item["event_name"],
        "evento_numero": item["event_number"],
        "evento_label": item.get("event_label", item["event_name"]),
        "isSeed": bool(item.get("is_seed")),
        "isReadOnly": bool(item.get("is_read_only")),
        "actionHints": serializar_action_hints_obrigacao(
            item,
            permissoes_action_hints=permissoes_action_hints,
        ),
        "readModelSource": item.get("read_model_source", "legacy"),
        "dataSource": item.get("read_model_source", "legacy"),
    }


def serializar_action_hints_obrigacao(item, *, permissoes_action_hints=None):
    acao_primaria = serializar_acao_operacional_obrigacao(
        item,
        permissoes_action_hints=permissoes_action_hints,
    )
    acao_admin = serializar_acao_admin_obrigacao(
        item,
        permissoes_action_hints=permissoes_action_hints,
    )
    acoes = [acao for acao in (acao_primaria, acao_admin) if acao]

    return {
        "primary": acao_primaria,
        "admin": acao_admin,
        "actions": acoes,
    }


def serializar_orientacao_conciliacao(diagnostico):
    orientacao = RECONCILIACAO_ORIENTACOES.get(
        diagnostico,
        RECONCILIACAO_ORIENTACOES["divergencia_valor"],
    )
    return {
        "code": orientacao["code"],
        "severity": orientacao["severity"],
        "title": orientacao["title"],
        "description": orientacao["description"],
    }


def serializar_acao_operacional_obrigacao(item, *, permissoes_action_hints=None):
    origem = item["source"]
    origem_id = item["source_id"]

    if origem == "custo_servico":
        if not pode_publicar_action_hint_pagamento_item(
            item, permissoes_action_hints
        ):
            return None

        return montar_action_hint(
            "legacyPayment",
            "Pagar custo de serviço",
            "/eventos/custos-servico/pagamentos/",
            {
                "custo_servico": origem_id,
                "tipo": item.get("source_detail"),
                "evento": item.get("event_id"),
                "situacao": "contas_pendentes",
            },
        )

    if origem == "custo_extra":
        if not pode_publicar_action_hint_pagamento_item(
            item, permissoes_action_hints
        ):
            return None

        return montar_action_hint(
            "legacyPayment",
            "Pagar custo extra",
            "/eventos/custos-extras/pagamentos/",
            {
                "custo_extra": origem_id,
                "evento": item.get("event_id"),
                "situacao": "contas_pendentes",
            },
        )

    if origem == "parcela_divida":
        if not pode_publicar_action_hint_pagamento_item(
            item, permissoes_action_hints
        ):
            return None

        return montar_action_hint(
            "legacyPayment",
            "Pagar parcela FCF",
            f"/fcf/parcelas/{origem_id}/pagar/",
        )

    if origem == "despesa_operacional":
        return montar_action_hint(
            "legacyList",
            "Abrir despesas",
            "/despesas/",
            {
                "busca": item.get("description"),
                "evento": item.get("event_id"),
                "cliente": item.get("client_id"),
            },
        )

    if origem == "receita_operacional":
        return montar_action_hint(
            "legacyList",
            "Abrir receitas",
            "/receitas/",
            {
                "busca": item.get("description"),
                "evento": item.get("event_id"),
                "cliente": item.get("client_id"),
            },
        )

    if origem == "custo_fixo":
        return montar_action_hint(
            "legacyList",
            "Abrir custos fixos",
            "/custos-fixos/",
            {"busca": item.get("description")},
        )

    if origem == "investimento":
        return montar_action_hint(
            "legacyList",
            "Abrir FCI",
            "/fci/",
            {
                **query_periodo_item(item),
                "contractCode": item.get("contract_code"),
                "eventId": item.get("event_id"),
            },
        )

    if origem == "financiamento_movimentacao":
        return montar_action_hint(
            "legacyList",
            "Abrir FCF",
            "/fcf/",
            {
                **query_periodo_item(item),
                "contractCode": item.get("contract_code"),
                "eventId": item.get("event_id"),
                **item.get("navigation_filters", {}),
            },
        )

    return None


def permissoes_action_hints_obrigacoes(usuario):
    return {
        "pagamentos": {
            origem: bool(usuario and usuario.has_perm(permissao))
            for origem, permissao in PERMISSOES_ACAO_PAGAMENTO_OBRIGACOES.items()
        },
        "admin": {
            origem: bool(
                usuario
                and (
                    usuario.has_perm(f"caixa.view_{modelo}")
                    or usuario.has_perm(f"caixa.change_{modelo}")
                )
            )
            for origem, modelo in ADMIN_MODELS_OBRIGACOES.items()
        },
    }


def pode_publicar_action_hint_pagamento(origem, permissoes_action_hints):
    return bool((permissoes_action_hints or {}).get("pagamentos", {}).get(origem))


def pode_publicar_action_hint_pagamento_item(item, permissoes_action_hints):
    if item.get("is_read_only"):
        return False

    if not pode_publicar_action_hint_pagamento(
        item["source"],
        permissoes_action_hints,
    ):
        return False

    if item.get("settlement_status") in {"liquidado", "cancelado"}:
        return False

    return decimal_item_action_hint(item.get("pending_amount")) > Decimal("0.00")


def decimal_item_action_hint(valor):
    try:
        return Decimal(str(valor or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def pode_publicar_action_hint_admin(origem, permissoes_action_hints):
    return bool((permissoes_action_hints or {}).get("admin", {}).get(origem))


def query_periodo_item(item):
    data = serializar_data(item.get("due_date"))
    if not data:
        return {}

    return {
        "startDate": data,
        "endDate": data,
    }


def serializar_acao_admin_obrigacao(item, *, permissoes_action_hints=None):
    modelo = ADMIN_MODELS_OBRIGACOES.get(item["source"])
    if not modelo:
        return None

    if not pode_publicar_action_hint_admin(item["source"], permissoes_action_hints):
        return None

    return montar_action_hint(
        "adminChange",
        "Abrir origem no admin",
        f"/admin/caixa/{modelo}/{item['source_id']}/change/",
    )


def montar_action_hint(tipo, label, path, query=None):
    return {
        "type": tipo,
        "label": label,
        "target": "backend",
        "path": path,
        "query": limpar_query_action_hint(query or {}),
    }


def limpar_query_action_hint(query):
    return {
        chave: valor
        for chave, valor in query.items()
        if valor not in (None, "")
    }


def serializar_disponibilidade_caixa_obrigacoes(filtros, resumo):
    posicao_caixa = montar_posicao_caixa_periodo(
        filtros_posicao_caixa_obrigacoes(filtros)
    )
    data_referencia = posicao_caixa["cashAvailableUntilDate"]
    tipo_obrigacao = filtros.get("obligationType") or "pagar"
    aplicavel = tipo_obrigacao == "pagar"
    caixa_disponivel = posicao_caixa["availableCashAmount"]
    caixa_disponivel_atual = posicao_caixa["currentAvailableCashAmount"]
    caixa_acumulado_ate_data = posicao_caixa["accumulatedCashUntilDate"]
    pendente_escopo = resumo["pending_amount"]
    cobertura_apos_pendencias = quantizar_moeda(caixa_disponivel - pendente_escopo)
    cobertura_atual_apos_pendencias = quantizar_moeda(
        caixa_disponivel_atual - pendente_escopo
    )
    deficit_cobertura = quantizar_moeda(
        pendente_escopo - caixa_disponivel
        if pendente_escopo > caixa_disponivel
        else Decimal("0.00")
    )
    deficit_cobertura_atual = quantizar_moeda(
        pendente_escopo - caixa_disponivel_atual
        if pendente_escopo > caixa_disponivel_atual
        else Decimal("0.00")
    )

    return {
        "applicable": aplicavel,
        "aplicavel": aplicavel,
        "appliesToObligationType": "pagar",
        "obligationTypeScope": tipo_obrigacao,
        "tipoObrigacaoEscopo": tipo_obrigacao,
        "availableCashAmount": decimal_para_numero(caixa_disponivel),
        "cashAvailableAmount": decimal_para_numero(caixa_disponivel),
        "caixaDisponivel": decimal_para_numero(caixa_disponivel),
        "saldoCaixaDisponivel": decimal_para_numero(caixa_disponivel),
        "finalCashAmount": decimal_para_numero(posicao_caixa["finalCashAmount"]),
        "currentAvailableCashAmount": decimal_para_numero(
            caixa_disponivel_atual
        ),
        "currentCashAvailableUntilDate": posicao_caixa[
            "currentCashAvailableUntilDate"
        ],
        "initialCashAmount": decimal_para_numero(posicao_caixa["initialCashAmount"]),
        "realizedInflowAmount": decimal_para_numero(
            posicao_caixa["realizedInflowAmount"]
        ),
        "realizedOutflowAmount": decimal_para_numero(
            posicao_caixa["realizedOutflowAmount"]
        ),
        "periodRealizedAmount": decimal_para_numero(
            posicao_caixa["periodRealizedAmount"]
        ),
        "accumulatedCashUntilDate": decimal_para_numero(caixa_acumulado_ate_data),
        "accumulatedAvailableCashAmount": decimal_para_numero(
            caixa_acumulado_ate_data
        ),
        "cashAvailableUntilDate": data_referencia,
        "pendingScopeAmount": decimal_para_numero(pendente_escopo),
        "pendingPayablesAmount": (
            decimal_para_numero(pendente_escopo) if aplicavel else None
        ),
        "cashCoverageAfterPendingAmount": (
            decimal_para_numero(cobertura_apos_pendencias) if aplicavel else None
        ),
        "paymentCapacityAfterPendingAmount": (
            decimal_para_numero(cobertura_apos_pendencias) if aplicavel else None
        ),
        "currentCashCoverageAfterPendingAmount": (
            decimal_para_numero(cobertura_atual_apos_pendencias)
            if aplicavel
            else None
        ),
        "availableAfterPendingAmount": (
            decimal_para_numero(cobertura_apos_pendencias) if aplicavel else None
        ),
        "cashCoverageDeficitAmount": (
            decimal_para_numero(deficit_cobertura) if aplicavel else None
        ),
        "currentCashCoverageDeficitAmount": (
            decimal_para_numero(deficit_cobertura_atual) if aplicavel else None
        ),
        "dateBasis": "data_lancamento efetiva dentro do periodo",
        "formula": (
            "initialCashAmount + realizedInflowAmount - realizedOutflowAmount"
        ),
        "accumulatedDateBasis": (
            "data_recebimento/data_pagamento acumulado ate endDate"
        ),
        "accumulatedFormula": (
            "accumulatedEffectiveInflowsUntilDate "
            "- accumulatedEffectiveOutflowsUntilDate"
        ),
        "coverageFormula": "finalCashAmount - pendingPayablesAmount",
    }


def filtros_posicao_caixa_obrigacoes(filtros):
    return {
        "startDate": filtros.get("startDate"),
        "endDate": filtros.get("endDate"),
        "eventId": filtros.get("eventId"),
        "clientId": filtros.get("clientId"),
        "contractCode": filtros.get("contractCode"),
        "quickPeriod": filtros.get("quickPeriod"),
    }


def serializar_resumo_obrigacoes(resumo, overview=None):
    payload = {
        "plannedAmount": decimal_para_numero(resumo["planned_amount"]),
        "realizedAmount": decimal_para_numero(resumo["realized_amount"]),
        "paidAmount": decimal_para_numero(resumo["realized_amount"]),
        "overRealizedAmount": decimal_para_numero(resumo["over_realized_amount"]),
        "realizedAbovePlannedAmount": decimal_para_numero(
            resumo["over_realized_amount"]
        ),
        "pendingAmount": decimal_para_numero(resumo["pending_amount"]),
        "originRealizedAmount": decimal_para_numero(resumo["origin_realized_amount"]),
        "originPendingAmount": decimal_para_numero(resumo["origin_pending_amount"]),
        "originOverRealizedAmount": decimal_para_numero(
            resumo["origin_over_realized_amount"]
        ),
        "ledgerRealizedAmount": decimal_para_numero(resumo["ledger_realized_amount"]),
        "ledgerPendingAmount": decimal_para_numero(resumo["ledger_pending_amount"]),
        "ledgerOverRealizedAmount": decimal_para_numero(
            resumo["ledger_over_realized_amount"]
        ),
        "realizedAmountDifference": decimal_para_numero(
            resumo["realized_amount_difference"]
        ),
        "reconciledCount": resumo["reconciled_count"],
        "divergentCount": resumo["divergent_count"],
        "overdueAmount": decimal_para_numero(resumo["overdue_amount"]),
        "obligationsCount": resumo["count"],
        "pendingCount": resumo["pending_count"],
        "overdueCount": resumo["overdue_count"],
        "liquidatedCount": resumo["liquidated_count"],
        "ledgerPendingCount": resumo["ledger_pending_count"],
        "ledgerOverdueCount": resumo["ledger_overdue_count"],
        "ledgerLiquidatedCount": resumo["ledger_liquidated_count"],
        "ledgerOverdueAmount": decimal_para_numero(resumo["ledger_overdue_amount"]),
        "valor_previsto": decimal_para_numero(resumo["planned_amount"]),
        "valor_pago": decimal_para_numero(resumo["realized_amount"]),
        "valor_excedente_realizado": decimal_para_numero(resumo["over_realized_amount"]),
        "contas_pendentes": decimal_para_numero(resumo["pending_amount"]),
        "valor_realizado_origem": decimal_para_numero(resumo["origin_realized_amount"]),
        "valor_pendente_origem": decimal_para_numero(resumo["origin_pending_amount"]),
        "valor_excedente_origem": decimal_para_numero(
            resumo["origin_over_realized_amount"]
        ),
        "valor_realizado_ledger": decimal_para_numero(resumo["ledger_realized_amount"]),
        "valor_pendente_ledger": decimal_para_numero(resumo["ledger_pending_amount"]),
        "valor_excedente_ledger": decimal_para_numero(
            resumo["ledger_over_realized_amount"]
        ),
        "diferenca_realizado_ledger": decimal_para_numero(
            resumo["realized_amount_difference"]
        ),
        "byCashFlowGroup": {
            fluxo: serializar_resumo_obrigacoes_fluxo(valores)
            for fluxo, valores in resumo["byCashFlowGroup"].items()
        },
        "bySource": {
            origem: {
                **serializar_resumo_obrigacoes_fluxo(valores),
                "sourceLabel": valores["sourceLabel"],
            }
            for origem, valores in sorted(resumo["bySource"].items())
        },
        "byReconciliationDiagnosis": {
            diagnostico: serializar_resumo_obrigacoes_diagnostico(
                diagnostico,
                valores,
            )
            for diagnostico, valores in sorted(
                resumo.get("byReconciliationDiagnosis", {}).items()
            )
        },
        "reconciliationWorklist": [
            serializar_fila_trabalho_conciliacao(grupo)
            for grupo in resumo.get("reconciliationWorklist", [])
        ],
    }
    if overview is not None:
        payload["overview"] = serializar_overview_obrigacoes(overview)
    return payload


def serializar_overview_obrigacoes(overview):
    return {
        "contractVersion": overview["contract_version"],
        "dateBasis": overview["date_basis"],
        "amountBasis": overview["amount_basis"],
        "scope": {
            "obligationType": overview["scope"]["obligation_type"],
            "cashFlowGroup": overview["scope"]["cash_flow_group"],
            "source": overview["scope"]["source"],
            "sources": overview["scope"]["sources"],
        },
        "totals": serializar_overview_totais(overview["totals"]),
        "monthlySeries": [
            serializar_overview_grupo(grupo)
            for grupo in overview["monthly_series"]
        ],
        "breakdownBySettlementStatus": [
            serializar_overview_grupo(grupo)
            for grupo in overview["breakdown_by_settlement_status"]
        ],
        "breakdownBySource": [
            serializar_overview_grupo(grupo)
            for grupo in overview["breakdown_by_source"]
        ],
        "breakdownByCategory": [
            serializar_overview_grupo(grupo)
            for grupo in overview["breakdown_by_category"]
        ],
    }


def serializar_overview_totais(totais):
    return {
        "itemsCount": totais["items_count"],
        "plannedAmount": decimal_para_numero(totais["planned_amount"]),
        "realizedAmount": decimal_para_numero(totais["realized_amount"]),
        "pendingAmount": decimal_para_numero(totais["pending_amount"]),
        "overdueAmount": decimal_para_numero(totais["overdue_amount"]),
        "overdueCount": totais["overdue_count"],
        "settledCount": totais["settled_count"],
        "distinctEventsCount": totais.get("distinct_events_count", 0),
        "distinctClientsCount": totais.get("distinct_clients_count", 0),
    }


def serializar_overview_grupo(grupo):
    payload = {
        "key": grupo["key"],
        "label": grupo["label"],
        "plannedAmount": decimal_para_numero(grupo["planned_amount"]),
        "realizedAmount": decimal_para_numero(grupo["realized_amount"]),
        "pendingAmount": decimal_para_numero(grupo["pending_amount"]),
        "overdueAmount": decimal_para_numero(grupo["overdue_amount"]),
        "itemsCount": grupo["items_count"],
    }
    if "pending_count" in grupo:
        payload["pendingCount"] = grupo["pending_count"]
    if "settled_count" in grupo:
        payload["settledCount"] = grupo["settled_count"]
    if "overdue_count" in grupo:
        payload["overdueCount"] = grupo["overdue_count"]
    if "percentage_by_planned_amount" in grupo:
        payload["percentageByPlannedAmount"] = decimal_para_numero(
            grupo["percentage_by_planned_amount"]
        )

    for origem, destino in (
        ("source", "source"),
        ("source_label", "sourceLabel"),
        ("source_detail", "sourceDetail"),
        ("source_detail_label", "sourceDetailLabel"),
    ):
        if origem in grupo:
            payload[destino] = grupo[origem]

    return payload


def montar_payment_queue_obrigacoes(itens, filtros, contrato_baixa):
    if not deve_publicar_payment_queue_obrigacoes(filtros):
        return None

    reference_date = timezone.localdate()
    candidates = listar_payment_queue_candidates(itens, contrato_baixa, reference_date)
    candidates = filtrar_payment_queue_candidates(candidates, filtros.get("queueFilter"))
    total = len(candidates)
    limit = normalizar_inteiro(filtros.get("queueLimit"), LIMITE_PADRAO, 1, LIMITE_MAXIMO)
    offset = normalizar_inteiro(filtros.get("queueOffset"), 0, 0, total)
    candidates_paginados = candidates[offset:offset + limit]

    return {
        "contractVersion": PAYMENT_QUEUE_CONTRACT_VERSION,
        "generatedAt": timezone.now().isoformat(),
        "referenceDate": reference_date.isoformat(),
        "referenceDateSource": "server",
        "dateBasis": "dueDate",
        "amountBasis": "originState",
        "scope": serializar_payment_queue_scope(filtros),
        "queueSummary": serializar_payment_queue_summary(candidates),
        "urgencyBuckets": serializar_payment_queue_urgency_buckets(candidates),
        "facets": serializar_payment_queue_facets(candidates),
        "sorting": {
            "officialOrder": ["urgency", "dueDate", "pendingAmountDesc", "id"],
            "urgencyOrder": list(PAYMENT_QUEUE_URGENCY_ORDER),
        },
        "readinessRules": [dict(rule) for rule in PAYMENT_QUEUE_READINESS_RULES],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "hasMore": offset + limit < total,
        },
        "items": [serializar_payment_queue_item(candidate) for candidate in candidates_paginados],
    }


def listar_payment_queue_candidates(itens, contrato_baixa, reference_date):
    candidates = [
        candidate
        for candidate in (
            montar_payment_queue_candidate(item, contrato_baixa, reference_date)
            for item in itens
        )
        if candidate is not None
    ]
    candidates.sort(key=payment_queue_sort_key)
    return candidates


def filtrar_payment_queue_candidates(candidates, queue_filter):
    queue_filter = normalizar_payment_queue_filter(queue_filter)
    if queue_filter == "overdue":
        return [candidate for candidate in candidates if candidate["urgency"] == "overdue"]
    if queue_filter == "next7":
        return [
            candidate
            for candidate in candidates
            if candidate["urgency"] in {"today", "next7"}
        ]
    if queue_filter == "blocked":
        return [candidate for candidate in candidates if not candidate["canSettle"]]
    return candidates


def deve_publicar_payment_queue_obrigacoes(filtros):
    return (
        filtros.get("permissionScope") == PAYMENT_QUEUE_PERMISSION_SCOPE
        and filtros.get("obligationType") == "pagar"
    )


def serializar_payment_queue_scope(filtros):
    return {
        "permissionScope": filtros.get("permissionScope") or "",
        "obligationType": filtros.get("obligationType") or "",
        "dataSource": filtros.get("dataSource") or "",
        "source": filtros.get("source") or "",
        "sources": list(filtros.get("sources") or []),
        "overdueScope": filtros.get("overdueScope") or "",
        "queueFilter": filtros.get("queueFilter") or "all",
        "search": filtros.get("search") or "",
        "startDate": filtros.get("startDate") or "",
        "endDate": filtros.get("endDate") or "",
        "eventId": filtros.get("eventId") or "",
        "clientId": filtros.get("clientId") or "",
        "contractCode": filtros.get("contractCode") or "",
    }


def montar_payment_queue_candidate(item, contrato_baixa, reference_date):
    pending_amount = payment_queue_origin_pending_amount(item)
    settlement_status = item.get("settlement_status") or ""

    if item.get("obligation_type") != "pagar":
        return None
    if settlement_status in {"liquidado", "cancelado"}:
        return None
    if pending_amount <= Decimal("0.00"):
        return None

    source_capability = (
        (contrato_baixa or {}).get("sources", {}).get(item.get("source")) or {}
    )
    readiness = avaliar_prontidao_payment_queue(item, source_capability, pending_amount)
    due_date = item.get("due_date")
    days_until_due = calcular_dias_ate_vencimento(due_date, reference_date)
    urgency = calcular_urgencia_payment_queue(item, days_until_due)

    return {
        "item": item,
        "pendingAmount": pending_amount,
        "urgency": urgency,
        "daysUntilDue": days_until_due,
        **readiness,
    }


def payment_queue_origin_pending_amount(item):
    valor = item.get("origin_pending_amount", item.get("pending_amount", Decimal("0.00")))
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor or "0"))
    return valor


def avaliar_prontidao_payment_queue(item, source_capability, pending_amount):
    supported_obligation_types = source_capability.get("supportedObligationTypes") or []
    supports_obligation_type = (
        not supported_obligation_types or "pagar" in supported_obligation_types
    )
    supports_native_settlement = bool(
        source_capability.get(
            "nativeSettlement",
            source_capability.get("supportsNativeSettlement", False),
        )
    )
    can_use_native_settlement = bool(
        source_capability.get(
            "canSettle",
            source_capability.get("canUseNativeSettlement", False),
        )
    )
    requires_source_detail = bool(source_capability.get("requiresSourceDetail"))
    source_detail = str(item.get("source_detail") or "").strip()
    settlement_status = item.get("settlement_status") or ""

    blocked_reason = ""
    if item.get("is_read_only"):
        blocked_reason = "demo_seed_read_only"
    elif not supports_native_settlement or not can_use_native_settlement:
        blocked_reason = "native_settlement_unavailable"
    elif not supports_obligation_type:
        blocked_reason = "unsupported_obligation_type"
    elif requires_source_detail and not source_detail:
        blocked_reason = "missing_source_detail"
    elif pending_amount <= Decimal("0.00"):
        blocked_reason = "no_pending_amount"
    elif settlement_status == "liquidado":
        blocked_reason = "settled"
    elif settlement_status == "cancelado":
        blocked_reason = "cancelled"

    return {
        "canSettle": not blocked_reason,
        "blockedReason": blocked_reason,
        "blockedReasonLabel": PAYMENT_QUEUE_BLOCK_REASON_LABELS.get(
            blocked_reason,
            "",
        ),
        "supportsPaymentMethod": bool(source_capability.get("supportsPaymentMethod")),
        "supportsPaymentDescription": bool(
            source_capability.get("supportsPaymentDescription")
        ),
        "supportsAdjustments": bool(source_capability.get("supportsAdjustments")),
        "supportsWriteOff": bool(source_capability.get("supportsWriteOff", True)),
        "requiresSourceDetail": requires_source_detail,
    }


def calcular_dias_ate_vencimento(due_date, reference_date):
    if not due_date:
        return None
    return (due_date - reference_date).days


def calcular_urgencia_payment_queue(item, days_until_due):
    if item.get("is_overdue") or (days_until_due is not None and days_until_due < 0):
        return "overdue"
    if days_until_due == 0:
        return "today"
    if days_until_due is not None and days_until_due <= 7:
        return "next7"
    return "later"


def payment_queue_sort_key(candidate):
    item = candidate["item"]
    due_date = item.get("due_date") or timezone.datetime.max.date()
    return (
        PAYMENT_QUEUE_URGENCY_ORDER.index(candidate["urgency"]),
        due_date,
        -candidate["pendingAmount"],
        str(item.get("id") or ""),
    )


def serializar_payment_queue_summary(candidates):
    summary = inicializar_payment_queue_summary()
    for candidate in candidates:
        somar_payment_queue_summary(summary, candidate)
    return serializar_payment_queue_summary_values(summary)


def inicializar_payment_queue_summary():
    return {
        "count": 0,
        "pendingAmount": Decimal("0.00"),
        "readyCount": 0,
        "readyAmount": Decimal("0.00"),
        "blockedCount": 0,
        "blockedAmount": Decimal("0.00"),
        "overdueCount": 0,
        "overdueAmount": Decimal("0.00"),
        "todayCount": 0,
        "todayAmount": Decimal("0.00"),
        "next7Count": 0,
        "next7Amount": Decimal("0.00"),
        "laterCount": 0,
        "laterAmount": Decimal("0.00"),
    }


def somar_payment_queue_summary(summary, candidate):
    pending_amount = candidate["pendingAmount"]
    urgency = candidate["urgency"]
    summary["count"] += 1
    summary["pendingAmount"] += pending_amount

    if candidate["canSettle"]:
        summary["readyCount"] += 1
        summary["readyAmount"] += pending_amount
    else:
        summary["blockedCount"] += 1
        summary["blockedAmount"] += pending_amount

    if urgency == "overdue":
        summary["overdueCount"] += 1
        summary["overdueAmount"] += pending_amount
    elif urgency == "today":
        summary["todayCount"] += 1
        summary["todayAmount"] += pending_amount
    elif urgency == "later":
        summary["laterCount"] += 1
        summary["laterAmount"] += pending_amount

    if urgency in {"today", "next7"}:
        summary["next7Count"] += 1
        summary["next7Amount"] += pending_amount


def serializar_payment_queue_summary_values(summary):
    return {
        "count": summary["count"],
        "pendingAmount": decimal_para_numero(summary["pendingAmount"]),
        "readyCount": summary["readyCount"],
        "readyAmount": decimal_para_numero(summary["readyAmount"]),
        "blockedCount": summary["blockedCount"],
        "blockedAmount": decimal_para_numero(summary["blockedAmount"]),
        "overdueCount": summary["overdueCount"],
        "overdueAmount": decimal_para_numero(summary["overdueAmount"]),
        "todayCount": summary["todayCount"],
        "todayAmount": decimal_para_numero(summary["todayAmount"]),
        "next7Count": summary["next7Count"],
        "next7Amount": decimal_para_numero(summary["next7Amount"]),
        "laterCount": summary["laterCount"],
        "laterAmount": decimal_para_numero(summary["laterAmount"]),
    }


def serializar_payment_queue_urgency_buckets(candidates):
    buckets = {urgency: inicializar_payment_queue_group() for urgency in PAYMENT_QUEUE_URGENCY_ORDER}
    for candidate in candidates:
        somar_payment_queue_group(buckets[candidate["urgency"]], candidate)
    return [
        {
            "key": urgency,
            "label": PAYMENT_QUEUE_URGENCY_LABELS[urgency],
            **serializar_payment_queue_group_values(buckets[urgency]),
        }
        for urgency in PAYMENT_QUEUE_URGENCY_ORDER
    ]


def serializar_payment_queue_facets(candidates):
    source_groups = {}
    status_groups = {}
    readiness_groups = {
        "ready": inicializar_payment_queue_group(),
        "blocked": inicializar_payment_queue_group(),
    }
    capability_groups = {
        key: inicializar_payment_queue_group()
        for key, _label in PAYMENT_QUEUE_CAPABILITY_FIELDS
    }
    block_reason_groups = {}

    for candidate in candidates:
        item = candidate["item"]
        source_key = item.get("source") or ""
        source_group = source_groups.setdefault(
            source_key,
            {
                **inicializar_payment_queue_group(),
                "value": source_key,
                "label": item.get("source_label") or source_key,
            },
        )
        somar_payment_queue_group(source_group, candidate)

        status_key = item.get("settlement_status") or ""
        status_group = status_groups.setdefault(
            status_key,
            {
                **inicializar_payment_queue_group(),
                "value": status_key,
                "label": item.get("settlement_status_label") or status_key,
            },
        )
        somar_payment_queue_group(status_group, candidate)

        readiness_key = "ready" if candidate["canSettle"] else "blocked"
        somar_payment_queue_group(readiness_groups[readiness_key], candidate)

        for capability_key, _label in PAYMENT_QUEUE_CAPABILITY_FIELDS:
            if candidate.get(capability_key):
                somar_payment_queue_group(capability_groups[capability_key], candidate)

        if candidate["blockedReason"]:
            block_reason_group = block_reason_groups.setdefault(
                candidate["blockedReason"],
                {
                    **inicializar_payment_queue_group(),
                    "key": candidate["blockedReason"],
                    "label": candidate["blockedReasonLabel"],
                },
            )
            somar_payment_queue_group(block_reason_group, candidate)

    return {
        "sources": [
            serializar_payment_queue_source_facet(grupo)
            for grupo in sorted(source_groups.values(), key=lambda grupo: grupo["value"])
        ],
        "settlementStatuses": [
            serializar_payment_queue_value_facet(grupo)
            for grupo in sorted(status_groups.values(), key=lambda grupo: grupo["value"])
        ],
        "readiness": [
            {
                "value": "ready",
                "label": "Prontas para baixa",
                **serializar_payment_queue_group_values(readiness_groups["ready"]),
            },
            {
                "value": "blocked",
                "label": "Bloqueadas",
                **serializar_payment_queue_group_values(readiness_groups["blocked"]),
            },
        ],
        "capabilities": [
            {
                "key": key,
                "label": label,
                **serializar_payment_queue_group_values(capability_groups[key]),
            }
            for key, label in PAYMENT_QUEUE_CAPABILITY_FIELDS
        ],
        "blockReasons": [
            serializar_payment_queue_block_reason_facet(grupo)
            for grupo in sorted(block_reason_groups.values(), key=lambda grupo: grupo["key"])
        ],
    }


def inicializar_payment_queue_group():
    return {
        "count": 0,
        "pendingAmount": Decimal("0.00"),
        "readyCount": 0,
        "readyAmount": Decimal("0.00"),
        "blockedCount": 0,
        "blockedAmount": Decimal("0.00"),
    }


def somar_payment_queue_group(group, candidate):
    pending_amount = candidate["pendingAmount"]
    group["count"] += 1
    group["pendingAmount"] += pending_amount
    if candidate["canSettle"]:
        group["readyCount"] += 1
        group["readyAmount"] += pending_amount
    else:
        group["blockedCount"] += 1
        group["blockedAmount"] += pending_amount


def serializar_payment_queue_group_values(group):
    return {
        "count": group["count"],
        "pendingAmount": decimal_para_numero(group["pendingAmount"]),
        "readyCount": group["readyCount"],
        "readyAmount": decimal_para_numero(group["readyAmount"]),
        "blockedCount": group["blockedCount"],
        "blockedAmount": decimal_para_numero(group["blockedAmount"]),
    }


def serializar_payment_queue_source_facet(group):
    return {
        "value": group["value"],
        "label": group["label"],
        **serializar_payment_queue_group_values(group),
    }


def serializar_payment_queue_value_facet(group):
    return {
        "value": group["value"],
        "label": group["label"],
        "count": group["count"],
        "pendingAmount": decimal_para_numero(group["pendingAmount"]),
    }


def serializar_payment_queue_block_reason_facet(group):
    return {
        "key": group["key"],
        "label": group["label"],
        "count": group["count"],
        "pendingAmount": decimal_para_numero(group["pendingAmount"]),
    }


def serializar_payment_queue_item(candidate):
    item = candidate["item"]
    pending_amount = candidate["pendingAmount"]
    sort_key = payment_queue_sort_key(candidate)
    return {
        "id": item["id"],
        "source": item["source"],
        "sourceId": item["source_id"],
        "sourceLabel": item["source_label"],
        "sourceDetail": item.get("source_detail") or "",
        "sourceDetailLabel": item.get("source_detail_label") or "",
        "description": item["description"],
        "obligationDescription": item["description"],
        "reference": item["reference"],
        "dueDate": serializar_data(item.get("due_date")),
        "settlementStatus": item.get("settlement_status") or "",
        "settlementStatusLabel": item.get("settlement_status_label") or "",
        "plannedAmount": decimal_para_numero(item["planned_amount"]),
        "realizedAmount": decimal_para_numero(item["realized_amount"]),
        "pendingAmount": decimal_para_numero(pending_amount),
        "originPendingAmount": decimal_para_numero(pending_amount),
        "originRealizedAmount": decimal_para_numero(
            item.get("origin_realized_amount", item["realized_amount"])
        ),
        "eventId": item.get("event_id"),
        "eventLabel": item.get("event_label") or item.get("event_name") or "",
        "clientName": item.get("client_name") or "",
        "contractCode": item.get("contract_code") or "",
        "contractLabel": item.get("contract_label") or item.get("contract_code") or "",
        "urgency": candidate["urgency"],
        "daysUntilDue": candidate["daysUntilDue"],
        "canSettle": candidate["canSettle"],
        "blockedReason": candidate["blockedReason"],
        "blockedReasonLabel": candidate["blockedReasonLabel"],
        "supportsPaymentMethod": candidate["supportsPaymentMethod"],
        "supportsPaymentDescription": candidate["supportsPaymentDescription"],
        "supportsAdjustments": candidate["supportsAdjustments"],
        "supportsWriteOff": candidate["supportsWriteOff"],
        "requiresSourceDetail": candidate["requiresSourceDetail"],
        "sortKey": {
            "urgency": candidate["urgency"],
            "dueDate": serializar_data(item.get("due_date")),
            "pendingAmountDesc": decimal_para_numero(pending_amount),
            "id": str(item.get("id") or ""),
            "order": [
                sort_key[0],
                serializar_data(item.get("due_date")),
                decimal_para_numero(pending_amount),
                str(item.get("id") or ""),
            ],
        },
    }


def montar_exportacao_obrigacoes_financeiras_csv(params, usuario=None):
    export_scope = normalizar_export_scope_obrigacoes(params.get("exportScope"))
    export_format = str(params.get("format") or "csv").strip().lower()
    if export_format != "csv":
        raise ValidationError({"format": "Formato de exportacao nao suportado."})

    filtros = normalizar_filtros_obrigacoes(params)
    itens, fonte_dados = listar_obrigacoes_com_fonte(filtros)
    filtros_serializados = serializar_filtros_obrigacoes(filtros)
    filtros_aplicados = json.dumps(
        filtros_serializados,
        ensure_ascii=False,
        sort_keys=True,
    )

    if export_scope == "payments":
        contrato_baixa = serializar_contrato_baixa_obrigacoes_usuario(usuario)
        candidates = listar_payment_queue_candidates(
            itens,
            contrato_baixa,
            timezone.localdate(),
        )
        candidates = filtrar_payment_queue_candidates_exportacao(
            candidates,
            params.get("queueFilter"),
        )
        headers, rows = linhas_csv_exportacao_pagamentos(
            candidates,
            filtros_aplicados,
        )
    else:
        headers, rows = linhas_csv_exportacao_obrigacoes(
            itens,
            export_scope,
            filtros,
            fonte_dados,
            filtros_aplicados,
        )

    return {
        "filename": nome_arquivo_exportacao_obrigacoes(export_scope, filtros),
        "content": renderizar_csv_completo(headers, rows),
        "rowCount": len(rows),
    }


def normalizar_export_scope_obrigacoes(valor):
    export_scope = str(valor or "obligations").strip()
    if export_scope not in EXPORT_SCOPES_OBRIGACOES:
        raise ValidationError({"exportScope": "Escopo de exportacao invalido."})
    return export_scope


def linhas_csv_exportacao_obrigacoes(
    itens,
    export_scope,
    filtros,
    fonte_dados,
    filtros_aplicados,
):
    if export_scope in {"revenues", "expenses"}:
        headers = [
            "item",
            "descricao",
            "origem",
            "detalhe_origem",
            "evento",
            "cliente",
            "contrato",
            "vencimento",
            "status",
            "previsto",
            "realizado",
            "pendente",
            "fluxo",
            "filtros_aplicados",
        ]
        return headers, [
            [
                item["id"],
                item.get("description") or "",
                item["source_label"],
                item.get("source_detail_label") or item.get("source_detail") or "",
                item.get("event_label") or item.get("event_name") or "",
                item.get("client_name") or "",
                item.get("contract_label") or item.get("contract_code") or "",
                serializar_data(item.get("due_date")),
                item.get("settlement_status_label") or item.get("status_label") or "",
                csv_decimal(item["planned_amount"]),
                csv_decimal(item["realized_amount"]),
                csv_decimal(item["pending_amount"]),
                item.get("cash_flow_group") or "",
                filtros_aplicados,
            ]
            for item in itens
        ]

    headers = [
        "obrigacao",
        "descricao",
        "tipo",
        "origem",
        "detalhe_origem",
        "fluxo",
        "vencimento",
        "contrato",
        "evento",
        "cliente",
        "previsto",
        "realizado_origem",
        "pendente_origem",
        "realizado_ledger",
        "pendente_ledger",
        "acima_previsto_origem",
        "acima_previsto_ledger",
        "diferenca_realizada",
        "status",
        "status_conciliacao",
        "diagnostico_conciliacao",
        "base_realizada",
        "read_model",
        "filtros_aplicados",
    ]
    realized_basis = filtros.get("realizedAmountBasis") or "originState"
    read_model = fonte_dados.get("actual") or ""
    return headers, [
        [
            item["id"],
            item.get("description") or "",
            item.get("obligation_type") or "",
            item["source_label"],
            item.get("source_detail_label") or item.get("source_detail") or "",
            item.get("cash_flow_group") or "",
            serializar_data(item.get("due_date")),
            item.get("contract_label") or item.get("contract_code") or "",
            item.get("event_label") or item.get("event_name") or "",
            item.get("client_name") or "",
            csv_decimal(item["planned_amount"]),
            csv_decimal(item.get("origin_realized_amount", item["realized_amount"])),
            csv_decimal(item.get("origin_pending_amount", item["pending_amount"])),
            csv_decimal(item.get("ledger_realized_amount", Decimal("0.00"))),
            csv_decimal(item.get("ledger_pending_amount", Decimal("0.00"))),
            csv_decimal(item.get("origin_over_realized_amount", Decimal("0.00"))),
            csv_decimal(item.get("ledger_over_realized_amount", Decimal("0.00"))),
            csv_decimal(item.get("realized_amount_difference", Decimal("0.00"))),
            item.get("settlement_status_label") or item.get("status_label") or "",
            item.get("reconciliation_status") or "",
            item.get("reconciliation_diagnosis_label")
            or item.get("reconciliation_diagnosis")
            or "",
            realized_basis,
            item.get("read_model_source") or read_model,
            filtros_aplicados,
        ]
        for item in itens
    ]


def linhas_csv_exportacao_pagamentos(candidates, filtros_aplicados):
    headers = [
        "obrigacao",
        "descricao",
        "origem",
        "detalhe_origem",
        "evento",
        "cliente",
        "contrato",
        "vencimento",
        "status",
        "previsto",
        "realizado_origem",
        "pendente_origem",
        "urgencia",
        "dias_ate_vencimento",
        "pronta_para_baixa",
        "motivo_bloqueio",
        "suporta_forma_pagamento",
        "suporta_descricao_pagamento",
        "suporta_ajustes",
        "suporta_baixa_saldo",
        "filtros_aplicados",
    ]
    rows = []
    for candidate in candidates:
        item = candidate["item"]
        rows.append(
            [
                item["id"],
                item.get("description") or "",
                item["source_label"],
                item.get("source_detail_label") or item.get("source_detail") or "",
                item.get("event_label") or item.get("event_name") or "",
                item.get("client_name") or "",
                item.get("contract_label") or item.get("contract_code") or "",
                serializar_data(item.get("due_date")),
                item.get("settlement_status_label") or item.get("status_label") or "",
                csv_decimal(item["planned_amount"]),
                csv_decimal(item.get("origin_realized_amount", item["realized_amount"])),
                csv_decimal(candidate["pendingAmount"]),
                candidate["urgency"],
                "" if candidate["daysUntilDue"] is None else candidate["daysUntilDue"],
                csv_bool(candidate["canSettle"]),
                candidate["blockedReasonLabel"],
                csv_bool(candidate["supportsPaymentMethod"]),
                csv_bool(candidate["supportsPaymentDescription"]),
                csv_bool(candidate["supportsAdjustments"]),
                csv_bool(candidate["supportsWriteOff"]),
                filtros_aplicados,
            ]
        )
    return headers, rows


def filtrar_payment_queue_candidates_exportacao(candidates, queue_filter):
    return filtrar_payment_queue_candidates(candidates, queue_filter)


def renderizar_csv_completo(headers, rows):
    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def nome_arquivo_exportacao_obrigacoes(export_scope, filtros):
    periodo = filtros.get("period") or ""
    if not periodo:
        inicio = filtros.get("startDate") or "inicio"
        fim = filtros.get("endDate") or "fim"
        periodo = f"{inicio}-{fim}"
    hoje = timezone.localdate().isoformat()
    return f"{export_scope}-{periodo}-{hoje}.csv"


def csv_decimal(valor):
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor or "0"))
    return f"{quantizar_moeda(valor):.2f}"


def csv_bool(valor):
    return "sim" if valor else "nao"


def serializar_resumo_obrigacoes_diagnostico(diagnostico, resumo):
    orientacao = serializar_orientacao_conciliacao(diagnostico)
    return {
        **serializar_resumo_obrigacoes_fluxo(resumo),
        "label": resumo["label"],
        "guidance": orientacao,
        "orientacaoConciliacao": orientacao,
    }


def serializar_fila_trabalho_conciliacao(grupo):
    diagnostico = grupo["reconciliation_diagnosis"]
    orientacao = serializar_orientacao_conciliacao(diagnostico)
    return {
        **serializar_resumo_obrigacoes_fluxo(grupo),
        "key": grupo["key"],
        "obligationType": grupo.get("obligation_type", "pagar"),
        "tipoObrigacao": grupo.get("obligation_type", "pagar"),
        "tipo_obrigacao": grupo.get("obligation_type", "pagar"),
        "reconciliationDiagnosis": diagnostico,
        "reconciliationDiagnosisLabel": grupo["reconciliation_diagnosis_label"],
        "diagnosticoConciliacao": diagnostico,
        "diagnosticoConciliacaoLabel": grupo["reconciliation_diagnosis_label"],
        "guidance": orientacao,
        "orientacaoConciliacao": orientacao,
        "source": grupo["source"],
        "origin": grupo["source"],
        "origem": grupo["source"],
        "sourceLabel": grupo["source_label"],
        "contractCode": grupo["contract_code"],
        "contractName": grupo.get("contract_name", ""),
        "contractLabel": grupo.get("contract_label", grupo["contract_code"]),
        "contract": grupo["contract_code"],
        "clientId": grupo["client_id"],
        "clientName": grupo["client_name"],
    }


def serializar_resumo_obrigacoes_fluxo(resumo):
    return {
        "plannedAmount": decimal_para_numero(resumo["planned_amount"]),
        "realizedAmount": decimal_para_numero(resumo["realized_amount"]),
        "paidAmount": decimal_para_numero(resumo["realized_amount"]),
        "overRealizedAmount": decimal_para_numero(resumo["over_realized_amount"]),
        "realizedAbovePlannedAmount": decimal_para_numero(
            resumo["over_realized_amount"]
        ),
        "pendingAmount": decimal_para_numero(resumo["pending_amount"]),
        "originRealizedAmount": decimal_para_numero(resumo["origin_realized_amount"]),
        "originPendingAmount": decimal_para_numero(resumo["origin_pending_amount"]),
        "originOverRealizedAmount": decimal_para_numero(
            resumo["origin_over_realized_amount"]
        ),
        "ledgerRealizedAmount": decimal_para_numero(resumo["ledger_realized_amount"]),
        "ledgerPendingAmount": decimal_para_numero(resumo["ledger_pending_amount"]),
        "ledgerOverRealizedAmount": decimal_para_numero(
            resumo["ledger_over_realized_amount"]
        ),
        "realizedAmountDifference": decimal_para_numero(
            resumo["realized_amount_difference"]
        ),
        "reconciledCount": resumo["reconciled_count"],
        "divergentCount": resumo["divergent_count"],
        "overdueAmount": decimal_para_numero(resumo["overdue_amount"]),
        "obligationsCount": resumo["count"],
        "pendingCount": resumo["pending_count"],
        "overdueCount": resumo["overdue_count"],
        "liquidatedCount": resumo["liquidated_count"],
        "ledgerPendingCount": resumo["ledger_pending_count"],
        "ledgerOverdueCount": resumo["ledger_overdue_count"],
        "ledgerLiquidatedCount": resumo["ledger_liquidated_count"],
        "ledgerOverdueAmount": decimal_para_numero(resumo["ledger_overdue_amount"]),
    }


def serializar_filtros_obrigacoes(filtros):
    status_liquidacao = (
        filtros.get("settlementStatus")
        or filtros.get("situacao")
        or filtros.get("status")
        or ""
    )
    start_date = filtros.get("startDate") or ""
    end_date = filtros.get("endDate") or ""
    event_id = "" if filtros.get("eventId") == "__invalid__" else filtros.get("eventId") or ""
    client_id = "" if filtros.get("clientId") == "__invalid__" else filtros.get("clientId") or ""
    contract_code_filter = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    contract_code = contract_code_filter
    contract_label = contract_code
    event_label = _rotulo_evento(event_id)
    client_label = _rotulo_cliente(client_id)

    payload = {
        "period": filtros.get("period") or "",
        "quickPeriod": filtros.get("quickPeriod") or "",
        "startDate": start_date,
        "endDate": end_date,
        "contractLabel": contract_label,
        "contractCode": contract_code,
        "eventId": event_id,
        "eventLabel": event_label,
        "clientId": client_id,
        "clientLabel": client_label,
        "source": filtros.get("source") or filtros.get("origin") or filtros.get("origem") or "",
        "sources": filtros.get("sources") or [],
        "cashFlowGroup": filtros.get("cashFlowGroup") or filtros.get("fluxo") or "",
        "nature": filtros.get("nature") or filtros.get("natureza") or "",
        "status": filtros.get("status") or "",
        "settlementStatus": status_liquidacao,
        "reconciliationStatus": filtros.get("reconciliationStatus") or "",
        "reconciliationDiagnosis": filtros.get("reconciliationDiagnosis") or "",
        "realizedAmountBasis": filtros.get("realizedAmountBasis") or "originState",
        "realizedAbovePlanned": filtros.get("realizedAbovePlanned") or "",
        "dataSource": filtros.get("dataSource") or "legacy",
        "obligationType": filtros.get("obligationType") or "",
        "search": filtros.get("search") or filtros.get("busca") or "",
        "queueFilter": filtros.get("queueFilter") or "all",
    }
    if filtros.get("overdueScope"):
        payload["overdueScope"] = filtros["overdueScope"]
    return payload

def _rotulo_evento(event_id):
    if not event_id:
        return ""

    evento = (
        Evento.objects.select_related("cliente", "orcamento")
        .filter(pk=event_id)
        .first()
    )
    if not evento:
        return ""

    return serializar_dimensao_operacional(evento)["eventLabel"]


def _rotulo_cliente(client_id):
    if not client_id:
        return ""

    cliente = Cliente.objects.filter(pk=client_id).first()
    if not cliente:
        return ""

    return serializar_cliente_operacional_opcao(cliente)["label"]


def serializar_opcoes_obrigacoes(filtros=None):
    filtros = filtros or {}
    tipo_obrigacao = filtros.get("obligationType") or "pagar"
    opcoes_dimensoes = _serializar_opcoes_dimensoes_operacionais()

    return {
        **opcoes_dimensoes,
        "sources": [
            {"value": origem, "label": rotulo}
            for origem, rotulo in fontes_obrigacoes_por_tipo(tipo_obrigacao).items()
        ],
        "cashFlowGroups": _copiar_opcoes(OPCOES_FLUXO_CAIXA_OBRIGACOES),
        "settlementStatuses": _copiar_opcoes(OPCOES_STATUS_LIQUIDACAO_OBRIGACOES),
        "reconciliationStatuses": _copiar_opcoes(OPCOES_STATUS_CONCILIACAO_OBRIGACOES),
        "reconciliationDiagnoses": [
            {"value": valor, "label": rotulo}
            for valor, rotulo in RECONCILIACAO_DIAGNOSTICOS.items()
            if valor != "conciliado"
        ],
        "realizedAmountBases": _copiar_opcoes(OPCOES_BASE_REALIZADO_OBRIGACOES),
        "realizedAbovePlannedStatuses": _copiar_opcoes(
            OPCOES_EXCEDENTE_REALIZADO_OBRIGACOES
        ),
        "obligationTypes": _copiar_opcoes(OPCOES_TIPO_OBRIGACAO),
        "dataSources": _copiar_opcoes(OPCOES_FONTE_DADOS_OBRIGACOES),
    }


def _copiar_opcoes(opcoes):
    return [dict(opcao) for opcao in opcoes]


def _serializar_opcoes_dimensoes_operacionais():
    opcoes = montar_opcoes_eventos_clientes_filtro()
    return serializar_opcoes_entidades_operacionais(
        opcoes,
        incluir_clientes=True,
        limite_contratos=80,
        limite_eventos=80,
        limite_clientes=120,
        event_description_format="iso",
    )


def fontes_obrigacoes_por_tipo(tipo_obrigacao):
    if tipo_obrigacao == "receber":
        return {
            origem: rotulo
            for origem, rotulo in FONTES_OBRIGACOES.items()
            if origem in {
                "receita_operacional",
                "investimento",
                "financiamento_movimentacao",
            }
        }

    return {
        origem: rotulo
        for origem, rotulo in FONTES_OBRIGACOES.items()
        if origem != "receita_operacional"
    }


def normalizar_reconciliation_status(valor):
    valor = str(valor or "").strip()
    if valor in {"conciliado", "divergente"}:
        return valor
    return ""


def normalizar_realized_amount_basis(valor):
    valor = str(valor or "").strip()
    if valor in {"ledger", "lancamento", "lancamentos", "LancamentoFinanceiro"}:
        return "ledger"
    return "originState"


def normalizar_reconciliation_diagnosis(valor):
    valor = str(valor or "").strip()
    diagnosticos = {
        "conciliado",
        "ledger_sem_lancamento",
        "origem_sem_realizado",
        "ledger_menor_que_origem",
        "ledger_maior_que_origem",
        "divergencia_valor",
    }
    return valor if valor in diagnosticos else ""


def normalizar_realized_above_planned_filter(valor):
    valor = str(valor or "").strip()
    if valor in {
        "1",
        "true",
        "sim",
        "yes",
        "with",
        "com",
        "com_excedente",
        "acima",
    }:
        return "with"
    if valor in {
        "0",
        "false",
        "nao",
        "no",
        "without",
        "sem",
        "sem_excedente",
    }:
        return "without"
    return ""


def normalizar_data_source_obrigacoes(valor):
    valor = str(valor or "").strip()
    if not valor:
        return "canonical"
    if valor in {
        "canonical",
        "canonico",
        "canonica",
        "modelagem_canonica",
        "canonicalWithFallback",
        "canonical_with_fallback",
    }:
        return "canonical"
    return "legacy"


def normalizar_tipo_obrigacao(valor):
    valor = str(valor or "").strip()
    if valor in {"pagar", "a_pagar", "conta_a_pagar", "saida"}:
        return "pagar"
    if valor in {"receber", "a_receber", "conta_a_receber", "entrada"}:
        return "receber"
    return ""


def normalizar_status_liquidacao_obrigacao(valor, tipo_obrigacao):
    valor = str(valor or "").strip().lower()
    if not valor:
        return ""
    if valor in STATUS_LIQUIDACAO_OBRIGACOES:
        return valor
    if tipo_obrigacao == "pagar" and valor == "pago":
        return "liquidado"
    if tipo_obrigacao == "receber" and valor == "recebido":
        return "liquidado"
    return valor


def avaliar_prontidao_canonica_obrigacoes(filtros=None):
    paridade = verificar_paridade_modelagem_financeira_canonica(limit=1)
    totais = _totais_paridade_canonica(paridade)
    reconciliacao = avaliar_reconciliacao_legado_para_leitura_canonica(filtros)
    ready = (
        paridade["consistent"]
        and totais["expected"] == totais["existing"]
        and reconciliacao["divergentCount"] == 0
    )
    if ready:
        reason = ""
    elif totais["missing"]:
        reason = "missing_canonical_records"
    elif totais["divergent"]:
        reason = "divergent_canonical_records"
    elif totais["extra"]:
        reason = "extra_canonical_records"
    elif reconciliacao["divergentCount"]:
        reason = "legacy_reconciliation_divergent"
    else:
        reason = "canonical_parity_not_ready"

    return {
        "readyForCanonicalReads": ready,
        "hasCanonicalParity": paridade["consistent"],
        "reason": reason,
        "totals": totais,
        "legacyReconciliation": reconciliacao,
    }


def avaliar_prontidao_canonica_visual_obrigacoes(filtros=None):
    registros_canonicos = contar_obrigacoes_financeiras_canonicas(filtros)
    ready = registros_canonicos > 0
    return {
        "readyForCanonicalReads": ready,
        "hasCanonicalParity": None,
        "reason": "" if ready else "missing_canonical_records",
        "totals": {
            "expected": 0,
            "existing": registros_canonicos,
            "missing": 0 if ready else 1,
            "divergent": 0,
            "extra": 0,
        },
        "legacyReconciliation": {
            "checked": False,
            "divergentCount": 0,
            "total": 0,
        },
        "mode": "visual_read",
    }


def avaliar_reconciliacao_legado_para_leitura_canonica(filtros=None):
    filtros_legados = dict(filtros or {})
    filtros_legados["dataSource"] = "legacy"
    itens = listar_obrigacoes_financeiras(filtros_legados)
    divergentes = [
        item for item in itens
        if item.get("reconciliation_status") == "divergente"
        or not item.get("is_ledger_reconciled", True)
    ]
    return {
        "checked": True,
        "divergentCount": len(divergentes),
        "total": len(itens),
    }


def _totais_paridade_canonica(paridade):
    grupos = (paridade["obrigacoes"], paridade["baixas"], paridade["alocacoes"])
    return {
        "expected": sum(grupo["expected"] for grupo in grupos),
        "existing": sum(grupo["existing"] for grupo in grupos),
        "missing": sum(grupo["missing"] for grupo in grupos),
        "divergent": sum(grupo["divergent"] for grupo in grupos),
        "extra": sum(grupo["extra"] for grupo in grupos),
    }


def normalizar_id(valor):
    valor = str(valor or "").strip()
    if not valor:
        return ""

    try:
        return str(int(valor))
    except (TypeError, ValueError):
        return "__invalid__"


def normalizar_inteiro(valor, padrao, minimo, maximo):
    try:
        inteiro = int(valor)
    except (TypeError, ValueError):
        return padrao

    return min(max(inteiro, minimo), maximo)


def serializar_data(valor):
    return valor.isoformat() if valor else ""


def decimal_para_numero(valor):
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor or "0"))

    return float(quantizar_moeda(valor))
