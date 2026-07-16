from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .demo_policy import is_demo_seed_object
from .constants_financeiros import (
    STATUS_REALIZADO,
    TIPO_CUSTO_ALIMENTACAO,
    TIPO_CUSTO_DIARIAS,
    TIPO_CUSTO_TRANSPORTE,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from .models import DespesaOperacional, LancamentoFinanceiro, ReceitaOperacional
from .models_custo_fixo import CustoFixo
from .models_custos_extras import EventoCustoExtra
from .models_dividas import ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .models_servico import EventoCustoServico
from .services_dimensoes_operacionais import (
    dados_parcela_divida_sem_lazy,
    relacao_carregada,
    serializar_dimensao_operacional_financeira,
)
from .utils_contratos import (
    montar_filtro_evento_ou_orcamento_por_contrato_visual,
    montar_filtro_evento_por_contrato_visual,
)
from .utils_financeiros import quantizar_moeda


ORIGEM_RECEITA_OPERACIONAL = "receita_operacional"
ORIGEM_DESPESA_OPERACIONAL = "despesa_operacional"
ORIGEM_CUSTO_FIXO = "custo_fixo"
ORIGEM_CUSTO_SERVICO = "custo_servico"
ORIGEM_CUSTO_EXTRA = "custo_extra"
ORIGEM_PARCELA_DIVIDA = "parcela_divida"
ORIGEM_INVESTIMENTO = "investimento"
ORIGEM_FINANCIAMENTO = "financiamento_movimentacao"

STATUS_PENDENTE = "pendente"
STATUS_PARCIAL = "parcial"
STATUS_VENCIDO = "vencido"
STATUS_LIQUIDADO = "liquidado"
STATUS_CANCELADO = "cancelado"

FONTES_OBRIGACOES = {
    ORIGEM_RECEITA_OPERACIONAL: "Receita operacional",
    ORIGEM_DESPESA_OPERACIONAL: "Despesa operacional manual",
    ORIGEM_CUSTO_FIXO: "Custo fixo",
    ORIGEM_CUSTO_SERVICO: "Custo de serviço",
    ORIGEM_CUSTO_EXTRA: "Custo extra do evento",
    ORIGEM_PARCELA_DIVIDA: "Parcela FCF",
    ORIGEM_INVESTIMENTO: "Investimento",
    ORIGEM_FINANCIAMENTO: "Movimentação de financiamento",
}

CUSTOS_SERVICO_COMPONENTES = (
    {
        "tipo": TIPO_CUSTO_DIARIAS,
        "rotulo": "Diarias",
        "campo_previsto": "valor_diarias",
        "campo_realizado": "total_pago_diarias",
        "campo_pendente": "valor_pendente_diarias",
    },
    {
        "tipo": TIPO_CUSTO_ALIMENTACAO,
        "rotulo": "Alimentacao",
        "campo_previsto": "valor_alimentacao",
        "campo_realizado": "total_pago_alimentacao",
        "campo_pendente": "valor_pendente_alimentacao",
    },
    {
        "tipo": TIPO_CUSTO_TRANSPORTE,
        "rotulo": "Transporte",
        "campo_previsto": "valor_transporte",
        "campo_realizado": "total_pago_transporte",
        "campo_pendente": "valor_pendente_transporte",
    },
)

FLUXOS_OBRIGACOES = ("fco", "fci", "fcf")
ZERO = Decimal("0.00")
OVERVIEW_CONTRACT_VERSION = "financial-obligation-overview-summary-v1"
OVERVIEW_MES_SEM_DATA = "sem-data"
OVERVIEW_STATUS_SEM_STATUS = "sem-status"

RECONCILIACAO_DIAGNOSTICOS = {
    "conciliado": "Origem e ledger conciliados",
    "ledger_sem_lancamento": "Origem possui realizado sem lançamento no ledger",
    "origem_sem_realizado": "Ledger possui realizado sem valor realizado na origem",
    "ledger_menor_que_origem": "Ledger menor que a origem",
    "ledger_maior_que_origem": "Ledger maior que a origem",
    "divergencia_valor": "Diferença de valor entre origem e ledger",
}

RECONCILIACAO_ORIENTACOES = {
    "conciliado": {
        "code": "sem_acao",
        "severity": "success",
        "title": "Conciliado",
        "description": "Origem e ledger estão alinhados.",
    },
    "ledger_sem_lancamento": {
        "code": "sincronizar_lancamento_ledger",
        "severity": "danger",
        "title": "Sincronizar lançamento no ledger",
        "description": (
            "A origem possui valor realizado, mas não há lançamento financeiro "
            "vinculado. Confira a baixa na origem e gere ou ajuste o lançamento "
            "do ledger."
        ),
    },
    "origem_sem_realizado": {
        "code": "revisar_baixa_origem",
        "severity": "warning",
        "title": "Revisar baixa na origem",
        "description": (
            "Existe lançamento financeiro, mas a origem não mostra valor "
            "realizado. Confira se a baixa foi registrada na entidade "
            "operacional correta."
        ),
    },
    "ledger_menor_que_origem": {
        "code": "complementar_lancamento_ledger",
        "severity": "danger",
        "title": "Complementar ledger",
        "description": (
            "O ledger registra menos realizado do que a origem. Confira "
            "lançamentos ausentes, parciais ou valor incorreto."
        ),
    },
    "ledger_maior_que_origem": {
        "code": "revisar_excesso_ledger",
        "severity": "warning",
        "title": "Revisar excesso no ledger",
        "description": (
            "O ledger registra mais realizado do que a origem. Procure "
            "lançamentos duplicados, origem incorreta ou valor excedente."
        ),
    },
    "divergencia_valor": {
        "code": "comparar_origem_ledger",
        "severity": "warning",
        "title": "Comparar origem e ledger",
        "description": (
            "Há diferença entre origem e ledger que não se encaixa nas causas "
            "específicas. Compare os lançamentos vinculados com a origem."
        ),
    },
}


def listar_obrigacoes_financeiras(filtros=None):
    filtros = filtros or {}

    if filtro_operacional_invalido(filtros) or _filtro_tipo_obrigacao_incompativel(filtros):
        return []

    itens = []
    if filtros.get("obligationType") == "receber":
        itens.extend(_itens_receitas(filtros))
        itens.extend(_itens_investimentos_entrada(filtros))
        itens.extend(_itens_financiamentos_entrada(filtros))
    else:
        itens.extend(_itens_despesas_manuais(filtros))
        itens.extend(_itens_custos_fixos(filtros))
        itens.extend(_itens_custos_servico(filtros))
        itens.extend(_itens_custos_extras(filtros))
        itens.extend(_itens_parcelas_divida(filtros))
        itens.extend(_itens_investimentos_saida(filtros))
        itens.extend(_itens_financiamentos_saida(filtros))

    itens = _filtrar_itens_obrigacoes(itens, filtros)
    _aplicar_reconciliacao_lancamentos(itens)
    _aplicar_base_realizado(itens, filtros)
    itens = _filtrar_itens_excedente_realizado(itens, filtros)
    itens = _filtrar_itens_reconciliacao(itens, filtros)
    itens = _filtrar_itens_diagnostico_reconciliacao(itens, filtros)
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


def _filtro_tipo_obrigacao_incompativel(filtros):
    tipo = filtros.get("obligationType")
    return bool(tipo and tipo not in {"pagar", "receber"})


def resumir_obrigacoes_financeiras(itens):
    resumo = _novo_resumo()
    por_fluxo = {fluxo: _novo_resumo() for fluxo in FLUXOS_OBRIGACOES}
    por_origem = defaultdict(_novo_resumo)
    por_diagnostico = defaultdict(_novo_resumo)
    fila_divergencias = {}

    for item in itens:
        _somar_item_resumo(resumo, item)
        _somar_item_resumo(por_fluxo[item["cash_flow_group"]], item)
        _somar_item_resumo(por_origem[item["source"]], item)
        _somar_item_resumo(
            por_diagnostico[item.get("reconciliation_diagnosis", "conciliado")],
            item,
        )
        _somar_item_fila_divergencias(fila_divergencias, item)

    return {
        **_serializar_resumo_decimal(resumo),
        "byCashFlowGroup": {
            fluxo: _serializar_resumo_decimal(por_fluxo[fluxo])
            for fluxo in FLUXOS_OBRIGACOES
        },
        "bySource": {
            origem: {
                **_serializar_resumo_decimal(valores),
                "sourceLabel": FONTES_OBRIGACOES.get(origem, origem),
            }
            for origem, valores in sorted(por_origem.items())
        },
        "byReconciliationDiagnosis": {
            diagnostico: {
                **_serializar_resumo_decimal(valores),
                "label": RECONCILIACAO_DIAGNOSTICOS.get(diagnostico, diagnostico),
            }
            for diagnostico, valores in sorted(por_diagnostico.items())
        },
        "reconciliationWorklist": [
            _serializar_grupo_fila_divergencias(grupo)
            for grupo in sorted(
                fila_divergencias.values(),
                key=_chave_ordenacao_fila_divergencias,
            )
        ],
    }


def montar_overview_obrigacoes_financeiras(itens, filtros=None):
    filtros = filtros or {}
    resumo = _novo_resumo()
    por_mes = {}
    por_status = {}
    por_origem = {}
    por_categoria = {}
    eventos = set()
    clientes = set()

    for item in itens:
        _somar_item_resumo(resumo, item)
        _adicionar_id_distinto(eventos, item.get("event_id"))
        _adicionar_id_distinto(clientes, item.get("client_id"))
        _somar_item_grupo_overview(
            por_mes,
            *_chave_mes_overview(item),
            item,
        )
        _somar_item_grupo_overview(
            por_status,
            *_chave_status_overview(item),
            item,
        )
        _somar_item_grupo_overview(
            por_origem,
            *_chave_origem_overview(item),
            item,
            source=item.get("source") or "",
            source_label=item.get("source_label") or "",
        )
        _somar_item_grupo_overview(
            por_categoria,
            *_chave_categoria_overview(item),
            item,
            source=item.get("source") or "",
            source_label=item.get("source_label") or "",
            source_detail=item.get("source_detail") or "",
            source_detail_label=item.get("source_detail_label") or "",
        )

    total_planejado = resumo["planned_amount"]
    return {
        "contract_version": OVERVIEW_CONTRACT_VERSION,
        "date_basis": "dueDate",
        "amount_basis": filtros.get("realizedAmountBasis") or "originState",
        "scope": {
            "obligation_type": filtros.get("obligationType") or "",
            "cash_flow_group": filtros.get("cashFlowGroup") or "",
            "source": filtros.get("source") or "",
            "sources": list(filtros.get("sources") or []),
        },
        "totals": {
            **_serializar_totais_overview(resumo),
            "distinct_events_count": len(eventos),
            "distinct_clients_count": len(clientes),
        },
        "monthly_series": [
            _serializar_grupo_overview(grupo)
            for grupo in sorted(
                por_mes.values(),
                key=_chave_ordenacao_mes_overview,
            )
        ],
        "breakdown_by_settlement_status": [
            _serializar_grupo_overview(grupo, total_planejado)
            for grupo in sorted(por_status.values(), key=lambda grupo: grupo["key"])
        ],
        "breakdown_by_source": [
            _serializar_grupo_overview(grupo, total_planejado)
            for grupo in sorted(por_origem.values(), key=lambda grupo: grupo["key"])
        ],
        "breakdown_by_category": [
            _serializar_grupo_overview(grupo, total_planejado)
            for grupo in sorted(por_categoria.values(), key=lambda grupo: grupo["key"])
        ],
    }


def _adicionar_id_distinto(destino, valor):
    if valor not in (None, ""):
        destino.add(valor)


def _somar_item_grupo_overview(grupos, key, label, item, **metadados):
    grupo = grupos.setdefault(
        key,
        {
            "key": key,
            "label": label,
            "summary": _novo_resumo(),
            **metadados,
        },
    )
    _somar_item_resumo(grupo["summary"], item)


def _chave_mes_overview(item):
    due_date = item.get("due_date")
    if not due_date:
        return OVERVIEW_MES_SEM_DATA, "Sem data"
    key = due_date.strftime("%Y-%m")
    return key, key


def _chave_status_overview(item):
    key = item.get("settlement_status") or item.get("status") or OVERVIEW_STATUS_SEM_STATUS
    label = item.get("settlement_status_label") or item.get("status_label") or "Sem status"
    return key, label


def _chave_origem_overview(item):
    key = item.get("source") or ""
    label = item.get("source_label") or key
    return key, label


def _chave_categoria_overview(item):
    source = item.get("source") or ""
    source_detail = item.get("source_detail") or ""
    key = source_detail or source
    label = (
        item.get("source_detail_label")
        or item.get("source_label")
        or "Categoria nao informada"
    )
    return key, label


def _chave_ordenacao_mes_overview(grupo):
    return (grupo["key"] == OVERVIEW_MES_SEM_DATA, grupo["key"])


def _serializar_totais_overview(resumo):
    return {
        "items_count": resumo["count"],
        "planned_amount": quantizar_moeda(resumo["planned_amount"]),
        "realized_amount": quantizar_moeda(resumo["realized_amount"]),
        "pending_amount": quantizar_moeda(resumo["pending_amount"]),
        "overdue_amount": quantizar_moeda(resumo["overdue_amount"]),
        "overdue_count": resumo["overdue_count"],
        "settled_count": resumo["liquidated_count"],
    }


def _serializar_grupo_overview(grupo, total_planejado=None):
    resumo = grupo["summary"]
    payload = {
        "key": grupo["key"],
        "label": grupo["label"],
        **_serializar_totais_overview(resumo),
        "pending_count": resumo["pending_count"],
    }
    for campo in (
        "source",
        "source_label",
        "source_detail",
        "source_detail_label",
    ):
        if campo in grupo:
            payload[campo] = grupo[campo]

    if total_planejado is not None:
        payload["percentage_by_planned_amount"] = _percentual_planejado_overview(
            resumo["planned_amount"],
            total_planejado,
        )

    return payload


def _percentual_planejado_overview(valor, total):
    if total <= ZERO:
        return ZERO
    return quantizar_moeda((valor / total) * Decimal("100"))


def _somar_item_fila_divergencias(fila, item):
    if item.get("is_ledger_reconciled", True):
        return

    diagnostico = item.get("reconciliation_diagnosis", "divergencia_valor")
    obligation_type = item.get("obligation_type", "pagar")
    source = item["source"]
    client_id = item.get("client_id")
    client_name = item.get("client_name") or ""
    contract_code = item.get("contract_code") or ""
    chave = (
        diagnostico,
        obligation_type,
        source,
        contract_code,
        client_id or 0,
        client_name,
    )
    grupo = fila.setdefault(
        chave,
        {
            "key": ":".join(
                [
                    diagnostico,
                    obligation_type,
                    source,
                    contract_code or "sem_contrato",
                    str(client_id or "sem_cliente"),
                ]
            ),
            "obligation_type": obligation_type,
            "reconciliation_diagnosis": diagnostico,
            "reconciliation_diagnosis_label": RECONCILIACAO_DIAGNOSTICOS.get(
                diagnostico,
                diagnostico,
            ),
            "source": source,
            "source_label": item.get("source_label") or FONTES_OBRIGACOES.get(source, source),
            "contract_code": contract_code,
            "contract_name": item.get("contract_name") or "",
            "contract_label": item.get("contract_label") or contract_code,
            "client_id": client_id,
            "client_name": client_name,
            "summary": _novo_resumo(),
        },
    )
    _somar_item_resumo(grupo["summary"], item)


def _serializar_grupo_fila_divergencias(grupo):
    return {
        **_serializar_resumo_decimal(grupo["summary"]),
        "key": grupo["key"],
        "obligation_type": grupo["obligation_type"],
        "reconciliation_diagnosis": grupo["reconciliation_diagnosis"],
        "reconciliation_diagnosis_label": grupo["reconciliation_diagnosis_label"],
        "source": grupo["source"],
        "source_label": grupo["source_label"],
        "contract_code": grupo["contract_code"],
        "contract_name": grupo["contract_name"],
        "contract_label": grupo["contract_label"],
        "client_id": grupo["client_id"],
        "client_name": grupo["client_name"],
    }


def _chave_ordenacao_fila_divergencias(grupo):
    resumo = grupo["summary"]
    return (
        grupo["reconciliation_diagnosis"],
        grupo["obligation_type"],
        grupo["source"],
        grupo["contract_code"],
        grupo["client_name"],
        -abs(resumo["realized_amount_difference"]),
    )


def _itens_receitas(filtros):
    if not _deve_carregar_origem(filtros, ORIGEM_RECEITA_OPERACIONAL):
        return []

    query = ReceitaOperacional.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
        "cliente",
    )
    query = _aplicar_periodo(query, "data_vencimento", filtros)
    query = _aplicar_filtros_evento(query, filtros, "evento_id")
    query = _aplicar_filtros_cliente_dimensao(
        query,
        filtros,
        "cliente_id",
        "evento__cliente_id",
    )
    query = _aplicar_filtros_contrato_evento(
        query,
        filtros,
        "evento__",
    )

    return [
        _montar_item(
            source=ORIGEM_RECEITA_OPERACIONAL,
            source_id=receita.id,
            description=receita.descricao,
            reference=_nome_evento_operacional(receita),
            due_date=receita.data_vencimento,
            planned_amount=receita.valor_previsto,
            realized_amount=receita.valor_recebido,
            pending_amount=receita.valor_pendente_recebimento,
            cash_flow_group=LancamentoFinanceiro.FLUXO_FCO,
            nature=LancamentoFinanceiro.NATUREZA_RECEITA_OPERACIONAL,
            status=receita.status,
            status_label=receita.get_status_display(),
            dimension_source=receita,
            payment_date=receita.data_recebimento,
            obligation_type="receber",
        )
        for receita in query
    ]


