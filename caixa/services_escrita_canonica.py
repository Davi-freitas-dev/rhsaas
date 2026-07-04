from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .constants_financeiros import (
    STATUS_REALIZADO,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from .contracts_obrigacoes import (
    CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
    CANONICAL_SETTLEMENT_ADAPTERS,
    CANONICAL_WRITE_MODE_CANONICAL_FIRST,
    CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
    NATIVE_SETTLEMENT_CAPABILITIES,
)
from .models import (
    BaixaFinanceira,
    BaixaFinanceiraAlocacao,
    FONTE_ESCRITA_CANONICAL_FIRST,
    ORIGENS_BAIXA_FINANCEIRA,
    ObrigacaoFinanceira,
)
from .services_obrigacoes import (
    obter_booleano,
    obter_data_opcional,
    obter_decimal_obrigatorio,
    obter_texto,
)
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")


def liquidar_obrigacao_canonica_primeiro(source, source_id, payload, usuario):
    source = str(source or "").strip()
    if source not in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES:
        raise ValidationError(
            {
                "source": (
                    "Escrita canonical-first ainda nao esta liberada para esta origem."
                )
            }
        )

    from .services_obrigacoes import (  # import tardio para evitar ciclo.
        liquidar_obrigacao_financeira,
        validar_permissao_baixa_nativa,
    )

    validar_permissao_baixa_nativa(source, usuario)
    simulacao = simular_baixa_canonica_primeiro(source, source_id, payload)

    with transaction.atomic():
        baixa_pre_sincronizada = salvar_baixa_canonica_primeiro(
            simulacao,
            payload or {},
            usuario,
        )
        item = liquidar_obrigacao_financeira(source, source_id, payload, usuario)

    return {
        "item": item,
        "writeModelSource": CANONICAL_WRITE_MODE_CANONICAL_FIRST,
        "preSyncedSettlementId": (
            baixa_pre_sincronizada.id if baixa_pre_sincronizada else None
        ),
    }


def simular_baixa_canonica_primeiro(source, source_id, payload=None):
    payload = dict(payload or {})
    source = str(source or "").strip()
    source_id = normalizar_source_id(source_id)
    source_detail = obter_source_detail(source, payload)
    realized_amount = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_pago",
    )
    payment_date = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    settle_remaining = obter_booleano(
        payload,
        "settleRemainingBalance",
        "baixarSaldo",
        "baixar_saldo",
    )
    write_off_reason = obter_texto(
        payload,
        "writeOffReason",
        "motivoBaixa",
        "motivo_baixa",
    )
    notes = obter_texto(payload, "notes", "observacao") or ""

    validar_source_suportado(source, source_detail, settle_remaining)
    obrigacao = obter_obrigacao_canonica(source, source_id, source_detail)
    valores = calcular_valores_baixa(obrigacao, realized_amount)

    validar_payload_canonical_first(
        obrigacao,
        valores,
        payment_date,
        settle_remaining,
        write_off_reason,
    )

    adapter = CANONICAL_SETTLEMENT_ADAPTERS[source]
    return {
        "ready": True,
        "dryRun": True,
        "writeMode": "canonicalFirstDryRun",
        "currentWriteMode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "canonicalFirstReady": False,
        "source": source,
        "sourceId": source_id,
        "sourceDetail": source_detail,
        "obligationKey": obrigacao.chave_origem,
        "obligationId": obrigacao.id,
        "current": {
            "plannedAmount": decimal_para_numero(obrigacao.valor_previsto),
            "realizedAmount": decimal_para_numero(obrigacao.valor_realizado),
            "pendingAmount": decimal_para_numero(obrigacao.valor_pendente),
            "status": obrigacao.status,
        },
        "requested": {
            "realizedAmount": decimal_para_numero(realized_amount),
            "deltaAmount": decimal_para_numero(valores["delta"]),
            "settlementDate": payment_date.isoformat() if payment_date else "",
            "settleRemainingBalance": settle_remaining,
            "writeOffReason": write_off_reason or "",
            "notes": notes,
        },
        "canonicalSettlementDraft": montar_draft_baixa_canonica(
            obrigacao,
            valores["delta"],
            payment_date,
            adapter,
            notes,
        ),
        "canonicalAllocationDraft": {
            "obligationId": obrigacao.id,
            "obligationKey": obrigacao.chave_origem,
            "allocatedAmount": decimal_para_numero(valores["delta"]),
            "interestAmount": 0.0,
            "fineAmount": 0.0,
            "discountAmount": 0.0,
        },
        "legacyAdapter": {
            "name": adapter["legacyAdapter"],
            "mode": adapter["mode"],
            "wouldRunAfterCanonicalSettlement": valores["delta"] > ZERO,
        },
        "effects": {
            "wouldCreateCanonicalSettlement": valores["delta"] > ZERO,
            "wouldCreateCanonicalAllocation": valores["delta"] > ZERO,
            "wouldUpdateCanonicalObligation": True,
            "wouldCallLegacyAdapter": valores["delta"] > ZERO,
            "writesDatabase": False,
        },
    }


