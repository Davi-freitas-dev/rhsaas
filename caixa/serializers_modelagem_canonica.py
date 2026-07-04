from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from .constants_nomenclatura import montar_metadados_nomenclatura_financeira
from .models import (
    BaixaFinanceira,
    BaixaFinanceiraAlocacao,
    FONTE_ESCRITA_BAIXA_CHOICES,
    ObrigacaoFinanceira,
)
from .selectors_opcoes_filtros import montar_opcoes_eventos_clientes_filtro
from .serializers_dimensoes_operacionais import serializar_opcoes_entidades_operacionais
from .services_dimensoes_operacionais import (
    relacao_carregada,
    relacoes_multiplas_carregadas,
    serializar_dimensao_operacional_financeira,
)
from .services_modelagem_canonica import (
    sincronizar_modelagem_financeira_canonica,
    verificar_paridade_modelagem_financeira_canonica,
)
from .utils_contratos import (
    montar_filtro_evento_ou_orcamento_por_contrato_visual,
    normalizar_codigo_contrato_visual,
)
from .utils_financeiros import quantizar_moeda
from .utils_periodos import resolver_intervalo_periodo_canonico


LIMITE_ISSUES_PADRAO = 20
LIMITE_ISSUES_MAXIMO = 200
LIMITE_BAIXAS_PADRAO = 100
LIMITE_BAIXAS_MAXIMO = 300

ORIGENS_BAIXA_CANONICA = {
    "receita_operacional": "receita_operacional",
    "despesa_operacional": "despesa_operacional",
    "custo_fixo": "custo_fixo",
    "custo_servico": "pagamento_custo_servico",
    "custo_extra": "pagamento_custo_extra",
    "parcela_divida": "pagamento_parcela_divida",
    "investimento": "investimento",
    "financiamento_movimentacao": "financiamento_movimentacao",
}
ROTULOS_ORIGENS_BAIXA_CANONICA = {
    "receita_operacional": "Receita operacional",
    "despesa_operacional": "Despesa operacional manual",
    "custo_fixo": "Custo fixo",
    "custo_servico": "Custo de serviço",
    "custo_extra": "Custo extra do evento",
    "parcela_divida": "Parcela FCF",
    "investimento": "Investimento",
    "financiamento_movimentacao": "Movimentação de financiamento",
}
FONTES_ESCRITA_BAIXA_CANONICA = {
    valor for valor, _rotulo in FONTE_ESCRITA_BAIXA_CHOICES
}


def montar_payload_modelagem_financeira_canonica_api(params=None):
    params = params or {}
    limit = normalizar_inteiro(
        params.get("limit") or params.get("issueLimit"),
        LIMITE_ISSUES_PADRAO,
        1,
        LIMITE_ISSUES_MAXIMO,
    )
    sincronizacao = sincronizar_modelagem_financeira_canonica(aplicar=False)
    paridade = verificar_paridade_modelagem_financeira_canonica(limit=limit)
    status = serializar_status_canonico(sincronizacao, paridade)

    return {
        "data": {
            "status": status,
            "synchronizationPreview": sincronizacao,
            "syncPreview": sincronizacao,
            "parity": paridade,
            "canonicalTotals": serializar_totais_canonicos(),
            "nomenclature": montar_metadados_nomenclatura_financeira(),
            "migrationPolicy": {
                "legacyWritePathsActive": True,
                "canonicalWritePathsActive": False,
                "canonicalReadsRecommended": status["readyForCanonicalReads"],
                "requiresExplicitApply": True,
                "applyCommand": (
                    "python manage.py sincronizar_modelagem_financeira_canonica "
                    "--aplicar"
                ),
                "verifyCommand": (
                    "python manage.py verificar_paridade_modelagem_canonica --falhar"
                ),
            },
            "meta": {
                "generatedAt": timezone.now().isoformat(),
                "source": "backend",
                "readOnly": True,
                "currency": "BRL",
            },
        }
    }


