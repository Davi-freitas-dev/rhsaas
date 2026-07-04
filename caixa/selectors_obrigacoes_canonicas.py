from decimal import Decimal

from django.utils import timezone

from .models import ObrigacaoFinanceira
from .selectors_obrigacoes import (
    FONTES_OBRIGACOES,
    STATUS_CANCELADO,
    STATUS_LIQUIDADO,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
    STATUS_VENCIDO,
)
from .services_dimensoes_operacionais import serializar_dimensao_operacional_financeira
from .utils_contratos import montar_filtro_evento_ou_orcamento_por_contrato_visual
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")

ORIGEM_ID_CANONICA = {
    "receita_operacional": "receita_operacional_id",
    "despesa_operacional": "despesa_operacional_id",
    "custo_fixo": "custo_fixo_id",
    "custo_servico": "evento_custo_servico_id",
    "custo_extra": "evento_custo_extra_id",
    "parcela_divida": "parcela_divida_id",
    "investimento": "investimento_id",
    "financiamento_movimentacao": "financiamento_movimentacao_id",
}


def listar_obrigacoes_financeiras_canonicas(filtros=None):
    filtros = filtros or {}
    if _filtro_operacional_invalido(filtros):
        return []

    query = (
        ObrigacaoFinanceira.objects.select_related(
            "cliente",
            "evento",
            "evento__orcamento",
        )
        .prefetch_related("alocacoes_baixa__baixa")
        .filter(tipo=_tipo_obrigacao_canonica(filtros))
    )
    query = _aplicar_filtros_canonicos(query, filtros)
    itens = [_montar_item_canonico(obrigacao) for obrigacao in query]
    itens = _filtrar_busca(itens, filtros)
    itens = _filtrar_excedente_realizado(itens, filtros)
    itens = _filtrar_reconciliacao(itens, filtros)
    return sorted(
        itens,
        key=lambda item: (
            item["due_date"] or timezone.datetime.max.date(),
            item["cash_flow_group"],
            item["source"],
            item["description"],
            str(item["source_id"]),
        ),
    )


def contar_obrigacoes_financeiras_canonicas(filtros=None):
    filtros = filtros or {}
    if _filtro_operacional_invalido(filtros):
        return 0

    query = ObrigacaoFinanceira.objects.filter(tipo=_tipo_obrigacao_canonica(filtros))
    query = _aplicar_filtros_canonicos(query, filtros)
    return query.count()


def _aplicar_filtros_canonicos(query, filtros):
    data_inicial = filtros.get("startDate") or filtros.get("data_inicial")
    data_final = filtros.get("endDate") or filtros.get("data_final")
    contract_code = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    event_id = filtros.get("eventId")
    client_id = filtros.get("clientId")
    source = filtros.get("source") or filtros.get("origin") or filtros.get("origem")
    cash_flow_group = filtros.get("cashFlowGroup") or filtros.get("fluxo")
    nature = filtros.get("nature") or filtros.get("natureza")
    status = filtros.get("status") or filtros.get("settlementStatus") or filtros.get("situacao")
    sources = filtros.get("sources") or []

    if data_inicial:
        query = query.filter(data_vencimento__gte=data_inicial)
    if data_final:
        query = query.filter(data_vencimento__lte=data_final)
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
    if source:
        query = query.filter(origem=source)
    elif sources:
        query = query.filter(origem__in=sources)
    if cash_flow_group:
        query = query.filter(fluxo=cash_flow_group)
    if nature:
        query = query.filter(natureza=nature)

    if status:
        if status == STATUS_VENCIDO:
            if filtros.get("overdueScope") == "all":
                query = query.exclude(status=STATUS_CANCELADO)
            query = query.filter(
                valor_pendente__gt=ZERO,
                data_vencimento__lt=timezone.localdate(),
            )
        elif status == STATUS_LIQUIDADO:
            query = query.filter(valor_pendente=ZERO)
        else:
            query = query.filter(status=status)

    return query.order_by("data_vencimento", "origem", "descricao", "id")


def _tipo_obrigacao_canonica(filtros):
    if filtros.get("obligationType") == ObrigacaoFinanceira.TIPO_RECEBER:
        return ObrigacaoFinanceira.TIPO_RECEBER
    return ObrigacaoFinanceira.TIPO_PAGAR