def normalizar_source_id(source_id):
    try:
        source_id = int(source_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"sourceId": "Informe uma origem valida."}) from exc

    if source_id <= 0:
        raise ValidationError({"sourceId": "Informe uma origem valida."})
    return source_id


def obter_source_detail(source, payload):
    source_detail = obter_texto(
        payload,
        "sourceDetail",
        "source_detail",
        "originDetail",
        "tipo",
        "tipoCustoServico",
        "tipo_custo_servico",
        "component",
        "componente",
    ) or ""
    capacidade = NATIVE_SETTLEMENT_CAPABILITIES.get(source) or {}
    if capacidade.get("requiresSourceDetail") and not source_detail:
        raise ValidationError(
            {"sourceDetail": "Informe o detalhe da origem para simular a baixa."}
        )
    accepted = set(capacidade.get("acceptedSourceDetails") or [])
    if source_detail and accepted and source_detail not in accepted:
        raise ValidationError({"sourceDetail": "Detalhe de origem invalido."})
    return source_detail


def validar_source_suportado(source, source_detail, settle_remaining):
    if source not in NATIVE_SETTLEMENT_CAPABILITIES:
        raise ValidationError({"source": "Origem não suporta baixa nativa."})
    capacidade = NATIVE_SETTLEMENT_CAPABILITIES[source]
    if settle_remaining and not capacidade.get("supportsWriteOff"):
        raise ValidationError(
            {
                "settleRemainingBalance": (
                    "Esta origem não suporta baixa do saldo restante."
                )
            }
        )
    if capacidade.get("requiresSourceDetail") and not source_detail:
        raise ValidationError({"sourceDetail": "Informe o detalhe da origem."})


def obter_obrigacao_canonica(source, source_id, source_detail):
    chave = montar_chave_obrigacao(source, source_id, source_detail)
    obrigacao = ObrigacaoFinanceira.objects.filter(chave_origem=chave).first()
    if not obrigacao:
        raise ValidationError(
            {"sourceId": "Obrigacao canonica nao encontrada para a origem."}
        )
    return obrigacao


def montar_chave_obrigacao(source, source_id, source_detail=""):
    if source == "custo_servico":
        return f"{source}:{source_id}:{source_detail}"
    return f"{source}:{source_id}"


def calcular_valores_baixa(obrigacao, realized_amount):
    realized_amount = quantizar_moeda(realized_amount)
    current_realized = quantizar_moeda(obrigacao.valor_realizado)
    return {
        "current": current_realized,
        "requested": realized_amount,
        "delta": quantizar_moeda(realized_amount - current_realized),
    }