def montar_payload_baixas_financeiras_canonicas_api(params=None):
    filtros = normalizar_filtros_baixas_canonicas(params)
    itens = listar_baixas_financeiras_canonicas(filtros)
    total_registros = len(itens)
    limit = normalizar_inteiro(
        filtros.get("limit"),
        LIMITE_BAIXAS_PADRAO,
        1,
        LIMITE_BAIXAS_MAXIMO,
    )
    offset = normalizar_inteiro(filtros.get("offset"), 0, 0, total_registros)
    itens_paginados = itens[offset:offset + limit]

    return {
        "data": {
            "items": itens_paginados,
            "summary": serializar_resumo_baixas_canonicas(itens),
            "filters": serializar_filtros_baixas_canonicas(filtros),
            "filterOptions": {
                **serializar_opcoes_dimensoes_operacionais_canonicas(),
                "types": [
                    {"value": "entrada", "label": "Entrada"},
                    {"value": "saida", "label": "Saída"},
                ],
                "cashFlowGroups": [
                    {"value": "fco", "label": "FCO"},
                    {"value": "fci", "label": "FCI"},
                    {"value": "fcf", "label": "FCF"},
                ],
                "sources": [
                    {
                        "value": origem,
                        "label": rotulo_origem_baixa_canonica(origem),
                    }
                    for origem in ORIGENS_BAIXA_CANONICA
                ],
                "writeModelSources": [
                    {"value": valor, "label": rotulo}
                    for valor, rotulo in FONTE_ESCRITA_BAIXA_CHOICES
                ],
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_registros,
                "hasMore": offset + limit < total_registros,
            },
            "meta": {
                "generatedAt": timezone.now().isoformat(),
                "source": "backend",
                "readOnly": True,
                "currency": "BRL",
                "dateBasis": "settlementDate",
                "model": "BaixaFinanceira",
                "allocationModel": "BaixaFinanceiraAlocacao",
            },
        }
    }


def serializar_opcoes_dimensoes_operacionais_canonicas():
    opcoes = montar_opcoes_eventos_clientes_filtro()
    return serializar_opcoes_entidades_operacionais(
        opcoes,
        incluir_clientes=True,
        limite_contratos=80,
        limite_eventos=80,
        limite_clientes=120,
        event_description_format="iso",
    )


def listar_baixas_financeiras_canonicas(filtros):
    if _filtro_operacional_invalido(filtros):
        return []

    query = (
        BaixaFinanceira.objects.select_related(
            "cliente",
            "evento",
            "evento__orcamento",
            "lancamento_financeiro",
            "receita_operacional",
            "despesa_operacional",
            "custo_fixo",
            "pagamento_custo_servico",
            "pagamento_custo_servico__custo_servico",
            "pagamento_custo_extra",
            "pagamento_custo_extra__custo_extra",
            "pagamento_parcela_divida",
            "pagamento_parcela_divida__parcela",
            "investimento",
            "financiamento_movimentacao",
        )
        .prefetch_related(
            "alocacoes__obrigacao",
            "alocacoes__obrigacao__cliente",
            "alocacoes__obrigacao__evento",
            "alocacoes__obrigacao__evento__orcamento",
        )
        .all()
    )
    query = aplicar_filtros_baixas_canonicas(query, filtros)

    return [
        serializar_baixa_financeira_canonica(baixa)
        for baixa in query
    ]