def _itens_despesas_manuais(filtros):
    if not _deve_carregar_origem(filtros, ORIGEM_DESPESA_OPERACIONAL):
        return []

    query = (
        DespesaOperacional.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
        )
        .filter(origem=DespesaOperacional.ORIGEM_MANUAL)
    )
    query = _aplicar_periodo(query, "data_vencimento", filtros)
    query = _aplicar_filtros_evento(query, filtros, "evento_id")
    query = _aplicar_filtros_cliente_evento(query, filtros, "evento__cliente_id")
    query = _aplicar_filtros_contrato_evento(query, filtros, "evento__")

    return [
        _montar_item(
            source=ORIGEM_DESPESA_OPERACIONAL,
            source_id=despesa.id,
            description=despesa.descricao,
            reference=_nome_evento_operacional(despesa),
            due_date=despesa.data_vencimento,
            planned_amount=despesa.valor_previsto,
            realized_amount=despesa.valor_pago,
            pending_amount=despesa.valor_pendente_pagamento,
            cash_flow_group=LancamentoFinanceiro.FLUXO_FCO,
            nature=LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            status=despesa.status,
            status_label=despesa.get_status_display(),
            dimension_source=despesa,
            payment_date=despesa.data_pagamento,
            source_detail=despesa.categoria,
            source_detail_label=despesa.get_categoria_display(),
        )
        for despesa in query
    ]


