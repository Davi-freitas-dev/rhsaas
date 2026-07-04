from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from .constants_financeiros import (
    TIPO_CUSTO_ALIMENTACAO,
    TIPO_CUSTO_DIARIAS,
    TIPO_CUSTO_TRANSPORTE,
)
from .models import DespesaOperacional
from .services_dimensoes_operacionais import (
    relacao_carregada,
    serializar_dimensao_operacional_financeira,
)
from .utils_financeiros import decimal_zero, quantizar_moeda


NOMES_CATEGORIAS_DESPESA = dict(DespesaOperacional.CATEGORIA_CHOICES)


def montar_custos_por_evento_dashboard(
    custos_evento,
    custos_extras,
    despesas,
    receitas_por_evento,
    receitas_recebidas_por_evento,
    despesas_pagas_por_evento,
):
    despesas_operacionais_por_evento = agrupar_despesas_operacionais_por_evento(despesas)
    custos_por_servico_raw = list(
        custos_evento
        .values(
            "evento_id",
            "evento__nome_evento",
            "evento__data_inicio",
            "servico__nome",
        )
        .annotate(
            total_diarias=Sum("valor_diarias"),
            total_alimentacao=Sum("valor_alimentacao"),
            total_transporte=Sum("valor_transporte"),
        )
        .order_by(
            "evento__data_inicio",
            "evento__nome_evento",
            "evento_id",
            "servico__nome",
        )
    )

    pagos_por_item = resumir_pagamentos_custos_servico_por_item(custos_evento)

    for item in custos_por_servico_raw:
        _preparar_item_custo_servico(item, pagos_por_item)

    custos_extras_raw = list(
        custos_extras
        .values(
            "evento_id",
            "evento__nome_evento",
            "evento__data_inicio",
        )
        .annotate(
            total_extra=Sum("valor_previsto"),
        )
        .order_by("evento__data_inicio", "evento__nome_evento")
    )

    extras_por_evento = {
        item["evento_id"]: quantizar_moeda(item["total_extra"])
        for item in custos_extras_raw
    }
    eventos_info_extras = {
        item["evento_id"]: {
            "evento_nome": item["evento__nome_evento"],
            "data_inicio": item["evento__data_inicio"],
        }
        for item in custos_extras_raw
    }
    resumo_extras = resumir_pagamentos_custos_extras_por_evento(custos_extras)
    pagos_extras_por_evento = resumo_extras["pagos_por_evento"]
    valores_pendentes_extras_por_evento = resumo_extras["valores_pendentes_por_evento"]

    custos_por_evento = []
    evento_atual_id = None
    grupo_atual = None
    eventos_processados = set()

    for item in custos_por_servico_raw:
        if item["evento_id"] != evento_atual_id:
            if grupo_atual:
                grupo_atual = finalizar_grupo_custos_evento(
                    grupo_atual,
                    extras_por_evento,
                    pagos_extras_por_evento,
                    valores_pendentes_extras_por_evento,
                    despesas_operacionais_por_evento,
                    receitas_por_evento,
                    receitas_recebidas_por_evento,
                    despesas_pagas_por_evento,
                )
                custos_por_evento.append(grupo_atual)
                eventos_processados.add(grupo_atual["evento_id"])

            grupo_atual = _novo_grupo_custos_evento(
                item["evento_id"],
                item["evento__nome_evento"],
                item["evento__data_inicio"],
            )
            evento_atual_id = item["evento_id"]

        grupo_atual["itens"].append(item)
        grupo_atual["subtotal_diarias"] += item["total_diarias"]
        grupo_atual["subtotal_alimentacao"] += item["total_alimentacao"]
        grupo_atual["subtotal_transporte"] += item["total_transporte"]

    if grupo_atual:
        grupo_atual = finalizar_grupo_custos_evento(
            grupo_atual,
            extras_por_evento,
            pagos_extras_por_evento,
            valores_pendentes_extras_por_evento,
            despesas_operacionais_por_evento,
            receitas_por_evento,
            receitas_recebidas_por_evento,
            despesas_pagas_por_evento,
        )
        custos_por_evento.append(grupo_atual)
        eventos_processados.add(grupo_atual["evento_id"])

    for evento_extra_id, total_extra in extras_por_evento.items():
        if evento_extra_id in eventos_processados:
            continue

        info_evento = eventos_info_extras.get(evento_extra_id, {})
        grupo_extra = _novo_grupo_custos_evento(
            evento_extra_id,
            info_evento.get("evento_nome", "Evento"),
            info_evento.get("data_inicio"),
        )
        grupo_extra = finalizar_grupo_custos_evento(
            grupo_extra,
            extras_por_evento,
            pagos_extras_por_evento,
            valores_pendentes_extras_por_evento,
            despesas_operacionais_por_evento,
            receitas_por_evento,
            receitas_recebidas_por_evento,
            despesas_pagas_por_evento,
        )
        custos_por_evento.append(grupo_extra)
        eventos_processados.add(evento_extra_id)

    for evento_id, despesas_manuais in despesas_operacionais_por_evento.items():
        if evento_id in eventos_processados:
            continue

        if (
            despesas_manuais.get("previsto", Decimal("0.00")) <= Decimal("0.00")
            and despesas_manuais.get("pago", Decimal("0.00")) <= Decimal("0.00")
        ):
            continue

        grupo_manual = _novo_grupo_custos_evento(
            evento_id,
            despesas_manuais["evento_nome"],
            despesas_manuais["data_inicio"],
        )
        grupo_manual = finalizar_grupo_custos_evento(
            grupo_manual,
            extras_por_evento,
            pagos_extras_por_evento,
            valores_pendentes_extras_por_evento,
            despesas_operacionais_por_evento,
            receitas_por_evento,
            receitas_recebidas_por_evento,
            despesas_pagas_por_evento,
        )
        custos_por_evento.append(grupo_manual)

    custos_por_evento.sort(
        key=lambda grupo: (
            grupo["data_inicio"] or timezone.localdate(),
            grupo["evento_nome"] or "",
        )
    )

    total_valor_pendente_eventos = quantizar_moeda(sum(
        (grupo["subtotal_valor_pendente_geral"] for grupo in custos_por_evento),
        Decimal("0.00"),
    ))

    return {
        "custos_por_evento": custos_por_evento,
        "total_receita_eventos_custos": quantizar_moeda(sum(
            (grupo["receita_evento"] for grupo in custos_por_evento),
            Decimal("0.00"),
        )),
        "total_custo_previsto_eventos": quantizar_moeda(sum(
            (grupo["subtotal_geral"] for grupo in custos_por_evento),
            Decimal("0.00"),
        )),
        "total_pago_eventos": quantizar_moeda(sum(
            (grupo["subtotal_pago_geral"] for grupo in custos_por_evento),
            Decimal("0.00"),
        )),
        "total_saldo_eventos": total_valor_pendente_eventos,
        "total_valor_pendente_eventos": total_valor_pendente_eventos,
        "total_contas_pendentes_eventos": total_valor_pendente_eventos,
        "total_lucro_eventos_custos": quantizar_moeda(sum(
            (grupo["lucro_evento"] for grupo in custos_por_evento),
            Decimal("0.00"),
        )),
        "total_lucro_previsto_eventos": quantizar_moeda(sum(
            (grupo["lucro_previsto"] for grupo in custos_por_evento),
            Decimal("0.00"),
        )),
        "total_lucro_real_eventos": quantizar_moeda(sum(
            (grupo["lucro_real"] for grupo in custos_por_evento),
            Decimal("0.00"),
        )),
    }