def aplicar_filtros_baixas_canonicas(query, filtros):
    data_inicial = filtros.get("startDate") or filtros.get("data_inicial")
    data_final = filtros.get("endDate") or filtros.get("data_final")
    tipo = filtros.get("type") or filtros.get("tipo")
    fluxo = filtros.get("cashFlowGroup") or filtros.get("fluxo")
    natureza = filtros.get("nature") or filtros.get("natureza")
    status = filtros.get("status")
    contract_code = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    event_id = filtros.get("eventId")
    client_id = filtros.get("clientId")
    origem = filtros.get("source") or filtros.get("origin") or filtros.get("origem")
    fonte_escrita = (
        filtros.get("writeModelSource")
        or filtros.get("write_model_source")
        or filtros.get("fonteEscrita")
        or filtros.get("fonte_escrita")
    )
    search = (filtros.get("search") or filtros.get("busca") or "").strip()

    if data_inicial:
        query = query.filter(data_baixa__gte=data_inicial)
    if data_final:
        query = query.filter(data_baixa__lte=data_final)
    if tipo in {"entrada", "saida"}:
        query = query.filter(tipo=tipo)
    if fluxo:
        query = query.filter(fluxo=fluxo)
    if natureza:
        query = query.filter(natureza=natureza)
    if status:
        query = query.filter(status=status)
    if contract_code:
        query = query.filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "evento__",
                contract_code,
            )
        )
    if event_id:
        query = query.filter(evento_id=event_id)
    if client_id:
        query = query.filter(cliente_id=client_id)
    if origem in ORIGENS_BAIXA_CANONICA:
        query = query.filter(**{f"{ORIGENS_BAIXA_CANONICA[origem]}__isnull": False})
    if fonte_escrita in FONTES_ESCRITA_BAIXA_CANONICA:
        query = query.filter(fonte_escrita=fonte_escrita)
    if search:
        query = query.filter(
            Q(chave_origem__icontains=search)
            | Q(descricao__icontains=search)
            | Q(observacao__icontains=search)
            | Q(cliente__nome_razao_social__icontains=search)
            | Q(evento__orcamento__numero__icontains=search)
            | Q(evento__nome_evento__icontains=search)
            | Q(evento__numero__icontains=search)
        )

    return query.order_by("-data_baixa", "-id")


def serializar_baixa_financeira_canonica(baixa):
    origem = _origem_baixa_canonica(baixa)
    dimensao = serializar_dimensao_operacional_financeira(baixa)
    alocacoes = [
        serializar_alocacao_baixa_canonica(alocacao)
        for alocacao in relacoes_multiplas_carregadas(baixa, "alocacoes")
    ]
    valor_alocado = quantizar_moeda(
        sum((Decimal(str(item["allocatedAmount"])) for item in alocacoes), Decimal("0.00"))
    )

    valor_baixa = decimal_para_numero(baixa.valor_baixa)

    return {
        "id": baixa.id,
        "key": baixa.chave_origem,
        "date": baixa.data_baixa.isoformat() if baixa.data_baixa else "",
        "settlementDate": baixa.data_baixa.isoformat() if baixa.data_baixa else "",
        "type": baixa.tipo,
        "tipo": baixa.tipo,
        "typeLabel": baixa.get_tipo_display(),
        "cashFlowGroup": baixa.fluxo,
        "fluxo": baixa.fluxo,
        "nature": baixa.natureza,
        "natureza": baixa.natureza,
        "amount": valor_baixa,
        "settlementAmount": valor_baixa,
        "valorBaixa": valor_baixa,
        "valor_baixa": valor_baixa,
        "valorTotal": valor_baixa,
        "allocatedAmount": decimal_para_numero(valor_alocado),
        "unallocatedAmount": decimal_para_numero(
            max(quantizar_moeda(baixa.valor_total - valor_alocado), Decimal("0.00"))
        ),
        "paymentMethod": baixa.forma_pagamento,
        "description": baixa.descricao,
        "settlementDescription": baixa.descricao,
        "descricao": baixa.descricao,
        "notes": baixa.observacao,
        "status": baixa.status,
        "statusLabel": baixa.get_status_display(),
        "writeModelSource": baixa.fonte_escrita,
        "fonteEscrita": baixa.fonte_escrita,
        "source": origem["source"],
        "origin": origem["source"],
        "origem": origem["source"],
        "sourceId": origem["sourceId"],
        "originId": origem["sourceId"],
        "sourceDetail": origem["sourceDetail"],
        "sourceLabel": origem["sourceLabel"],
        "clientId": dimensao["clientId"] or baixa.cliente_id,
        "clientName": dimensao["clientName"],
        "cliente_id": dimensao["clientId"] or baixa.cliente_id,
        "cliente_nome": dimensao["clientName"],
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "contractLabel": dimensao["contractLabel"],
        "contrato_codigo": dimensao["contractCode"],
        "eventId": dimensao["eventId"] or baixa.evento_id,
        "eventName": dimensao["eventName"],
        "eventNumber": dimensao["eventNumber"],
        "eventLabel": dimensao["eventLabel"],
        "evento_id": dimensao["eventId"] or baixa.evento_id,
        "evento_nome": dimensao["eventName"],
        "evento_numero": dimensao["eventNumber"],
        "evento_label": dimensao["eventLabel"],
        "ledgerEntryId": baixa.lancamento_financeiro_id,
        "allocations": alocacoes,
        "allocationCount": len(alocacoes),
    }