def _itens_custos_fixos(filtros):
    if not _deve_carregar_origem(filtros, ORIGEM_CUSTO_FIXO):
        return []

    if _possui_filtro_operacional(filtros):
        return []

    query = CustoFixo.objects.filter(ativo=True)
    query = _aplicar_periodo(query, "data_vencimento", filtros)

    return [
        _montar_item(
            source=ORIGEM_CUSTO_FIXO,
            source_id=custo.id,
            description=custo.descricao,
            reference=custo.get_categoria_display(),
            due_date=custo.data_vencimento,
            planned_amount=custo.valor_previsto,
            realized_amount=custo.valor_pago,
            pending_amount=custo.valor_pendente_pagamento,
            cash_flow_group=LancamentoFinanceiro.FLUXO_FCO,
            nature=LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            status=custo.status,
            status_label=custo.get_status_display(),
            dimension_source=None,
            payment_date=custo.data_pagamento,
            source_detail=custo.categoria,
            source_detail_label=custo.get_categoria_display(),
        )
        for custo in query
    ]


def _itens_custos_servico(filtros):
    if not _deve_carregar_origem(filtros, ORIGEM_CUSTO_SERVICO):
        return []

    query = (
        EventoCustoServico.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
            "servico",
        )
        .prefetch_related("pagamentos")
    )
    query = _aplicar_periodo(query, "evento__data_inicio", filtros)
    query = _aplicar_filtros_evento(query, filtros, "evento_id")
    query = _aplicar_filtros_cliente_evento(query, filtros, "evento__cliente_id")
    query = _aplicar_filtros_contrato_evento(query, filtros, "evento__")

    itens = []
    for custo in query:
        evento = _evento_carregado(custo)
        evento_nome = _nome_evento_operacional(custo)
        data_inicio_evento = getattr(evento, "data_inicio", None) if evento else None
        for componente in CUSTOS_SERVICO_COMPONENTES:
            previsto = getattr(custo, componente["campo_previsto"])
            realizado = getattr(custo, componente["campo_realizado"])
            pendente = getattr(custo, componente["campo_pendente"])
            if previsto <= ZERO and realizado <= ZERO and pendente <= ZERO:
                continue

            itens.append(
                _montar_item(
                    source=ORIGEM_CUSTO_SERVICO,
                    source_id=custo.id,
                    description=f"{custo.servico.nome} - {componente['rotulo']}",
                    reference=evento_nome,
                    due_date=data_inicio_evento,
                    planned_amount=previsto,
                    realized_amount=realizado,
                    pending_amount=pendente,
                    cash_flow_group=LancamentoFinanceiro.FLUXO_FCO,
                    nature=LancamentoFinanceiro.NATUREZA_CUSTO_SERVICO,
                    status="pago" if pendente <= ZERO else STATUS_PENDENTE,
                    status_label="Pago" if pendente <= ZERO else "Pendente",
                    dimension_source=custo,
                    source_detail=componente["tipo"],
                    source_detail_label=componente["rotulo"],
                )
            )

    return itens


