from django.conf import settings

from .constants_financeiros import TIPOS_CUSTO_SERVICO
from .selectors_obrigacoes import (
    FONTES_OBRIGACOES,
    ORIGEM_CUSTO_EXTRA,
    ORIGEM_CUSTO_FIXO,
    ORIGEM_CUSTO_SERVICO,
    ORIGEM_DESPESA_OPERACIONAL,
    ORIGEM_FINANCIAMENTO,
    ORIGEM_INVESTIMENTO,
    ORIGEM_PARCELA_DIVIDA,
)


PERMISSAO_VISUALIZAR_OBRIGACOES = "caixa.view_lancamentofinanceiro"
SETTLEMENT_CONTRACT_VERSION = "financial-obligations-settlement-v1"
REALIZED_AMOUNT_MODE_ACCUMULATED = "accumulated"
CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED = "legacyAdapterSynced"
CANONICAL_WRITE_MODE_CANONICAL_FIRST = "canonicalFirst"

BASE_SETTLEMENT_FIELDS = [
    "source",
    "sourceId",
    "realizedAmount",
    "paymentDate",
    "notes",
]
WRITE_OFF_FIELDS = ["settleRemainingBalance", "writeOffReason"]
PAYMENT_METHOD_FIELDS = ["paymentMethod"]
PAYMENT_DESCRIPTION_FIELDS = ["paymentDescription"]
PARCELA_ADJUSTMENT_FIELDS = ["interestAmount", "fineAmount", "discountAmount"]


def _capacidade(
    source,
    permission,
    *,
    supported_obligation_types=None,
    requires_source_detail=False,
    accepted_source_details=None,
    supports_payment_method=False,
    supports_payment_description=False,
    supports_write_off=True,
    supports_adjustments=False,
    adjustment_fields=None,
):
    accepted_fields = list(BASE_SETTLEMENT_FIELDS)
    if requires_source_detail:
        accepted_fields.append("sourceDetail")
    if supports_payment_method:
        accepted_fields.extend(PAYMENT_METHOD_FIELDS)
    if supports_payment_description:
        accepted_fields.extend(PAYMENT_DESCRIPTION_FIELDS)
    if supports_write_off:
        accepted_fields.extend(WRITE_OFF_FIELDS)
    if supports_adjustments:
        accepted_fields.extend(adjustment_fields or [])

    return {
        "source": source,
        "label": FONTES_OBRIGACOES[source],
        "nativeSettlement": True,
        "supportsNativeSettlement": True,
        "permission": permission,
        "supportedObligationTypes": list(supported_obligation_types or ["pagar"]),
        "realizedAmountMode": REALIZED_AMOUNT_MODE_ACCUMULATED,
        "requiresSourceDetail": requires_source_detail,
        "acceptedSourceDetails": list(accepted_source_details or []),
        "supportsPaymentMethod": supports_payment_method,
        "supportsPaymentDescription": supports_payment_description,
        "supportsWriteOff": supports_write_off,
        "supportsAdjustments": supports_adjustments,
        "adjustmentFields": list(adjustment_fields or []),
        "acceptedFields": accepted_fields,
    }