def serializar_alocacao_baixa_canonica(alocacao):
    obrigacao = relacao_carregada(alocacao, "obrigacao")
    origem = (
        _origem_obrigacao_canonica(obrigacao)
        if obrigacao is not None
        else {
            "source": "",
            "sourceId": None,
            "sourceDetail": "",
            "sourceLabel": "",
        }
    )
    dimensao = serializar_dimensao_operacional_financeira(obrigacao)
    due_date = getattr(obrigacao, "data_vencimento", None)
    return {
        "id": alocacao.id,
        "obligationId": alocacao.obrigacao_id,
        "obligationKey": getattr(obrigacao, "chave_origem", ""),
        "source": origem["source"],
        "sourceId": origem["sourceId"],
        "sourceDetail": origem["sourceDetail"],
        "sourceLabel": origem["sourceLabel"],
        "description": getattr(obrigacao, "descricao", ""),
        "obligationDescription": getattr(obrigacao, "descricao", ""),
        "dueDate": due_date.isoformat() if due_date else "",
        "allocatedAmount": decimal_para_numero(alocacao.valor_alocado),
        "interestAmount": decimal_para_numero(alocacao.valor_juros),
        "fineAmount": decimal_para_numero(alocacao.valor_multa),
        "discountAmount": decimal_para_numero(alocacao.valor_desconto),
        "clientId": dimensao["clientId"] or getattr(obrigacao, "cliente_id", None),
        "clientName": dimensao["clientName"],
        "cliente_id": dimensao["clientId"] or getattr(obrigacao, "cliente_id", None),
        "cliente_nome": dimensao["clientName"],
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "contractLabel": dimensao["contractLabel"],
        "contrato_codigo": dimensao["contractCode"],
        "eventId": dimensao["eventId"] or getattr(obrigacao, "evento_id", None),
        "eventName": dimensao["eventName"],
        "eventNumber": dimensao["eventNumber"],
        "eventLabel": dimensao["eventLabel"],
        "evento_id": dimensao["eventId"] or getattr(obrigacao, "evento_id", None),
        "evento_nome": dimensao["eventName"],
        "evento_numero": dimensao["eventNumber"],
        "evento_label": dimensao["eventLabel"],
    }