def _itens_custos_extras(filtros):
    if not _deve_carregar_origem(filtros, ORIGEM_CUSTO_EXTRA):
        return []

    query = (
        EventoCustoExtra.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
        )
        .prefetch_related("pagamentos")
    )
    query = _aplicar_periodo(query, "data_vencimento", filtros)
    query = _aplicar_filtros_evento(query, filtros, "evento_id")
    query = _aplicar_filtros_cliente_evento(query, filtros, "evento__cliente_id")
    query = _aplicar_filtros_contrato_evento(query, filtros, "evento__")

    return [
        _montar_item(
            source=ORIGEM_CUSTO_EXTRA,
            source_id=custo.id,
            description=custo.descricao,
            reference=_nome_evento_operacional(custo),
            due_date=custo.data_vencimento,
            planned_amount=custo.valor_previsto,
            realized_amount=custo.total_pago,
            pending_amount=custo.valor_pendente_pagamento,
            cash_flow_group=LancamentoFinanceiro.FLUXO_FCO,
            nature=LancamentoFinanceiro.NATUREZA_CUSTO_EXTRA,
            status="pago" if custo.valor_pendente_pagamento <= ZERO else STATUS_PENDENTE,
            status_label="Pago" if custo.valor_pendente_pagamento <= ZERO else "Pendente",
            dimension_source=custo,
            source_detail=custo.categoria,
            source_detail_label=custo.get_categoria_display(),
        )
        for custo in query
    ]


def _itens_parcelas_divida(filtros):
    if not _deve_carregar_origem(filtros, ORIGEM_PARCELA_DIVIDA):
        return []

    query = ParcelaDivida.objects.select_related(
        "divida",
        "divida__evento",
        "divida__evento__cliente",
        "divida__evento__orcamento",
    )
    query = _aplicar_periodo(query, "data_vencimento_atual", filtros)
    query = _aplicar_filtros_evento(query, filtros, "divida__evento_id")
    query = _aplicar_filtros_cliente_dimensao(
        query,
        filtros,
        "divida__evento__cliente_id",
        "divida__evento__cliente_id",
    )
    query = _aplicar_filtros_contrato_dimensao(
        query,
        filtros,
        "divida__evento__",
        "divida__evento__",
    )

    return [_montar_item_parcela_divida(parcela) for parcela in query]


def _itens_investimentos_entrada(filtros):
    return _itens_investimentos_por_tipo_fluxo(
        filtros,
        tipo_fluxo=TIPO_FLUXO_ENTRADA,
        obligation_type="receber",
    )


def _itens_investimentos_saida(filtros):
    return _itens_investimentos_por_tipo_fluxo(
        filtros,
        tipo_fluxo=TIPO_FLUXO_SAIDA,
        obligation_type="pagar",
    )


def _itens_investimentos_por_tipo_fluxo(filtros, *, tipo_fluxo, obligation_type):
    if not _deve_carregar_origem(filtros, ORIGEM_INVESTIMENTO):
        return []

    query = Investimento.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).filter(ativo=True, tipo_fluxo=tipo_fluxo)
    query = _aplicar_periodo(query, "data_prevista", filtros)
    query = _aplicar_filtros_evento(query, filtros, "evento_id")
    query = _aplicar_filtros_cliente_dimensao(
        query,
        filtros,
        "evento__cliente_id",
        "evento__cliente_id",
    )
    query = _aplicar_filtros_contrato_dimensao(
        query,
        filtros,
        "evento__",
        "evento__",
    )

    return [
        _montar_item(
            source=ORIGEM_INVESTIMENTO,
            source_id=investimento.id,
            description=investimento.descricao,
            reference=investimento.get_categoria_display(),
            due_date=investimento.data_prevista,
            planned_amount=investimento.valor_previsto,
            realized_amount=investimento.valor_realizado,
            pending_amount=investimento.valor_pendente_realizacao,
            cash_flow_group=LancamentoFinanceiro.FLUXO_FCI,
            nature=LancamentoFinanceiro.NATUREZA_INVESTIMENTO,
            status=investimento.status,
            status_label=investimento.get_status_display(),
            dimension_source=investimento,
            payment_date=investimento.data_realizacao,
            source_detail=investimento.categoria,
            source_detail_label=investimento.get_categoria_display(),
            obligation_type=obligation_type,
        )
        for investimento in query
    ]