def validar_payload_canonical_first(
    obrigacao,
    valores,
    payment_date,
    settle_remaining,
    write_off_reason,
):
    if valores["requested"] < valores["current"]:
        raise ValidationError(
            {
                "realizedAmount": (
                    "O valor realizado acumulado não pode ser menor que o valor já registrado."
                )
            }
        )

    if valores["requested"] > quantizar_moeda(obrigacao.valor_previsto):
        raise ValidationError(
            {"realizedAmount": "O valor realizado acumulado não pode superar o previsto."}
        )

    if valores["delta"] > ZERO and payment_date is None:
        raise ValidationError({"paymentDate": "Informe a data do pagamento."})

    if (
        settle_remaining
        and valores["requested"] < quantizar_moeda(obrigacao.valor_previsto)
        and not write_off_reason
    ):
        raise ValidationError(
            {"writeOffReason": "Informe o motivo para baixar o saldo restante."}
        )


def montar_draft_baixa_canonica(obrigacao, delta, payment_date, adapter, notes):
    tipo = (
        TIPO_FLUXO_ENTRADA
        if obrigacao.tipo == ObrigacaoFinanceira.TIPO_RECEBER
        else TIPO_FLUXO_SAIDA
    )
    return {
        "model": "BaixaFinanceira",
        "status": STATUS_REALIZADO,
        "type": tipo,
        "cashFlowGroup": obrigacao.fluxo,
        "nature": obrigacao.natureza,
        "amount": decimal_para_numero(delta),
        "date": payment_date.isoformat() if payment_date else "",
        "description": f"Baixa canonica simulada - {obrigacao.descricao}",
        "notes": notes,
        "canonicalSettlementOriginField": adapter["canonicalSettlementOriginField"],
        "contractCode": "",
        "eventId": obrigacao.evento_id,
        "clientId": obrigacao.cliente_id,
    }


def salvar_baixa_canonica_primeiro(simulacao, payload, usuario):
    valor_realizado = quantizar_moeda(
        Decimal(str(simulacao["requested"]["realizedAmount"]))
    )
    if valor_realizado <= ZERO:
        return None

    obrigacao = ObrigacaoFinanceira.objects.select_for_update().get(
        pk=simulacao["obligationId"]
    )
    data_baixa = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    forma_pagamento = obter_texto(
        payload,
        "paymentMethod",
        "formaPagamento",
        "forma_pagamento",
    ) or ""
    observacao = obter_texto(payload, "notes", "observacao") or ""
    adapter = CANONICAL_SETTLEMENT_ADAPTERS[simulacao["source"]]
    campo_origem_baixa = adapter["canonicalSettlementOriginField"]
    origem_defaults = {campo: None for campo in ORIGENS_BAIXA_FINANCEIRA}
    origem_defaults.pop(campo_origem_baixa, None)
    origem_defaults[f"{campo_origem_baixa}_id"] = simulacao["sourceId"]

    baixa, _ = BaixaFinanceira.objects.update_or_create(
        chave_origem=obrigacao.chave_origem,
        defaults={
            "tipo": TIPO_FLUXO_ENTRADA
            if obrigacao.tipo == ObrigacaoFinanceira.TIPO_RECEBER
            else TIPO_FLUXO_SAIDA,
            "fluxo": obrigacao.fluxo,
            "natureza": obrigacao.natureza,
            "valor_total": valor_realizado,
            "data_baixa": data_baixa,
            "forma_pagamento": forma_pagamento,
            "descricao": f"Baixa canonical-first - {obrigacao.descricao}",
            "observacao": observacao,
            "status": STATUS_REALIZADO,
            "fonte_escrita": FONTE_ESCRITA_CANONICAL_FIRST,
            "cliente_id": obrigacao.cliente_id,
            "evento_id": obrigacao.evento_id,
            "lancamento_financeiro": None,
            "atualizado_por": usuario,
            **origem_defaults,
        },
    )
    if usuario and not baixa.criado_por_id:
        baixa.criado_por = usuario
        baixa.save(update_fields=["criado_por", "atualizado_em"])

    BaixaFinanceiraAlocacao.objects.update_or_create(
        baixa=baixa,
        obrigacao=obrigacao,
        defaults={"valor_alocado": valor_realizado},
    )
    return baixa


def decimal_para_numero(valor):
    return float(quantizar_moeda(valor or ZERO))