def serializar_resumo_baixas_canonicas(itens):
    entradas = Decimal("0.00")
    saidas = Decimal("0.00")
    alocado = Decimal("0.00")
    nao_alocado = Decimal("0.00")
    por_fluxo = {}
    por_origem = {}
    por_fonte_escrita = {}

    for item in itens:
        valor = Decimal(str(item["amount"]))
        valor_alocado = Decimal(str(item["allocatedAmount"]))
        valor_nao_alocado = Decimal(str(item["unallocatedAmount"]))
        if item["type"] == "entrada":
            entradas += valor
        else:
            saidas += valor
        alocado += valor_alocado
        nao_alocado += valor_nao_alocado
        _somar_grupo_baixa(por_fluxo, item["cashFlowGroup"], item)
        _somar_grupo_baixa(por_origem, item["source"], item)
        _somar_grupo_baixa(por_fonte_escrita, item["writeModelSource"], item)

    return {
        "count": len(itens),
        "inflowAmount": decimal_para_numero(entradas),
        "outflowAmount": decimal_para_numero(saidas),
        "financialResult": decimal_para_numero(entradas - saidas),
        "allocatedAmount": decimal_para_numero(alocado),
        "unallocatedAmount": decimal_para_numero(nao_alocado),
        "byCashFlowGroup": {
            chave: serializar_grupo_baixa_canonica(valor)
            for chave, valor in sorted(por_fluxo.items())
        },
        "bySource": {
            chave: serializar_grupo_baixa_canonica(valor)
            for chave, valor in sorted(por_origem.items())
        },
        "byWriteModelSource": {
            chave: serializar_grupo_baixa_canonica(valor)
            for chave, valor in sorted(por_fonte_escrita.items())
        },
    }


def _somar_grupo_baixa(grupos, chave, item):
    grupo = grupos.setdefault(
        chave or "",
        {
            "count": 0,
            "inflowAmount": Decimal("0.00"),
            "outflowAmount": Decimal("0.00"),
            "allocatedAmount": Decimal("0.00"),
            "unallocatedAmount": Decimal("0.00"),
        },
    )
    valor = Decimal(str(item["amount"]))
    if item["type"] == "entrada":
        grupo["inflowAmount"] += valor
    else:
        grupo["outflowAmount"] += valor
    grupo["count"] += 1
    grupo["allocatedAmount"] += Decimal(str(item["allocatedAmount"]))
    grupo["unallocatedAmount"] += Decimal(str(item["unallocatedAmount"]))


def serializar_grupo_baixa_canonica(grupo):
    return {
        "count": grupo["count"],
        "inflowAmount": decimal_para_numero(grupo["inflowAmount"]),
        "outflowAmount": decimal_para_numero(grupo["outflowAmount"]),
        "financialResult": decimal_para_numero(
            grupo["inflowAmount"] - grupo["outflowAmount"]
        ),
        "allocatedAmount": decimal_para_numero(grupo["allocatedAmount"]),
        "unallocatedAmount": decimal_para_numero(grupo["unallocatedAmount"]),
    }


def normalizar_filtros_baixas_canonicas(params):
    params = dict(params.items()) if hasattr(params, "items") else dict(params or {})
    periodo = resolver_intervalo_periodo_canonico(params)

    filtros = {
        "period": periodo["period"],
        "quickPeriod": periodo["quickPeriod"],
        "startDate": periodo["startDate"],
        "data_inicial": periodo["startDate"],
        "endDate": periodo["endDate"],
        "data_final": periodo["endDate"],
        "limit": params.get("limit"),
        "offset": params.get("offset"),
    }
    filtros["contractCode"] = normalizar_codigo_contrato_visual(params.get("contractCode"))
    filtros["contrato_codigo"] = filtros["contractCode"]
    filtros["eventId"] = normalizar_id(params.get("eventId"))
    filtros["clientId"] = normalizar_id(params.get("clientId"))
    filtros["source"] = params.get("source") or ""
    filtros["type"] = params.get("type") or ""
    filtros["cashFlowGroup"] = params.get("cashFlowGroup") or ""
    filtros["nature"] = params.get("nature") or ""
    filtros["status"] = params.get("status") or ""
    filtros["writeModelSource"] = params.get("writeModelSource") or ""
    filtros["fonteEscrita"] = filtros["writeModelSource"]
    filtros["write_model_source"] = filtros["writeModelSource"]
    filtros["fluxo"] = filtros["cashFlowGroup"]
    filtros["tipo"] = filtros["type"]
    filtros["natureza"] = filtros["nature"]
    filtros["search"] = params.get("search") or ""
    filtros["busca"] = filtros["search"]
    return filtros