def _itens_financiamentos_entrada(filtros):
    return _itens_financiamentos_por_tipo_fluxo(
        filtros,
        tipo_fluxo=TIPO_FLUXO_ENTRADA,
        obligation_type="receber",
    )


def _itens_financiamentos_saida(filtros):
    return _itens_financiamentos_por_tipo_fluxo(
        filtros,
        tipo_fluxo=TIPO_FLUXO_SAIDA,
        obligation_type="pagar",
    )


def _itens_financiamentos_por_tipo_fluxo(filtros, *, tipo_fluxo, obligation_type):
    if not _deve_carregar_origem(filtros, ORIGEM_FINANCIAMENTO):
        return []

    query = FinanciamentoMovimentacao.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
        "divida_financeira",
        "divida_financeira__credor_cadastro",
    ).filter(ativo=True, tipo_fluxo=tipo_fluxo)
    query = _aplicar_periodo(query, "data_prevista", filtros)
    query = _aplicar_filtros_evento(query, filtros, "evento_id")
    query = _aplicar_filtros_cliente_dimensao(
        query,
        filtros,
        "evento__cliente_id",
        "evento__cliente_id",
    )
    query = _aplicar_filtros_contrato_dimensao(
        query,
        filtros,
        "evento__",
        "evento__",
    )

    return [
        _montar_item(
            source=ORIGEM_FINANCIAMENTO,
            source_id=financiamento.id,
            description=financiamento.descricao,
            reference=financiamento.get_categoria_display(),
            due_date=financiamento.data_prevista,
            planned_amount=financiamento.valor_previsto,
            realized_amount=financiamento.valor_realizado,
            pending_amount=financiamento.valor_pendente_realizacao,
            cash_flow_group=LancamentoFinanceiro.FLUXO_FCF,
            nature=LancamentoFinanceiro.NATUREZA_FINANCIAMENTO,
            status=financiamento.status,
            status_label=financiamento.get_status_display(),
            dimension_source=financiamento,
            payment_date=financiamento.data_realizacao,
            source_detail=financiamento.categoria,
            source_detail_label=financiamento.get_categoria_display(),
            obligation_type=obligation_type,
            navigation_filters=_filtros_navegacao_financiamento(financiamento),
        )
        for financiamento in query
    ]


def _filtros_navegacao_financiamento(financiamento):
    divida = relacao_carregada(financiamento, "divida_financeira")
    filtros = {
        "sourceType": (
            "divida_automatica"
            if financiamento.divida_financeira_id
            else "manual"
        ),
    }
    credor_id = getattr(divida, "credor_cadastro_id", None) if divida else None
    if financiamento.divida_financeira_id and credor_id:
        filtros["creditorId"] = credor_id

    return filtros


def _montar_item_parcela_divida(parcela):
    dados_divida = dados_parcela_divida_sem_lazy(parcela)
    divida = dados_divida["divida"]

    return _montar_item(
        source=ORIGEM_PARCELA_DIVIDA,
        source_id=parcela.id,
        description=dados_divida["descricao"],
        reference=dados_divida["referencia"],
        due_date=parcela.data_vencimento_atual,
        planned_amount=parcela.valor_total_devido,
        realized_amount=parcela.valor_pago,
        pending_amount=parcela.valor_pendente_pagamento,
        cash_flow_group=LancamentoFinanceiro.FLUXO_FCF,
        nature=LancamentoFinanceiro.NATUREZA_PARCELA_DIVIDA,
        status=parcela.status,
        status_label=parcela.get_status_display(),
        dimension_source=divida,
        source_detail=getattr(divida, "tipo", "") if divida else "",
        source_detail_label=divida.get_tipo_display() if divida else "",
    )


def _montar_item(
    *,
    source,
    source_id,
    description,
    reference,
    due_date,
    planned_amount,
    realized_amount,
    pending_amount,
    cash_flow_group,
    nature,
    status,
    status_label,
    dimension_source,
    payment_date=None,
    source_detail="",
    source_detail_label="",
    obligation_type="pagar",
    navigation_filters=None,
):
    planned_amount = quantizar_moeda(planned_amount)
    realized_amount = quantizar_moeda(realized_amount)
    pending_amount = max(quantizar_moeda(pending_amount), ZERO)
    over_realized_amount = _calcular_excedente_realizado(planned_amount, realized_amount)
    dimensao = _montar_dimensao(dimension_source)
    is_seed = is_demo_seed_object(dimension_source)
    settlement_status = _status_liquidacao(status, realized_amount, pending_amount, due_date)
    today = timezone.localdate()
    is_overdue = bool(due_date and due_date < today and pending_amount > ZERO)

    return {
        "id": f"{source}:{source_id}:{source_detail}" if source_detail else f"{source}:{source_id}",
        "obligation_type": obligation_type,
        "source": source,
        "source_id": source_id,
        "source_label": FONTES_OBRIGACOES.get(source, source),
        "source_detail": source_detail or "",
        "source_detail_label": source_detail_label or "",
        "description": description,
        "reference": reference,
        "due_date": due_date,
        "payment_date": payment_date,
        "planned_amount": planned_amount,
        "realized_amount": realized_amount,
        "over_realized_amount": over_realized_amount,
        "pending_amount": pending_amount,
        "cash_flow_group": cash_flow_group,
        "nature": nature,
        "status": status,
        "status_label": status_label,
        "settlement_status": settlement_status,
        "settlement_status_label": _rotulo_status_liquidacao(settlement_status),
        "is_overdue": is_overdue,
        "days_overdue": (today - due_date).days if is_overdue else 0,
        "navigation_filters": navigation_filters or {},
        "is_seed": is_seed,
        "is_read_only": is_seed,
        **dimensao,
    }


def _montar_dimensao(objeto):
    if not objeto:
        return {
            "client_id": None,
            "client_name": "",
            "contract_code": "",
            "contract_name": "",
            "contract_label": "",
            "event_id": None,
            "event_name": "",
            "event_number": "",
            "event_label": "",
        }

    dimensao = serializar_dimensao_operacional_financeira(objeto)

    return {
        "client_id": dimensao["clientId"],
        "client_name": dimensao["clientName"],
        "contract_code": dimensao["contractCode"],
        "contract_name": dimensao["contractName"],
        "contract_label": dimensao["contractLabel"],
        "event_id": dimensao["eventId"],
        "event_name": dimensao["eventName"],
        "event_number": dimensao["eventNumber"],
        "event_label": dimensao["eventLabel"],
    }


