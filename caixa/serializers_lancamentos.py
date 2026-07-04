from decimal import Decimal

from django.utils import timezone

from .selectors_lancamentos import (
    calcular_totais_lancamentos_financeiros,
    filtrar_lancamentos_financeiros,
)
from .selectors_obrigacoes import FONTES_OBRIGACOES
from .services_dimensoes_operacionais import serializar_dimensao_operacional_financeira
from .utils_financeiros import quantizar_moeda
from .utils_contratos import normalizar_codigo_contrato_visual
from .utils_periodos import resolver_intervalo_periodo_canonico


LIMITE_PADRAO = 100
LIMITE_MAXIMO = 200


def montar_payload_lancamentos_financeiros_api(params):
    filtros = normalizar_filtros_lancamentos(params)
    queryset = (
        filtrar_lancamentos_financeiros(filtros)
        .select_related(
            "cliente",
            "evento",
            "evento__cliente",
            "evento__orcamento",
        )
        .order_by("-data_lancamento", "-id")
    )
    total_registros = queryset.count()
    limit = normalizar_inteiro(filtros.get("limit"), LIMITE_PADRAO, 1, LIMITE_MAXIMO)
    offset = normalizar_inteiro(filtros.get("offset"), 0, 0, total_registros)
    itens = queryset[offset:offset + limit]

    return {
        "data": {
            "items": [serializar_lancamento_financeiro(item) for item in itens],
            "summary": serializar_totais(calcular_totais_lancamentos_financeiros(filtros)),
            "filters": serializar_filtros_lancamentos(filtros),
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
            },
        }
    }


def normalizar_filtros_lancamentos(params):
    params = dict(params.items()) if hasattr(params, "items") else dict(params or {})
    periodo = resolver_intervalo_periodo_canonico(params)
    event_id = normalizar_id(params.get("eventId"))
    client_id = normalizar_id(params.get("clientId"))
    source_id = normalizar_id(params.get("sourceId"))

    filtros = {
        "period": periodo["period"],
        "quickPeriod": periodo["quickPeriod"],
        "startDate": periodo["startDate"],
        "data_inicial": periodo["startDate"],
        "endDate": periodo["endDate"],
        "data_final": periodo["endDate"],
        "contractCode": normalizar_codigo_contrato_visual(params.get("contractCode")),
        "eventId": event_id,
        "clientId": client_id,
        "cashFlowGroup": params.get("cashFlowGroup") or "",
        "type": params.get("type") or "",
        "nature": params.get("nature") or "",
        "origin": params.get("origin") or "",
        "source": params.get("source") or "",
        "sourceId": source_id,
        "sourceDetail": params.get("sourceDetail") or "",
        "status": params.get("status") or "",
        "search": params.get("search") or "",
        "limit": params.get("limit"),
        "offset": params.get("offset"),
    }
    filtros["contrato_codigo"] = filtros["contractCode"]
    filtros["evento_id"] = event_id
    filtros["cliente_id"] = client_id
    filtros["fluxo"] = filtros["cashFlowGroup"]
    filtros["tipo"] = filtros["type"]
    filtros["natureza"] = filtros["nature"]
    filtros["origem"] = filtros["origin"]
    filtros["source_id"] = source_id
    filtros["source_detail"] = filtros["sourceDetail"]
    filtros["busca"] = filtros["search"]
    return filtros


def serializar_lancamento_financeiro(lancamento):
    origem = origem_lancamento(lancamento)
    dimensao = serializar_dimensao_operacional_financeira(lancamento)
    ledger_amount = decimal_para_numero(lancamento.valor)
    origin_id = getattr(lancamento, f"{origem}_id", None) if origem else None
    origin_label = rotulo_origem_lancamento(origem)

    return {
        "id": lancamento.id,
        "date": lancamento.data_lancamento.isoformat(),
        "data": lancamento.data_lancamento.isoformat(),
        "type": lancamento.tipo,
        "tipo": lancamento.tipo,
        "typeLabel": lancamento.get_tipo_display(),
        "cashFlowGroup": lancamento.fluxo,
        "fluxo": lancamento.fluxo,
        "cashFlowGroupLabel": lancamento.get_fluxo_display(),
        "nature": lancamento.natureza,
        "natureza": lancamento.natureza,
        "natureLabel": lancamento.get_natureza_display(),
        "amount": ledger_amount,
        "ledgerAmount": ledger_amount,
        "valorLancamento": ledger_amount,
        "valor_lancamento": ledger_amount,
        "valor": ledger_amount,
        "description": lancamento.descricao,
        "ledgerDescription": lancamento.descricao,
        "descricao": lancamento.descricao,
        "status": lancamento.status,
        "statusLabel": lancamento.get_status_display(),
        "origin": origem,
        "origem": origem,
        "originId": origin_id,
        "originLabel": origin_label,
        "source": origem,
        "sourceId": origin_id,
        "sourceLabel": origin_label,
        "clientId": dimensao["clientId"] or lancamento.cliente_id,
        "clientName": dimensao["clientName"],
        "cliente_id": dimensao["clientId"] or lancamento.cliente_id,
        "cliente_nome": dimensao["clientName"],
        "contractCode": dimensao["contractCode"],
        "contractName": dimensao["contractName"],
        "contractLabel": dimensao["contractLabel"],
        "contract": dimensao["contractCode"],
        "contrato_codigo": dimensao["contractCode"],
        "eventId": dimensao["eventId"] or lancamento.evento_id,
        "eventName": dimensao["eventName"],
        "eventNumber": dimensao["eventNumber"],
        "eventLabel": dimensao["eventLabel"],
        "evento_id": dimensao["eventId"] or lancamento.evento_id,
        "evento_nome": dimensao["eventName"],
        "evento_numero": dimensao["eventNumber"],
        "evento_label": dimensao["eventLabel"],
    }