NATIVE_SETTLEMENT_CAPABILITIES = {
    ORIGEM_DESPESA_OPERACIONAL: _capacidade(
        ORIGEM_DESPESA_OPERACIONAL,
        "caixa.change_despesaoperacional",
        supports_payment_method=True,
    ),
    ORIGEM_CUSTO_FIXO: _capacidade(
        ORIGEM_CUSTO_FIXO,
        "caixa.change_custofixo",
    ),
    ORIGEM_CUSTO_EXTRA: _capacidade(
        ORIGEM_CUSTO_EXTRA,
        "caixa.add_pagamentoeventocustoextra",
        supports_payment_description=True,
    ),
    ORIGEM_CUSTO_SERVICO: _capacidade(
        ORIGEM_CUSTO_SERVICO,
        "caixa.add_pagamentoeventocustoservico",
        requires_source_detail=True,
        accepted_source_details=TIPOS_CUSTO_SERVICO.keys(),
        supports_payment_description=True,
    ),
    ORIGEM_PARCELA_DIVIDA: _capacidade(
        ORIGEM_PARCELA_DIVIDA,
        "caixa.add_pagamentoparceladivida",
        supports_payment_method=True,
        supports_adjustments=True,
        adjustment_fields=PARCELA_ADJUSTMENT_FIELDS,
    ),
    ORIGEM_INVESTIMENTO: _capacidade(
        ORIGEM_INVESTIMENTO,
        "caixa.change_investimento",
    ),
    ORIGEM_FINANCIAMENTO: _capacidade(
        ORIGEM_FINANCIAMENTO,
        "caixa.change_financiamentomovimentacao",
        supports_write_off=False,
    ),
}

CANONICAL_SETTLEMENT_ADAPTERS = {
    ORIGEM_DESPESA_OPERACIONAL: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_despesa_operacional_manual",
        "canonicalObligationSource": ORIGEM_DESPESA_OPERACIONAL,
        "canonicalSettlementOriginField": "despesa_operacional",
        "requiresSourceDetail": False,
        "canonicalFirstReady": False,
    },
    ORIGEM_CUSTO_FIXO: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_custo_fixo",
        "canonicalObligationSource": ORIGEM_CUSTO_FIXO,
        "canonicalSettlementOriginField": "custo_fixo",
        "requiresSourceDetail": False,
        "canonicalFirstReady": False,
    },
    ORIGEM_CUSTO_EXTRA: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_custo_extra_evento",
        "canonicalObligationSource": ORIGEM_CUSTO_EXTRA,
        "canonicalSettlementOriginField": "pagamento_custo_extra",
        "requiresSourceDetail": False,
        "canonicalFirstReady": False,
    },
    ORIGEM_CUSTO_SERVICO: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_custo_servico_evento",
        "canonicalObligationSource": ORIGEM_CUSTO_SERVICO,
        "canonicalSettlementOriginField": "pagamento_custo_servico",
        "requiresSourceDetail": True,
        "canonicalFirstReady": False,
    },
    ORIGEM_PARCELA_DIVIDA: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_parcela_divida_fcf",
        "canonicalObligationSource": ORIGEM_PARCELA_DIVIDA,
        "canonicalSettlementOriginField": "pagamento_parcela_divida",
        "requiresSourceDetail": False,
        "canonicalFirstReady": False,
    },
    ORIGEM_INVESTIMENTO: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_investimento_fci",
        "canonicalObligationSource": ORIGEM_INVESTIMENTO,
        "canonicalSettlementOriginField": "investimento",
        "requiresSourceDetail": False,
        "canonicalFirstReady": False,
    },
    ORIGEM_FINANCIAMENTO: {
        "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "legacyAdapter": "liquidar_financiamento_fcf",
        "canonicalObligationSource": ORIGEM_FINANCIAMENTO,
        "canonicalSettlementOriginField": "financiamento_movimentacao",
        "requiresSourceDetail": False,
        "canonicalFirstReady": False,
    },
}

READ_ONLY_SETTLEMENT_SOURCES = ()
SUPPORTED_NATIVE_SETTLEMENT_SOURCES = frozenset(NATIVE_SETTLEMENT_CAPABILITIES)
CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES = frozenset(
    (
        ORIGEM_DESPESA_OPERACIONAL,
        ORIGEM_CUSTO_FIXO,
        ORIGEM_INVESTIMENTO,
        ORIGEM_FINANCIAMENTO,
    )
)
PERMISSOES_BAIXA_NATIVA = {
    source: capacidade["permission"]
    for source, capacidade in NATIVE_SETTLEMENT_CAPABILITIES.items()
}