def resumir_pagamentos_custos_servico_por_item(custos_evento):
    pagos_por_item = {}

    for item in custos_evento.values(
        "evento_id",
        "servico__nome",
        "valor_diarias",
        "valor_alimentacao",
        "valor_transporte",
        "diarias_quitadas",
        "alimentacao_quitada",
        "transporte_quitado",
    ).annotate(
        pago_diarias=Sum(
            "pagamentos__valor_pagamento",
            filter=Q(pagamentos__tipo=TIPO_CUSTO_DIARIAS),
        ),
        pago_alimentacao=Sum(
            "pagamentos__valor_pagamento",
            filter=Q(pagamentos__tipo=TIPO_CUSTO_ALIMENTACAO),
        ),
        pago_transporte=Sum(
            "pagamentos__valor_pagamento",
            filter=Q(pagamentos__tipo=TIPO_CUSTO_TRANSPORTE),
        ),
        pago_total=Sum("pagamentos__valor_pagamento"),
    ):
        pago_diarias = quantizar_moeda(decimal_zero(item["pago_diarias"]))
        pago_alimentacao = quantizar_moeda(decimal_zero(item["pago_alimentacao"]))
        pago_transporte = quantizar_moeda(decimal_zero(item["pago_transporte"]))
        pago_total = quantizar_moeda(decimal_zero(item["pago_total"]))

        saldo_diarias = _saldo_custo_servico(
            item["valor_diarias"],
            pago_diarias,
            item["diarias_quitadas"],
        )
        saldo_alimentacao = _saldo_custo_servico(
            item["valor_alimentacao"],
            pago_alimentacao,
            item["alimentacao_quitada"],
        )
        saldo_transporte = _saldo_custo_servico(
            item["valor_transporte"],
            pago_transporte,
            item["transporte_quitado"],
        )

        chave = (item["evento_id"], item["servico__nome"])
        valor_pendente_total = quantizar_moeda(
            saldo_diarias + saldo_alimentacao + saldo_transporte
        )
        pagos_por_item[chave] = {
            "pago_diarias": pago_diarias,
            "pago_alimentacao": pago_alimentacao,
            "pago_transporte": pago_transporte,
            "pago_total": pago_total,
            "saldo_total": valor_pendente_total,
            "valor_pendente_total": valor_pendente_total,
            "contas_pendentes_total": valor_pendente_total,
        }

    return pagos_por_item