def serializar_filtros_baixas_canonicas(filtros):
    period = filtros.get("period") or ""
    start_date = filtros.get("startDate") or ""
    end_date = filtros.get("endDate") or ""
    contract_code = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    event_id = "" if filtros.get("eventId") == "__invalid__" else filtros.get("eventId") or ""
    client_id = "" if filtros.get("clientId") == "__invalid__" else filtros.get("clientId") or ""
    source = filtros.get("source") or ""
    tipo = filtros.get("type") or ""
    cash_flow_group = filtros.get("cashFlowGroup") or ""
    nature = filtros.get("nature") or ""
    status = filtros.get("status") or ""
    write_model_source = filtros.get("writeModelSource") or ""
    search = filtros.get("search") or ""

    return {
        "period": period,
        "quickPeriod": filtros.get("quickPeriod") or "",
        "startDate": start_date,
        "endDate": end_date,
        "contractCode": contract_code,
        "eventId": event_id,
        "clientId": client_id,
        "source": source,
        "type": tipo,
        "cashFlowGroup": cash_flow_group,
        "nature": nature,
        "status": status,
        "writeModelSource": write_model_source,
        "search": search,
    }


def _origem_baixa_canonica(baixa):
    if baixa.receita_operacional_id:
        return _dados_origem("receita_operacional", baixa.receita_operacional_id)
    if baixa.despesa_operacional_id:
        return _dados_origem("despesa_operacional", baixa.despesa_operacional_id)
    if baixa.custo_fixo_id:
        return _dados_origem("custo_fixo", baixa.custo_fixo_id)
    if baixa.pagamento_custo_servico_id:
        pagamento = relacao_carregada(baixa, "pagamento_custo_servico")
        return _dados_origem(
            "custo_servico",
            getattr(pagamento, "custo_servico_id", None),
            getattr(pagamento, "tipo", ""),
        )
    if baixa.pagamento_custo_extra_id:
        pagamento = relacao_carregada(baixa, "pagamento_custo_extra")
        return _dados_origem(
            "custo_extra",
            getattr(pagamento, "custo_extra_id", None),
        )
    if baixa.pagamento_parcela_divida_id:
        pagamento = relacao_carregada(baixa, "pagamento_parcela_divida")
        return _dados_origem(
            "parcela_divida",
            getattr(pagamento, "parcela_id", None),
        )
    if baixa.investimento_id:
        return _dados_origem("investimento", baixa.investimento_id)
    if baixa.financiamento_movimentacao_id:
        return _dados_origem(
            "financiamento_movimentacao",
            baixa.financiamento_movimentacao_id,
        )
    return _dados_origem("", None)


def _origem_obrigacao_canonica(obrigacao):
    source_id = None
    if obrigacao.receita_operacional_id:
        source_id = obrigacao.receita_operacional_id
    elif obrigacao.despesa_operacional_id:
        source_id = obrigacao.despesa_operacional_id
    elif obrigacao.custo_fixo_id:
        source_id = obrigacao.custo_fixo_id
    elif obrigacao.evento_custo_servico_id:
        source_id = obrigacao.evento_custo_servico_id
    elif obrigacao.evento_custo_extra_id:
        source_id = obrigacao.evento_custo_extra_id
    elif obrigacao.parcela_divida_id:
        source_id = obrigacao.parcela_divida_id
    elif obrigacao.investimento_id:
        source_id = obrigacao.investimento_id
    elif obrigacao.financiamento_movimentacao_id:
        source_id = obrigacao.financiamento_movimentacao_id
    return _dados_origem(obrigacao.origem, source_id, obrigacao.detalhe_origem)


def _dados_origem(source, source_id, source_detail=""):
    return {
        "source": source or "",
        "sourceId": source_id,
        "sourceDetail": source_detail or "",
        "sourceLabel": rotulo_origem_baixa_canonica(source),
    }


def rotulo_origem_baixa_canonica(source):
    return ROTULOS_ORIGENS_BAIXA_CANONICA.get(source or "", "")


def _filtro_operacional_invalido(filtros):
    return any(
        filtros.get(nome) == "__invalid__"
        for nome in ("eventId", "clientId")
    )