def _nome_evento_operacional(objeto):
    return serializar_dimensao_operacional_financeira(objeto)["eventName"]


def _evento_carregado(objeto):
    return relacao_carregada(objeto, "evento")


def _status_liquidacao(status, realized_amount, pending_amount, due_date):
    if status == STATUS_CANCELADO:
        return STATUS_CANCELADO

    if pending_amount <= ZERO:
        return STATUS_LIQUIDADO

    if due_date and due_date < timezone.localdate():
        return STATUS_VENCIDO

    if realized_amount > ZERO:
        return STATUS_PARCIAL

    return STATUS_PENDENTE


def _rotulo_status_liquidacao(status):
    return {
        STATUS_PENDENTE: "Pendente",
        STATUS_PARCIAL: "Parcial",
        STATUS_VENCIDO: "Vencido",
        STATUS_LIQUIDADO: "Liquidado",
        STATUS_CANCELADO: "Cancelado",
    }.get(status, status)


def _filtrar_itens_obrigacoes(itens, filtros):
    source = filtros.get("source") or filtros.get("origin") or filtros.get("origem")
    sources = set(filtros.get("sources") or [])
    cash_flow_group = filtros.get("cashFlowGroup") or filtros.get("fluxo")
    nature = filtros.get("nature") or filtros.get("natureza")
    status = filtros.get("status") or filtros.get("settlementStatus") or filtros.get("situacao")
    search = (filtros.get("search") or filtros.get("busca") or "").strip().lower()

    filtrados = []
    for item in itens:
        if source and item["source"] != source:
            continue
        if sources and item["source"] not in sources:
            continue
        if cash_flow_group and item["cash_flow_group"] != cash_flow_group:
            continue
        if nature and item["nature"] != nature:
            continue
        if status and status not in {item["status"], item["settlement_status"]}:
            continue
        if search and not _item_contem_busca(item, search):
            continue
        filtrados.append(item)

    return filtrados


def _filtrar_itens_reconciliacao(itens, filtros):
    status = (
        filtros.get("reconciliationStatus")
        or filtros.get("reconciliation_status")
        or filtros.get("statusConciliacao")
        or filtros.get("conciliacao")
    )
    if status not in {"conciliado", "divergente"}:
        return itens

    return [item for item in itens if item["reconciliation_status"] == status]


def _filtrar_itens_diagnostico_reconciliacao(itens, filtros):
    diagnostico = (
        filtros.get("reconciliationDiagnosis")
        or filtros.get("reconciliation_diagnosis")
        or filtros.get("diagnosticoConciliacao")
        or filtros.get("diagnostico_conciliacao")
    )
    if diagnostico not in RECONCILIACAO_DIAGNOSTICOS:
        return itens

    return [
        item for item in itens
        if item.get("reconciliation_diagnosis") == diagnostico
    ]


def _filtrar_itens_excedente_realizado(itens, filtros):
    filtro = (
        filtros.get("realizedAbovePlanned")
        or filtros.get("realized_above_planned")
        or filtros.get("overRealized")
        or filtros.get("over_realized")
        or filtros.get("excedenteRealizado")
        or filtros.get("excedente_realizado")
    )
    if filtro == "with":
        return [item for item in itens if item.get("over_realized_amount", ZERO) > ZERO]
    if filtro == "without":
        return [item for item in itens if item.get("over_realized_amount", ZERO) <= ZERO]
    return itens


def _item_contem_busca(item, search):
    campos = (
        item["description"],
        item["reference"],
        item["source_label"],
        item["source_detail_label"],
        item["client_name"],
        item["contract_code"],
        item["event_name"],
        item["event_number"],
    )
    return any(search in str(campo or "").lower() for campo in campos)


def _aplicar_reconciliacao_lancamentos(itens):
    totais = {}
    _adicionar_totais_lancamentos_diretos(
        totais,
        itens,
        ORIGEM_RECEITA_OPERACIONAL,
        "receita_operacional",
    )
    _adicionar_totais_lancamentos_diretos(
        totais,
        itens,
        ORIGEM_DESPESA_OPERACIONAL,
        "despesa_operacional",
    )
    _adicionar_totais_lancamentos_diretos(
        totais,
        itens,
        ORIGEM_CUSTO_FIXO,
        "custo_fixo",
    )
    _adicionar_totais_lancamentos_diretos(
        totais,
        itens,
        ORIGEM_INVESTIMENTO,
        "investimento",
    )
    _adicionar_totais_lancamentos_diretos(
        totais,
        itens,
        ORIGEM_FINANCIAMENTO,
        "financiamento_movimentacao",
    )
    _adicionar_totais_lancamentos_custos_servico(totais, itens)
    _adicionar_totais_lancamentos_pagamentos(
        totais,
        itens,
        ORIGEM_CUSTO_EXTRA,
        "pagamento_custo_extra__custo_extra_id",
    )
    _adicionar_totais_lancamentos_pagamentos(
        totais,
        itens,
        ORIGEM_PARCELA_DIVIDA,
        "pagamento_parcela_divida__parcela_id",
    )

    for item in itens:
        total = totais.get(_chave_reconciliacao_item(item), _total_lancamento_vazio())
        valor_origem = item["realized_amount"]
        pendente_origem = item["pending_amount"]
        excedente_origem = _calcular_excedente_realizado(item["planned_amount"], valor_origem)
        valor_ledger = quantizar_moeda(total["valor"])
        excedente_ledger = _calcular_excedente_realizado(item["planned_amount"], valor_ledger)
        diferenca = quantizar_moeda(valor_ledger - valor_origem)
        reconciliado = diferenca == ZERO
        pendente_ledger = _calcular_pendente_ledger(item, valor_ledger)
        status_ledger, rotulo_ledger, vencido_ledger, dias_vencido_ledger = (
            _campos_liquidacao_base(item, valor_ledger, pendente_ledger)
        )
        item["origin_realized_amount"] = valor_origem
        item["origin_pending_amount"] = pendente_origem
        item["origin_over_realized_amount"] = excedente_origem
        item["realized_amount_source"] = "origin"
        item["ledger_realized_amount"] = valor_ledger
        item["ledger_pending_amount"] = pendente_ledger
        item["ledger_over_realized_amount"] = excedente_ledger
        item["ledger_settlement_status"] = status_ledger
        item["ledger_settlement_status_label"] = rotulo_ledger
        item["ledger_is_overdue"] = vencido_ledger
        item["ledger_days_overdue"] = dias_vencido_ledger
        item["ledger_entry_count"] = total["quantidade"]
        item["realized_amount_difference"] = diferenca
        item["is_ledger_reconciled"] = reconciliado
        item["reconciliation_status"] = "conciliado" if reconciliado else "divergente"
        diagnostico = _diagnosticar_reconciliacao(
            valor_origem,
            valor_ledger,
            total["quantidade"],
            reconciliado,
        )
        item["reconciliation_diagnosis"] = diagnostico
        item["reconciliation_diagnosis_label"] = RECONCILIACAO_DIAGNOSTICOS[diagnostico]