def _saldo_custo_servico(valor_previsto, valor_pago, quitado):
    if quitado:
        return Decimal("0.00")

    return quantizar_moeda(decimal_zero(valor_previsto) - decimal_zero(valor_pago))


def resumir_pagamentos_custos_extras_por_evento(custos_extras):
    pagos_por_evento = {}
    valores_pendentes_por_evento = {}

    for item in custos_extras.values(
        "id",
        "evento_id",
        "valor_previsto",
        "quitado",
    ).annotate(
        total_pago=Sum("pagamentos__valor_pagamento"),
    ):
        evento_id = item["evento_id"]
        total_pago = quantizar_moeda(decimal_zero(item["total_pago"]))
        valor_pendente = (
            Decimal("0.00")
            if item["quitado"]
            else quantizar_moeda(decimal_zero(item["valor_previsto"]) - total_pago)
        )

        pagos_por_evento[evento_id] = quantizar_moeda(
            pagos_por_evento.get(evento_id, Decimal("0.00")) + total_pago
        )
        valores_pendentes_por_evento[evento_id] = quantizar_moeda(
            valores_pendentes_por_evento.get(evento_id, Decimal("0.00")) + valor_pendente
        )

    return {
        "pagos_por_evento": pagos_por_evento,
        "saldos_por_evento": valores_pendentes_por_evento,
        "valores_pendentes_por_evento": valores_pendentes_por_evento,
        "contas_pendentes_por_evento": valores_pendentes_por_evento,
    }