def serializar_totais(totais):
    return {
        "entradas": decimal_para_numero(totais["entradas"]),
        "inflowAmount": decimal_para_numero(totais["entradas"]),
        "saidas": decimal_para_numero(totais["saidas"]),
        "outflowAmount": decimal_para_numero(totais["saidas"]),
        "resultadoFinanceiro": decimal_para_numero(totais["resultado_financeiro"]),
        "financialResultAmount": decimal_para_numero(totais["resultado_financeiro"]),
        "resultado_financeiro": decimal_para_numero(totais["resultado_financeiro"]),
        "cashFlows": {
            "fco": serializar_totais_fluxo(totais["fco"]),
            "fci": serializar_totais_fluxo(totais["fci"]),
            "fcf": serializar_totais_fluxo(totais["fcf"]),
        },
    }


def serializar_totais_fluxo(totais_fluxo):
    return {
        "entradas": decimal_para_numero(totais_fluxo["entradas"]),
        "inflowAmount": decimal_para_numero(totais_fluxo["entradas"]),
        "saidas": decimal_para_numero(totais_fluxo["saidas"]),
        "outflowAmount": decimal_para_numero(totais_fluxo["saidas"]),
        "resultadoFinanceiro": decimal_para_numero(
            totais_fluxo["resultado_financeiro"]
        ),
        "financialResultAmount": decimal_para_numero(
            totais_fluxo["resultado_financeiro"]
        ),
        "resultado_financeiro": decimal_para_numero(
            totais_fluxo["resultado_financeiro"]
        ),
    }


def serializar_filtros_lancamentos(filtros):
    period = filtros.get("period") or ""
    start_date = filtros.get("startDate") or filtros.get("data_inicial") or ""
    end_date = filtros.get("endDate") or filtros.get("data_final") or ""
    contract_code = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    event_id = (
        filtros.get("eventId")
        or filtros.get("costCenterId")
        or filtros.get("evento")
        or filtros.get("evento_id")
        or ""
    )
    client_id = filtros.get("clientId") or filtros.get("cliente") or filtros.get("cliente_id") or ""
    cash_flow_group = filtros.get("cashFlowGroup") or filtros.get("fluxo") or ""
    tipo = filtros.get("type") or filtros.get("tipo") or ""
    nature = filtros.get("nature") or filtros.get("natureza") or ""
    origin = filtros.get("origin") or filtros.get("origem") or ""
    source = filtros.get("source") or filtros.get("origem_obrigacao") or ""
    source_id = (
        filtros.get("sourceId")
        or filtros.get("source_id")
        or filtros.get("originId")
        or filtros.get("origin_id")
        or ""
    )
    source_detail = filtros.get("sourceDetail") or filtros.get("source_detail") or ""
    status = filtros.get("status") or ""
    search = filtros.get("search") or filtros.get("busca") or ""
    origin_label = rotulo_origem_lancamento(origin)
    source_label = rotulo_source_lancamento(source or origin)

    return {
        "period": period,
        "quickPeriod": filtros.get("quickPeriod") or "",
        "startDate": start_date,
        "endDate": end_date,
        "contractCode": contract_code,
        "eventId": event_id,
        "clientId": client_id,
        "cashFlowGroup": cash_flow_group,
        "type": tipo,
        "nature": nature,
        "origin": origin,
        "originLabel": origin_label,
        "source": source,
        "sourceLabel": source_label,
        "sourceId": source_id,
        "sourceDetail": source_detail,
        "status": status,
        "search": search,
    }


def origem_lancamento(lancamento):
    origens = lancamento.campos_origem_preenchidos()
    return origens[0] if origens else ""


def rotulo_origem_lancamento(origem):
    return {
        "receita_operacional": "Receita operacional",
        "despesa_operacional": "Despesa operacional manual",
        "custo_fixo": "Custo fixo",
        "pagamento_custo_servico": "Pagamento de custo de serviço",
        "pagamento_custo_extra": "Pagamento de custo extra",
        "pagamento_parcela_divida": "Pagamento de parcela",
        "investimento": "Investimento",
        "financiamento_movimentacao": "Movimentação de financiamento",
    }.get(origem, "")


def rotulo_source_lancamento(source):
    return FONTES_OBRIGACOES.get(source or "", rotulo_origem_lancamento(source))


def normalizar_inteiro(valor, padrao, minimo, maximo):
    try:
        inteiro = int(valor)
    except (TypeError, ValueError):
        return padrao

    return min(max(inteiro, minimo), maximo)


def normalizar_id(valor):
    valor = str(valor or "").strip()
    if not valor:
        return ""

    try:
        return str(int(valor))
    except (TypeError, ValueError):
        return "__invalid__"


def decimal_para_numero(valor):
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor or "0"))

    return float(quantizar_moeda(valor))