def serializar_adapters_baixa_canonica():
    return {
        source: {
            **adapter,
            "supportsCanonicalFirstWrite": source
            in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
            "supportedObligationTypes": list(
                NATIVE_SETTLEMENT_CAPABILITIES.get(source, {}).get(
                    "supportedObligationTypes", []
                )
            ),
        }
        for source, adapter in CANONICAL_SETTLEMENT_ADAPTERS.items()
    }


def serializar_contrato_baixa_obrigacoes():
    fontes = {
        source: _serializar_capacidade_baixa(capacidade)
        for source, capacidade in NATIVE_SETTLEMENT_CAPABILITIES.items()
    }
    ativacao_canonical_first = estado_ativacao_canonical_first()

    for source in READ_ONLY_SETTLEMENT_SOURCES:
        fontes[source] = {
            "source": source,
            "label": FONTES_OBRIGACOES[source],
            "nativeSettlement": False,
            "supportsNativeSettlement": False,
            "supportedObligationTypes": [],
            "realizedAmountMode": REALIZED_AMOUNT_MODE_ACCUMULATED,
            "requiresSourceDetail": False,
            "acceptedSourceDetails": [],
            "supportsPaymentMethod": False,
            "supportsPaymentDescription": False,
            "supportsWriteOff": False,
            "supportsAdjustments": False,
            "supportsCanonicalFirstWrite": False,
            "adjustmentFields": [],
            "acceptedFields": [],
        }

    return {
        "version": SETTLEMENT_CONTRACT_VERSION,
        "realizedAmountMode": REALIZED_AMOUNT_MODE_ACCUMULATED,
        "canonicalSettlement": {
            "mode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
            "writeModelSource": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
            "obligationModel": "ObrigacaoFinanceira",
            "settlementModel": "BaixaFinanceira",
            "allocationModel": "BaixaFinanceiraAlocacao",
            "apiResponseField": "canonicalSettlement",
            "canonicalFirstReady": False,
            "canonicalFirstDirectSources": list(
                CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
            ),
            "canonicalFirstActivation": ativacao_canonical_first,
            "adapters": serializar_adapters_baixa_canonica(),
        },
        "nativeSources": list(NATIVE_SETTLEMENT_CAPABILITIES.keys()),
        "readOnlySources": list(READ_ONLY_SETTLEMENT_SOURCES),
        "sources": fontes,
    }


def serializar_contrato_baixa_obrigacoes_usuario(usuario=None):
    contrato = serializar_contrato_baixa_obrigacoes()

    for source, capacidade_serializada in contrato["sources"].items():
        capacidade = NATIVE_SETTLEMENT_CAPABILITIES.get(source) or {}
        permissao = capacidade.get("permission")
        pode_baixar = bool(usuario and permissao and usuario.has_perm(permissao))
        capacidade_serializada["canSettle"] = pode_baixar
        capacidade_serializada["canUseNativeSettlement"] = pode_baixar

    return contrato


def _serializar_capacidade_baixa(capacidade):
    serializada = {
        chave: valor
        for chave, valor in capacidade.items()
        if chave != "permission"
    }
    serializada["supportsCanonicalFirstWrite"] = (
        capacidade["source"] in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
    )
    return serializada


def estado_ativacao_canonical_first():
    feature_flag_enabled = bool(
        getattr(settings, "CANONICAL_FIRST_SETTLEMENT_ENABLED", False)
    )
    feature_flag_sources = set(
        getattr(settings, "CANONICAL_FIRST_SETTLEMENT_SOURCES", [])
    )
    invalid_sources = feature_flag_sources - CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
    enabled_sources = (
        feature_flag_sources & CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
        if feature_flag_enabled
        else set()
    )

    return {
        "featureFlagEnabled": feature_flag_enabled,
        "featureFlagSources": sorted(feature_flag_sources),
        "enabledSources": sorted(enabled_sources),
        "invalidSources": sorted(invalid_sources),
        "directSources": sorted(CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES),
    }