def agrupar_despesas_operacionais_por_evento(despesas):
    despesas_por_evento = {}

    for despesa in despesas:
        evento = relacao_carregada(despesa, "evento")
        dimensao = serializar_dimensao_operacional_financeira(despesa)
        grupo = despesas_por_evento.setdefault(
            despesa.evento_id,
            {
                "evento_nome": dimensao["eventName"],
                "data_inicio": getattr(evento, "data_inicio", None),
                "previsto": Decimal("0.00"),
                "pago": Decimal("0.00"),
                "saldo": Decimal("0.00"),
                "valor_pendente": Decimal("0.00"),
                "contas_pendentes": Decimal("0.00"),
                "breakdown_por_categoria": {},
                "breakdown_por_origem": {},
            },
        )
        valor_previsto = decimal_zero(despesa.valor_previsto)
        valor_pago = decimal_zero(despesa.valor_pago)
        valor_pendente = decimal_zero(despesa.saldo_a_pagar)
        origem = despesa.origem_pagamento
        categoria, categoria_nome, descricao = _dados_breakdown_despesa_operacional(
            despesa
        )
        categorias_origem = grupo["breakdown_por_origem"].setdefault(origem, {})
        grupo_categoria_origem = categorias_origem.setdefault(
            categoria,
            _novo_breakdown_categoria(categoria, categoria_nome),
        )
        _adicionar_valores_breakdown(
            grupo_categoria_origem,
            valor_previsto,
            valor_pago,
            valor_pendente,
        )
        grupo_categoria_origem["items"].append({
            "description": descricao,
            "plannedAmount": quantizar_moeda(valor_previsto),
            "realizedAmount": quantizar_moeda(valor_pago),
            "pendingAmount": quantizar_moeda(valor_pendente),
        })

        if origem != DespesaOperacional.ORIGEM_MANUAL:
            continue

        grupo["previsto"] += valor_previsto
        grupo["pago"] += valor_pago
        grupo["saldo"] += valor_pendente
        grupo["valor_pendente"] += valor_pendente
        grupo["contas_pendentes"] += valor_pendente
        grupo_categoria = grupo["breakdown_por_categoria"].setdefault(
            categoria,
            _novo_breakdown_categoria(categoria, categoria_nome),
        )
        _adicionar_valores_breakdown(
            grupo_categoria,
            valor_previsto,
            valor_pago,
            valor_pendente,
        )
        grupo_categoria["items"].append({
            "description": descricao,
            "plannedAmount": quantizar_moeda(valor_previsto),
            "realizedAmount": quantizar_moeda(valor_pago),
            "pendingAmount": quantizar_moeda(valor_pendente),
        })

    for grupo in despesas_por_evento.values():
        grupo["previsto"] = quantizar_moeda(grupo["previsto"])
        grupo["pago"] = quantizar_moeda(grupo["pago"])
        grupo["saldo"] = quantizar_moeda(grupo["saldo"])
        grupo["valor_pendente"] = quantizar_moeda(grupo["valor_pendente"])
        grupo["contas_pendentes"] = quantizar_moeda(grupo["contas_pendentes"])
        grupo["breakdown"] = _finalizar_breakdown_categorias(
            grupo["breakdown_por_categoria"]
        )
        grupo["breakdown_por_origem"] = {
            origem: _finalizar_breakdown_categorias(categorias)
            for origem, categorias in grupo["breakdown_por_origem"].items()
        }

    return despesas_por_evento


def _dados_breakdown_despesa_operacional(despesa):
    if (
        despesa.origem_pagamento == DespesaOperacional.ORIGEM_CUSTO_EXTRA
        and despesa.origem_custo_extra_id
    ):
        custo_extra = despesa.origem_custo_extra
        categoria = custo_extra.categoria or "outros"
        return (
            categoria,
            custo_extra.get_categoria_display() or categoria,
            custo_extra.descricao or despesa.descricao,
        )

    categoria = despesa.categoria or "outros"
    return (
        categoria,
        NOMES_CATEGORIAS_DESPESA.get(categoria, categoria),
        despesa.descricao or NOMES_CATEGORIAS_DESPESA.get(categoria, categoria),
    )


def _novo_breakdown_categoria(categoria, categoria_nome):
    return {
        "category": categoria,
        "categoryLabel": categoria_nome,
        "plannedAmount": Decimal("0.00"),
        "realizedAmount": Decimal("0.00"),
        "pendingAmount": Decimal("0.00"),
        "items": [],
    }


def _adicionar_valores_breakdown(
    grupo_categoria,
    valor_previsto,
    valor_pago,
    valor_pendente,
):
    grupo_categoria["plannedAmount"] += decimal_zero(valor_previsto)
    grupo_categoria["realizedAmount"] += decimal_zero(valor_pago)
    grupo_categoria["pendingAmount"] += decimal_zero(valor_pendente)


def _finalizar_breakdown_categorias(categorias):
    breakdown = []

    for grupo_categoria in categorias.values():
        grupo_categoria["plannedAmount"] = quantizar_moeda(
            grupo_categoria["plannedAmount"]
        )
        grupo_categoria["realizedAmount"] = quantizar_moeda(
            grupo_categoria["realizedAmount"]
        )
        grupo_categoria["pendingAmount"] = quantizar_moeda(
            grupo_categoria["pendingAmount"]
        )
        grupo_categoria["items"].sort(key=lambda item: item["description"] or "")
        breakdown.append(grupo_categoria)

    breakdown.sort(key=lambda item: item["categoryLabel"] or item["category"])
    return breakdown