def _diagnosticar_reconciliacao(valor_origem, valor_ledger, quantidade_lancamentos, reconciliado):
    if reconciliado:
        return "conciliado"

    if valor_origem > ZERO and quantidade_lancamentos == 0:
        return "ledger_sem_lancamento"

    if valor_origem == ZERO and valor_ledger != ZERO:
        return "origem_sem_realizado"

    if valor_ledger < valor_origem:
        return "ledger_menor_que_origem"

    if valor_ledger > valor_origem:
        return "ledger_maior_que_origem"

    return "divergencia_valor"


def _aplicar_base_realizado(itens, filtros):
    if filtros.get("realizedAmountBasis") != "ledger":
        return

    for item in itens:
        item["realized_amount"] = item.get("ledger_realized_amount", ZERO)
        item["pending_amount"] = item.get("ledger_pending_amount", ZERO)
        item["over_realized_amount"] = item.get("ledger_over_realized_amount", ZERO)
        item["realized_amount_source"] = "ledger"
        item["settlement_status"] = item.get(
            "ledger_settlement_status",
            item["settlement_status"],
        )
        item["settlement_status_label"] = item.get(
            "ledger_settlement_status_label",
            item["settlement_status_label"],
        )
        item["is_overdue"] = item.get("ledger_is_overdue", item["is_overdue"])
        item["days_overdue"] = item.get("ledger_days_overdue", item["days_overdue"])


def _calcular_pendente_ledger(item, valor_ledger):
    if item["status"] == STATUS_CANCELADO:
        return ZERO
    return max(quantizar_moeda(item["planned_amount"] - valor_ledger), ZERO)


def _calcular_excedente_realizado(valor_previsto, valor_realizado):
    return max(quantizar_moeda(valor_realizado - valor_previsto), ZERO)


def _campos_liquidacao_base(item, realized_amount, pending_amount):
    settlement_status = _status_liquidacao(
        item["status"],
        realized_amount,
        pending_amount,
        item["due_date"],
    )
    today = timezone.localdate()
    is_overdue = bool(item["due_date"] and item["due_date"] < today and pending_amount > ZERO)
    days_overdue = (today - item["due_date"]).days if is_overdue else 0
    return (
        settlement_status,
        _rotulo_status_liquidacao(settlement_status),
        is_overdue,
        days_overdue,
    )


def _adicionar_totais_lancamentos_diretos(totais, itens, origem, campo_origem):
    ids = _ids_por_origem(itens, origem)
    if not ids:
        return

    campo_id = f"{campo_origem}_id"
    for linha in _query_lancamentos_realizados(**{f"{campo_id}__in": ids}).values(
        campo_id
    ).annotate(valor=Sum("valor"), quantidade=Count("id")):
        totais[(origem, linha[campo_id], "")] = _total_lancamento(
            linha["valor"],
            linha["quantidade"],
        )


def _adicionar_totais_lancamentos_custos_servico(totais, itens):
    ids = _ids_por_origem(itens, ORIGEM_CUSTO_SERVICO)
    if not ids:
        return

    for linha in _query_lancamentos_realizados(
        pagamento_custo_servico__custo_servico_id__in=ids,
    ).values(
        "pagamento_custo_servico__custo_servico_id",
        "pagamento_custo_servico__tipo",
    ).annotate(valor=Sum("valor"), quantidade=Count("id")):
        totais[
            (
                ORIGEM_CUSTO_SERVICO,
                linha["pagamento_custo_servico__custo_servico_id"],
                linha["pagamento_custo_servico__tipo"],
            )
        ] = _total_lancamento(linha["valor"], linha["quantidade"])


def _adicionar_totais_lancamentos_pagamentos(totais, itens, origem, campo_origem):
    ids = _ids_por_origem(itens, origem)
    if not ids:
        return

    for linha in _query_lancamentos_realizados(**{f"{campo_origem}__in": ids}).values(
        campo_origem
    ).annotate(valor=Sum("valor"), quantidade=Count("id")):
        totais[(origem, linha[campo_origem], "")] = _total_lancamento(
            linha["valor"],
            linha["quantidade"],
        )


def _deve_carregar_origem(filtros, origem):
    origem_filtro = filtros.get("source") or filtros.get("origin") or filtros.get("origem")
    origens_filtro = set(filtros.get("sources") or [])
    return (
        (not origem_filtro and not origens_filtro)
        or origem_filtro == origem
        or origem in origens_filtro
    )


def _possui_filtro_operacional(filtros):
    return bool(
        filtros.get("contractCode")
        or filtros.get("contrato_codigo")
        or filtros.get("eventId")
        or filtros.get("costCenterId")
        or filtros.get("evento")
        or filtros.get("evento_id")
        or filtros.get("clientId")
        or filtros.get("cliente")
        or filtros.get("cliente_id")
    )


def filtro_operacional_invalido(filtros):
    return any(
        filtros.get(nome) == "__invalid__"
        for nome in ("eventId", "clientId")
    )


def _aplicar_periodo(queryset, campo, filtros):
    data_inicial = filtros.get("startDate") or filtros.get("data_inicial")
    data_final = filtros.get("endDate") or filtros.get("data_final")

    if data_inicial:
        queryset = queryset.filter(**{f"{campo}__gte": data_inicial})

    if data_final:
        queryset = queryset.filter(**{f"{campo}__lte": data_final})

    return queryset


def _aplicar_filtros_evento(queryset, filtros, campo_evento):
    evento_id = (
        filtros.get("eventId")
        or filtros.get("costCenterId")
        or filtros.get("evento")
        or filtros.get("evento_id")
    )
    if evento_id:
        return queryset.filter(**{campo_evento: evento_id})
    return queryset


def _aplicar_filtros_cliente_evento(queryset, filtros, campo_cliente):
    cliente_id = filtros.get("clientId") or filtros.get("cliente") or filtros.get("cliente_id")
    if cliente_id:
        return queryset.filter(**{campo_cliente: cliente_id})
    return queryset