def _montar_item_canonico(obrigacao):
    realized_amount = quantizar_moeda(obrigacao.valor_realizado)
    pending_amount = quantizar_moeda(obrigacao.valor_pendente)
    planned_amount = quantizar_moeda(obrigacao.valor_previsto)
    over_realized_amount = quantizar_moeda(obrigacao.valor_excedente_realizado)
    payment_date = _data_ultima_baixa(obrigacao)
    settlement_status = _status_liquidacao_canonico(obrigacao)
    source_id = getattr(obrigacao, ORIGEM_ID_CANONICA.get(obrigacao.origem, "id"))
    dimensao = serializar_dimensao_operacional_financeira(obrigacao)

    return {
        "id": obrigacao.chave_origem or f"obrigacao_financeira:{obrigacao.id}",
        "obligation_type": obrigacao.tipo,
        "source": obrigacao.origem,
        "source_id": source_id,
        "source_label": FONTES_OBRIGACOES.get(obrigacao.origem, obrigacao.get_origem_display()),
        "source_detail": obrigacao.detalhe_origem,
        "source_detail_label": obrigacao.detalhe_origem,
        "description": obrigacao.descricao,
        "reference": obrigacao.referencia,
        "due_date": obrigacao.data_vencimento,
        "payment_date": payment_date,
        "planned_amount": planned_amount,
        "realized_amount": realized_amount,
        "over_realized_amount": over_realized_amount,
        "pending_amount": pending_amount,
        "cash_flow_group": obrigacao.fluxo,
        "nature": obrigacao.natureza,
        "status": obrigacao.status,
        "status_label": obrigacao.get_status_display(),
        "settlement_status": settlement_status,
        "settlement_status_label": _rotulo_status_liquidacao(settlement_status),
        "is_overdue": settlement_status == STATUS_VENCIDO,
        "days_overdue": _dias_vencido(obrigacao, pending_amount),
        "client_id": dimensao["clientId"] or obrigacao.cliente_id,
        "client_name": dimensao["clientName"],
        "contract_code": dimensao["contractCode"],
        "contract_name": dimensao["contractName"],
        "contract_label": dimensao["contractLabel"],
        "event_id": dimensao["eventId"] or obrigacao.evento_id,
        "event_name": dimensao["eventName"],
        "event_number": dimensao["eventNumber"],
        "event_label": dimensao["eventLabel"],
        "origin_realized_amount": realized_amount,
        "origin_pending_amount": pending_amount,
        "origin_over_realized_amount": over_realized_amount,
        "ledger_realized_amount": realized_amount,
        "ledger_pending_amount": pending_amount,
        "ledger_over_realized_amount": over_realized_amount,
        "ledger_settlement_status": settlement_status,
        "ledger_settlement_status_label": _rotulo_status_liquidacao(settlement_status),
        "ledger_is_overdue": settlement_status == STATUS_VENCIDO,
        "ledger_days_overdue": _dias_vencido(obrigacao, pending_amount),
        "ledger_entry_count": obrigacao.alocacoes_baixa.count(),
        "realized_amount_difference": ZERO,
        "is_ledger_reconciled": True,
        "reconciliation_status": "conciliado",
        "reconciliation_diagnosis": "conciliado",
        "reconciliation_diagnosis_label": "Origem e ledger conciliados",
        "realized_amount_source": "canonical",
        "read_model_source": "canonical",
    }


def _data_ultima_baixa(obrigacao):
    datas = [
        alocacao.baixa.data_baixa
        for alocacao in obrigacao.alocacoes_baixa.all()
        if alocacao.baixa
    ]
    return max(datas) if datas else None


def _status_liquidacao_canonico(obrigacao):
    if obrigacao.status == STATUS_CANCELADO:
        return STATUS_CANCELADO
    if obrigacao.valor_pendente <= ZERO:
        return STATUS_LIQUIDADO
    if obrigacao.data_vencimento < timezone.localdate():
        return STATUS_VENCIDO
    if obrigacao.valor_realizado > ZERO:
        return STATUS_PARCIAL
    return STATUS_PENDENTE


def _dias_vencido(obrigacao, pending_amount):
    if pending_amount <= ZERO or obrigacao.data_vencimento >= timezone.localdate():
        return 0
    return (timezone.localdate() - obrigacao.data_vencimento).days


def _rotulo_status_liquidacao(status):
    return {
        STATUS_PENDENTE: "Pendente",
        STATUS_PARCIAL: "Parcial",
        STATUS_VENCIDO: "Vencido",
        STATUS_LIQUIDADO: "Liquidado",
        STATUS_CANCELADO: "Cancelado",
    }.get(status, status)


def _filtrar_busca(itens, filtros):
    search = (filtros.get("search") or filtros.get("busca") or "").strip().lower()
    if not search:
        return itens

    return [
        item for item in itens
        if any(
            search in str(valor or "").lower()
            for valor in (
                item["description"],
                item["reference"],
                item["source_label"],
                item["source_detail_label"],
                item["client_name"],
                item["contract_code"],
                item["event_name"],
                item["event_number"],
            )
        )
    ]


def _filtrar_excedente_realizado(itens, filtros):
    filtro = filtros.get("realizedAbovePlanned")
    if filtro == "with":
        return [item for item in itens if item["over_realized_amount"] > ZERO]
    if filtro == "without":
        return [item for item in itens if item["over_realized_amount"] <= ZERO]
    return itens


def _filtrar_reconciliacao(itens, filtros):
    status = (
        filtros.get("reconciliationStatus")
        or filtros.get("reconciliation_status")
        or filtros.get("statusConciliacao")
        or filtros.get("conciliacao")
    )
    diagnostico = (
        filtros.get("reconciliationDiagnosis")
        or filtros.get("reconciliation_diagnosis")
        or filtros.get("diagnosticoConciliacao")
        or filtros.get("diagnostico_conciliacao")
    )

    if status == "divergente":
        return []
    if status == "conciliado":
        itens = [
            item for item in itens
            if item.get("reconciliation_status") == "conciliado"
        ]

    if diagnostico and diagnostico != "conciliado":
        return []
    if diagnostico == "conciliado":
        itens = [
            item for item in itens
            if item.get("reconciliation_diagnosis") == "conciliado"
        ]

    return itens


def _filtro_operacional_invalido(filtros):
    return any(
        filtros.get(nome) == "__invalid__"
        for nome in ("eventId", "clientId")
    )