def _preparar_item_custo_servico(item, pagos_por_item):
    item["total_diarias"] = decimal_zero(item["total_diarias"])
    item["total_alimentacao"] = decimal_zero(item["total_alimentacao"])
    item["total_transporte"] = decimal_zero(item["total_transporte"])
    item["total_custos_extras"] = Decimal("0.00")
    item["eh_custo_extra"] = False

    item["total_geral"] = (
        item["total_diarias"]
        + item["total_alimentacao"]
        + item["total_transporte"]
    )
    item["total_geral"] = quantizar_moeda(item["total_geral"])

    chave = (item["evento_id"], item["servico__nome"])
    pagos_item = pagos_por_item.get(chave, {})

    item["pago_diarias"] = pagos_item.get("pago_diarias", Decimal("0.00"))
    item["pago_alimentacao"] = pagos_item.get("pago_alimentacao", Decimal("0.00"))
    item["pago_transporte"] = pagos_item.get("pago_transporte", Decimal("0.00"))
    item["pago_total"] = pagos_item.get("pago_total", Decimal("0.00"))
    item["saldo_total"] = pagos_item.get(
        "saldo_total",
        quantizar_moeda(item["total_geral"] - item["pago_total"]),
    )
    item["valor_pendente_total"] = pagos_item.get(
        "valor_pendente_total",
        item["saldo_total"],
    )
    item["contas_pendentes_total"] = pagos_item.get(
        "contas_pendentes_total",
        item["valor_pendente_total"],
    )


def _novo_grupo_custos_evento(evento_id, evento_nome, data_inicio):
    return {
        "evento_id": evento_id,
        "evento_nome": evento_nome,
        "data_inicio": data_inicio,
        "itens": [],
        "subtotal_diarias": Decimal("0.00"),
        "subtotal_alimentacao": Decimal("0.00"),
        "subtotal_transporte": Decimal("0.00"),
        "subtotal_custos_extras": Decimal("0.00"),
        "subtotal_geral": Decimal("0.00"),
        "subtotal_pago_geral": Decimal("0.00"),
        "subtotal_saldo_geral": Decimal("0.00"),
        "subtotal_valor_pendente_geral": Decimal("0.00"),
        "subtotal_contas_pendentes_geral": Decimal("0.00"),
        "subtotal_valor_pendente_custos_extras": Decimal("0.00"),
        "subtotal_contas_pendentes_custos_extras": Decimal("0.00"),
        "custos_servico_breakdown": [],
        "custos_extras_breakdown": [],
        "despesas_manuais_breakdown": [],
        "receita_evento": Decimal("0.00"),
        "receita_recebida_evento": Decimal("0.00"),
        "lucro_previsto": Decimal("0.00"),
        "lucro_real": Decimal("0.00"),
        "lucro_evento": Decimal("0.00"),
    }