def _aplicar_filtros_contrato_evento(queryset, filtros, campo_contrato):
    contrato_codigo = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    if contrato_codigo:
        return queryset.filter(
            montar_filtro_evento_por_contrato_visual(
                campo_contrato,
                contrato_codigo,
            )
        )
    return queryset


def _aplicar_filtros_cliente_dimensao(queryset, filtros, campo_cliente_contrato, campo_cliente_evento):
    cliente_id = filtros.get("clientId") or filtros.get("cliente") or filtros.get("cliente_id")
    if cliente_id:
        return queryset.filter(
            Q(**{campo_cliente_contrato: cliente_id}) | Q(**{campo_cliente_evento: cliente_id})
        )
    return queryset


def _aplicar_filtros_contrato_dimensao(queryset, filtros, campo_contrato, campo_contrato_evento):
    contrato_codigo = filtros.get("contractCode") or filtros.get("contrato_codigo") or ""
    if contrato_codigo:
        return queryset.filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                campo_contrato_evento,
                contrato_codigo,
            )
        )
    return queryset


def _novo_resumo():
    return {
        "planned_amount": ZERO,
        "realized_amount": ZERO,
        "over_realized_amount": ZERO,
        "pending_amount": ZERO,
        "origin_realized_amount": ZERO,
        "origin_pending_amount": ZERO,
        "origin_over_realized_amount": ZERO,
        "ledger_realized_amount": ZERO,
        "ledger_pending_amount": ZERO,
        "ledger_over_realized_amount": ZERO,
        "realized_amount_difference": ZERO,
        "reconciled_count": 0,
        "divergent_count": 0,
        "overdue_amount": ZERO,
        "count": 0,
        "pending_count": 0,
        "overdue_count": 0,
        "liquidated_count": 0,
        "ledger_pending_count": 0,
        "ledger_overdue_count": 0,
        "ledger_liquidated_count": 0,
        "ledger_overdue_amount": ZERO,
    }


def _somar_item_resumo(resumo, item):
    resumo["planned_amount"] += item["planned_amount"]
    resumo["realized_amount"] += item["realized_amount"]
    resumo["over_realized_amount"] += item.get("over_realized_amount", ZERO)
    resumo["pending_amount"] += item["pending_amount"]
    resumo["origin_realized_amount"] += item.get(
        "origin_realized_amount",
        item["realized_amount"],
    )
    resumo["origin_pending_amount"] += item.get(
        "origin_pending_amount",
        item["pending_amount"],
    )
    resumo["origin_over_realized_amount"] += item.get(
        "origin_over_realized_amount",
        item.get("over_realized_amount", ZERO),
    )
    resumo["count"] += 1
    resumo["ledger_realized_amount"] += item.get("ledger_realized_amount", ZERO)
    resumo["ledger_pending_amount"] += item.get("ledger_pending_amount", ZERO)
    resumo["ledger_over_realized_amount"] += item.get(
        "ledger_over_realized_amount",
        ZERO,
    )
    resumo["realized_amount_difference"] += item.get(
        "realized_amount_difference",
        ZERO,
    )
    resumo["reconciled_count"] += 1 if item.get("is_ledger_reconciled") else 0
    resumo["divergent_count"] += 1 if not item.get("is_ledger_reconciled") else 0

    if item["pending_amount"] > ZERO:
        resumo["pending_count"] += 1

    if item["is_overdue"]:
        resumo["overdue_count"] += 1
        resumo["overdue_amount"] += item["pending_amount"]

    if item["settlement_status"] == STATUS_LIQUIDADO:
        resumo["liquidated_count"] += 1

    if item.get("ledger_pending_amount", ZERO) > ZERO:
        resumo["ledger_pending_count"] += 1

    if item.get("ledger_is_overdue"):
        resumo["ledger_overdue_count"] += 1
        resumo["ledger_overdue_amount"] += item.get("ledger_pending_amount", ZERO)

    if item.get("ledger_settlement_status") == STATUS_LIQUIDADO:
        resumo["ledger_liquidated_count"] += 1


def _serializar_resumo_decimal(resumo):
    return {
        "planned_amount": quantizar_moeda(resumo["planned_amount"]),
        "realized_amount": quantizar_moeda(resumo["realized_amount"]),
        "over_realized_amount": quantizar_moeda(resumo["over_realized_amount"]),
        "pending_amount": quantizar_moeda(resumo["pending_amount"]),
        "origin_realized_amount": quantizar_moeda(resumo["origin_realized_amount"]),
        "origin_pending_amount": quantizar_moeda(resumo["origin_pending_amount"]),
        "origin_over_realized_amount": quantizar_moeda(
            resumo["origin_over_realized_amount"]
        ),
        "ledger_realized_amount": quantizar_moeda(resumo["ledger_realized_amount"]),
        "ledger_pending_amount": quantizar_moeda(resumo["ledger_pending_amount"]),
        "ledger_over_realized_amount": quantizar_moeda(
            resumo["ledger_over_realized_amount"]
        ),
        "realized_amount_difference": quantizar_moeda(
            resumo["realized_amount_difference"]
        ),
        "reconciled_count": resumo["reconciled_count"],
        "divergent_count": resumo["divergent_count"],
        "overdue_amount": quantizar_moeda(resumo["overdue_amount"]),
        "count": resumo["count"],
        "pending_count": resumo["pending_count"],
        "overdue_count": resumo["overdue_count"],
        "liquidated_count": resumo["liquidated_count"],
        "ledger_pending_count": resumo["ledger_pending_count"],
        "ledger_overdue_count": resumo["ledger_overdue_count"],
        "ledger_liquidated_count": resumo["ledger_liquidated_count"],
        "ledger_overdue_amount": quantizar_moeda(resumo["ledger_overdue_amount"]),
    }


def _ids_por_origem(itens, origem):
    return {item["source_id"] for item in itens if item["source"] == origem}


def _chave_reconciliacao_item(item):
    if item["source"] == ORIGEM_CUSTO_SERVICO:
        return (item["source"], item["source_id"], item["source_detail"])
    return (item["source"], item["source_id"], "")


def _query_lancamentos_realizados(**filtros):
    return LancamentoFinanceiro.objects.filter(
        status=STATUS_REALIZADO,
        **filtros,
    )


def _total_lancamento(valor, quantidade):
    return {
        "valor": quantizar_moeda(valor or ZERO),
        "quantidade": quantidade or 0,
    }


def _total_lancamento_vazio():
    return _total_lancamento(ZERO, 0)