def normalizar_id(valor):
    valor = str(valor or "").strip()
    if not valor:
        return ""

    try:
        return str(int(valor))
    except (TypeError, ValueError):
        return "__invalid__"


def serializar_status_canonico(sincronizacao, paridade):
    totais = _totais_paridade(paridade)
    consistent = paridade["consistent"]
    has_expected_records = totais["expected"] > 0
    has_canonical_records = totais["existing"] > 0
    has_missing_records = totais["missing"] > 0
    has_divergent_records = totais["divergent"] > 0
    has_extra_records = totais["extra"] > 0
    ready = consistent and (has_canonical_records or not has_expected_records)

    if not has_expected_records:
        next_action = "no_business_data"
    elif not has_canonical_records and has_missing_records:
        next_action = "apply_canonical_sync"
    elif has_missing_records:
        next_action = "complete_canonical_sync"
    elif has_divergent_records:
        next_action = "review_canonical_divergences"
    elif has_extra_records:
        next_action = "review_extra_canonical_records"
    elif consistent:
        next_action = "ready_for_canonical_reads"
    else:
        next_action = "review_canonical_parity"

    return {
        "readyForCanonicalReads": ready,
        "hasCanonicalParity": consistent,
        "hasExpectedRecords": has_expected_records,
        "hasCanonicalRecords": has_canonical_records,
        "hasMissingCanonicalRecords": has_missing_records,
        "hasDivergentCanonicalRecords": has_divergent_records,
        "hasExtraCanonicalRecords": has_extra_records,
        "recommendedNextAction": next_action,
        "sourceOfTruth": "legacy_until_canonical_parity",
        "totals": totais,
        "dryRun": sincronizacao,
    }


def serializar_totais_canonicos():
    obrigacoes = ObrigacaoFinanceira.objects.all()
    baixas = BaixaFinanceira.objects.all()
    alocacoes = BaixaFinanceiraAlocacao.objects.all()

    total_entradas = _somar(baixas.filter(tipo="entrada"), "valor_total")
    total_saidas = _somar(baixas.filter(tipo="saida"), "valor_total")

    return {
        "obligations": {
            "count": obrigacoes.count(),
            "plannedAmount": decimal_para_numero(_somar(obrigacoes, "valor_previsto")),
            "realizedAmount": decimal_para_numero(_somar(obrigacoes, "valor_realizado")),
            "pendingAmount": decimal_para_numero(_somar(obrigacoes, "valor_pendente")),
            "overRealizedAmount": decimal_para_numero(
                _somar(obrigacoes, "valor_excedente_realizado")
            ),
        },
        "settlements": {
            "count": baixas.count(),
            "inflowAmount": decimal_para_numero(total_entradas),
            "outflowAmount": decimal_para_numero(total_saidas),
            "financialResult": decimal_para_numero(total_entradas - total_saidas),
        },
        "allocations": {
            "count": alocacoes.count(),
            "allocatedAmount": decimal_para_numero(_somar(alocacoes, "valor_alocado")),
            "interestAmount": decimal_para_numero(_somar(alocacoes, "valor_juros")),
            "fineAmount": decimal_para_numero(_somar(alocacoes, "valor_multa")),
            "discountAmount": decimal_para_numero(_somar(alocacoes, "valor_desconto")),
        },
    }


def _totais_paridade(paridade):
    grupos = (paridade["obrigacoes"], paridade["baixas"], paridade["alocacoes"])
    return {
        "expected": sum(grupo["expected"] for grupo in grupos),
        "existing": sum(grupo["existing"] for grupo in grupos),
        "missing": sum(grupo["missing"] for grupo in grupos),
        "divergent": sum(grupo["divergent"] for grupo in grupos),
        "extra": sum(grupo["extra"] for grupo in grupos),
    }


def _somar(queryset, campo):
    return quantizar_moeda(queryset.aggregate(total=Sum(campo))["total"] or Decimal("0.00"))


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