def finalizar_grupo_custos_evento(
    grupo,
    extras_por_evento,
    pagos_extras_por_evento,
    valores_pendentes_extras_por_evento,
    despesas_operacionais_por_evento,
    receitas_por_evento,
    receitas_recebidas_por_evento,
    despesas_pagas_por_evento,
):
    total_extra = quantizar_moeda(extras_por_evento.get(
        grupo["evento_id"],
        Decimal("0.00"),
    ))
    pago_extra = quantizar_moeda(pagos_extras_por_evento.get(
        grupo["evento_id"],
        Decimal("0.00"),
    ))
    valor_pendente_extra = quantizar_moeda(valores_pendentes_extras_por_evento.get(
        grupo["evento_id"],
        total_extra - pago_extra,
    ))
    despesas_operacionais = despesas_operacionais_por_evento.get(grupo["evento_id"], {})
    total_manual = quantizar_moeda(despesas_operacionais.get(
        "previsto",
        Decimal("0.00"),
    ))
    pago_manual = quantizar_moeda(despesas_operacionais.get(
        "pago",
        Decimal("0.00"),
    ))
    valor_pendente_manual = quantizar_moeda(despesas_operacionais.get(
        "valor_pendente",
        despesas_operacionais.get("saldo", total_manual - pago_manual),
    ))
    saldo_manual = quantizar_moeda(despesas_operacionais.get(
        "saldo",
        total_manual - pago_manual,
    ))
    breakdown_por_origem = despesas_operacionais.get("breakdown_por_origem", {})
    grupo["custos_servico_breakdown"] = breakdown_por_origem.get(
        DespesaOperacional.ORIGEM_CUSTO_SERVICO,
        [],
    )
    grupo["custos_extras_breakdown"] = breakdown_por_origem.get(
        DespesaOperacional.ORIGEM_CUSTO_EXTRA,
        [],
    )
    grupo["despesas_manuais_breakdown"] = despesas_operacionais.get("breakdown", [])

    grupo["subtotal_custos_extras"] = quantizar_moeda(total_extra + total_manual)
    grupo["subtotal_pago_custos_extras"] = quantizar_moeda(pago_extra + pago_manual)
    grupo["subtotal_valor_pendente_custos_extras"] = quantizar_moeda(
        valor_pendente_extra + valor_pendente_manual
    )
    grupo["subtotal_contas_pendentes_custos_extras"] = grupo[
        "subtotal_valor_pendente_custos_extras"
    ]
    grupo["subtotal_saldo_custos_extras"] = grupo["subtotal_valor_pendente_custos_extras"]

    if total_extra > Decimal("0.00"):
        grupo["itens"].append({
            "evento_id": grupo["evento_id"],
            "evento__nome_evento": grupo["evento_nome"],
            "evento__data_inicio": grupo["data_inicio"],
            "servico__nome": "Custos extras",
            "total_diarias": Decimal("0.00"),
            "total_alimentacao": Decimal("0.00"),
            "total_transporte": Decimal("0.00"),
            "total_custos_extras": total_extra,
            "total_geral": total_extra,
            "pago_diarias": Decimal("0.00"),
            "pago_alimentacao": Decimal("0.00"),
            "pago_transporte": Decimal("0.00"),
            "pago_total": pago_extra,
            "saldo_total": valor_pendente_extra,
            "valor_pendente_total": valor_pendente_extra,
            "contas_pendentes_total": valor_pendente_extra,
            "eh_custo_extra": True,
        })

    if total_manual > Decimal("0.00") or pago_manual > Decimal("0.00"):
        grupo["itens"].append({
            "evento_id": grupo["evento_id"],
            "evento__nome_evento": grupo["evento_nome"],
            "evento__data_inicio": grupo["data_inicio"],
            "servico__nome": "Despesas operacionais",
            "total_diarias": Decimal("0.00"),
            "total_alimentacao": Decimal("0.00"),
            "total_transporte": Decimal("0.00"),
            "total_custos_extras": total_manual,
            "total_geral": total_manual,
            "pago_diarias": Decimal("0.00"),
            "pago_alimentacao": Decimal("0.00"),
            "pago_transporte": Decimal("0.00"),
            "pago_total": pago_manual,
            "saldo_total": saldo_manual,
            "valor_pendente_total": valor_pendente_manual,
            "contas_pendentes_total": valor_pendente_manual,
            "eh_custo_extra": False,
            "eh_despesa_manual": True,
        })

    grupo["subtotal_geral"] = quantizar_moeda(
        grupo["subtotal_diarias"]
        + grupo["subtotal_alimentacao"]
        + grupo["subtotal_transporte"]
        + grupo["subtotal_custos_extras"]
    )

    subtotal_pago_itens = quantizar_moeda(sum(
        (item.get("pago_total", Decimal("0.00")) for item in grupo["itens"]),
        Decimal("0.00"),
    ))
    subtotal_pago_despesas = quantizar_moeda(despesas_pagas_por_evento.get(
        grupo["evento_id"],
        Decimal("0.00"),
    ))
    grupo["subtotal_pago_geral"] = max(subtotal_pago_itens, subtotal_pago_despesas)

    grupo["subtotal_valor_pendente_geral"] = quantizar_moeda(
        sum(
            (
                item.get(
                    "valor_pendente_total",
                    item.get("saldo_total", Decimal("0.00")),
                )
                for item in grupo["itens"]
            ),
            Decimal("0.00"),
        )
    )
    grupo["subtotal_saldo_geral"] = grupo["subtotal_valor_pendente_geral"]
    grupo["subtotal_contas_pendentes_geral"] = grupo["subtotal_valor_pendente_geral"]

    grupo["receita_evento"] = quantizar_moeda(receitas_por_evento.get(
        grupo["evento_id"],
        Decimal("0.00"),
    ))

    grupo["receita_recebida_evento"] = quantizar_moeda(receitas_recebidas_por_evento.get(
        grupo["evento_id"],
        Decimal("0.00"),
    ))

    grupo["lucro_previsto"] = quantizar_moeda(
        grupo["receita_evento"] - grupo["subtotal_geral"]
    )

    grupo["lucro_real"] = quantizar_moeda(
        grupo["receita_recebida_evento"] - grupo["subtotal_pago_geral"]
    )

    grupo["lucro_evento"] = grupo["lucro_previsto"]
    return grupo
