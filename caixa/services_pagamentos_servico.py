from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .constants_financeiros import TIPOS_CUSTO_SERVICO
from .models import DespesaOperacional
from .models_pagamentos import PagamentoEventoCustoServico
from .models_servico import EventoCustoServico
from .utils_forms import adicionar_erros_validacao
from .utils_financeiros import quantizar_moeda


MAPA_DESCRICAO = {
    "mao_obra": "Mão de obra prevista",
    "alimentacao": "Alimentação prevista",
    "transporte": "Transporte previsto",
}

MAPA_TIPO_CUSTO_SERVICO = {
    "mao_obra": "diarias",
    "alimentacao": "alimentacao",
    "transporte": "transporte",
}


def sincronizar_pagamentos_servico_com_despesas(evento):
    custos = list(EventoCustoServico.objects.filter(evento=evento))

    total_pago_diarias = sum(
        (custo.total_pago_diarias for custo in custos),
        Decimal("0.00")
    )

    total_pago_alimentacao = sum(
        (custo.total_pago_alimentacao for custo in custos),
        Decimal("0.00")
    )

    total_pago_transporte = sum(
        (custo.total_pago_transporte for custo in custos),
        Decimal("0.00")
    )
    total_diarias = sum((custo.valor_diarias for custo in custos), Decimal("0.00"))
    total_alimentacao = sum((custo.valor_alimentacao for custo in custos), Decimal("0.00"))
    total_transporte = sum((custo.valor_transporte for custo in custos), Decimal("0.00"))
    diarias_quitadas = total_diarias > Decimal("0.00") and sum(
        (custo.saldo_diarias for custo in custos),
        Decimal("0.00"),
    ) <= Decimal("0.00")
    alimentacao_quitada = total_alimentacao > Decimal("0.00") and sum(
        (custo.saldo_alimentacao for custo in custos),
        Decimal("0.00"),
    ) <= Decimal("0.00")
    transporte_quitado = total_transporte > Decimal("0.00") and sum(
        (custo.saldo_transporte for custo in custos),
        Decimal("0.00"),
    ) <= Decimal("0.00")
    motivo_diarias = motivo_baixa_custos_servico(custos, "diarias_quitadas")
    motivo_alimentacao = motivo_baixa_custos_servico(custos, "alimentacao_quitada")
    motivo_transporte = motivo_baixa_custos_servico(custos, "transporte_quitado")

    atualizar_despesa_pago(
        evento=evento,
        categoria="mao_obra",
        valor_pago_total=total_pago_diarias,
        quitado=diarias_quitadas,
        motivo_baixa=motivo_diarias,
    )

    atualizar_despesa_pago(
        evento=evento,
        categoria="alimentacao",
        valor_pago_total=total_pago_alimentacao,
        quitado=alimentacao_quitada,
        motivo_baixa=motivo_alimentacao,
    )

    atualizar_despesa_pago(
        evento=evento,
        categoria="transporte",
        valor_pago_total=total_pago_transporte,
        quitado=transporte_quitado,
        motivo_baixa=motivo_transporte,
    )


def sincronizar_pagamento_servico_e_recalcular_evento(evento):
    sincronizar_pagamentos_servico_com_despesas(evento)
    evento.recalcular_realizado()


def motivo_baixa_custos_servico(custos, campo_quitado):
    motivos = [
        custo.motivo_baixa.strip()
        for custo in custos
        if getattr(custo, campo_quitado) and custo.motivo_baixa.strip()
    ]
    return "; ".join(motivos) or "Baixa manual informada nos custos do evento."


def atualizar_despesa_pago(
    evento,
    categoria,
    valor_pago_total,
    quitado=False,
    motivo_baixa="",
):
    descricao = MAPA_DESCRICAO.get(categoria, categoria)
    tipo_custo_servico = MAPA_TIPO_CUSTO_SERVICO[categoria]

    despesa = (
        DespesaOperacional.objects.filter(
            evento=evento,
            categoria=categoria,
            origem=DespesaOperacional.ORIGEM_CUSTO_SERVICO,
            origem_custo_servico_tipo=tipo_custo_servico,
        )
        .order_by("id")
        .first()
    )
    despesas_legadas_reservadas = list(
        DespesaOperacional.objects.filter(
            evento=evento,
            categoria=categoria,
            origem=DespesaOperacional.ORIGEM_MANUAL,
            descricao=descricao,
        )
        .order_by("id")
    )
    if despesa is None:
        despesa = despesas_legadas_reservadas[0] if despesas_legadas_reservadas else None
        if despesa is None:
            despesa = DespesaOperacional(
                evento=evento,
                categoria=categoria,
                descricao=descricao,
                valor_previsto=Decimal("0.00"),
                valor_pago=Decimal("0.00"),
                data_vencimento=evento.data_inicio,
                status="pendente",
                origem=DespesaOperacional.ORIGEM_CUSTO_SERVICO,
                origem_custo_servico_tipo=tipo_custo_servico,
            )

    despesa.descricao = descricao
    despesa.origem = DespesaOperacional.ORIGEM_CUSTO_SERVICO
    despesa.origem_custo_servico_tipo = tipo_custo_servico
    despesa.origem_custo_extra = None

    if not despesa.data_vencimento:
        despesa.data_vencimento = evento.data_inicio

    despesa.valor_pago = quantizar_moeda(valor_pago_total)
    despesa.baixado_manualmente = quitado
    despesa.motivo_baixa = motivo_baixa if quitado else ""

    if despesa.valor_previsto == Decimal("0.00") and despesa.valor_pago == Decimal("0.00"):
        despesa.status = "cancelado"
    elif quitado:
        despesa.status = "pago"
    elif despesa.valor_pago <= Decimal("0.00"):
        despesa.status = "pendente"
    elif despesa.valor_pago < despesa.valor_previsto:
        despesa.status = "parcial"
    else:
        despesa.status = "pago"

    despesa.save(sincronizacao_origem=True)

    despesas_legadas_duplicadas = [
        item
        for item in despesas_legadas_reservadas
        if item.id != despesa.id
    ]
    if despesas_legadas_duplicadas:
        DespesaOperacional.objects.filter(
            id__in=[item.id for item in despesas_legadas_duplicadas]
        ).delete()


def registrar_pagamento_custo_servico_com_lock(form, usuario):
    form.pagamento_registrado = False

    try:
        with transaction.atomic():
            custo_servico = (
                EventoCustoServico.objects.select_for_update()
                .select_related("evento", "evento__cliente", "servico")
                .get(pk=form.cleaned_data["custo_servico"].pk)
            )
            tipo = form.cleaned_data["tipo"]

            validar_custo_servico_pagavel(custo_servico, tipo)

            valor_pagamento = form.cleaned_data.get("valor_pagamento") or Decimal("0.00")
            if valor_pagamento > Decimal("0.00"):
                pagamento = PagamentoEventoCustoServico(
                    custo_servico=custo_servico,
                    tipo=tipo,
                    descricao=form.cleaned_data.get("descricao") or "",
                    valor_pagamento=valor_pagamento,
                    data_pagamento=form.cleaned_data["data_pagamento"],
                    observacao=form.cleaned_data.get("observacao") or "",
                    criado_por=usuario,
                    atualizado_por=usuario,
                )
                pagamento.save()

            if form.cleaned_data.get("baixar_saldo"):
                aplicar_baixa_custo_servico(
                    custo_servico,
                    tipo,
                    form.cleaned_data.get("motivo_baixa"),
                    usuario,
                )
    except ValidationError as erro:
        adicionar_erros_validacao(form, erro)
        return form

    form.pagamento_registrado = True
    return form


def validar_custo_servico_pagavel(custo_servico, tipo):
    config_tipo = TIPOS_CUSTO_SERVICO.get(tipo)
    if not config_tipo:
        raise ValidationError({"tipo": "Tipo de custo invalido."})

    if getattr(custo_servico, config_tipo["quitado"]):
        raise ValidationError({"tipo": "Este tipo de custo já foi quitado."})


def aplicar_baixa_custo_servico(custo_servico, tipo, motivo_baixa, usuario):
    config_tipo = TIPOS_CUSTO_SERVICO.get(tipo)
    if not config_tipo:
        return

    campo_quitado = config_tipo["quitado"]
    setattr(custo_servico, campo_quitado, True)
    custo_servico.motivo_baixa = montar_motivo_baixa_custo_servico(
        custo_servico.motivo_baixa,
        config_tipo["rotulo"],
        motivo_baixa,
    )
    custo_servico.atualizado_por = usuario
    custo_servico.full_clean()
    custo_servico.save(
        update_fields=[
            campo_quitado,
            "motivo_baixa",
            "atualizado_por",
            "atualizado_em",
        ]
    )


def montar_motivo_baixa_custo_servico(motivo_atual, rotulo_tipo, motivo_baixa):
    motivo_atual = (motivo_atual or "").strip()
    motivo_novo = f"{rotulo_tipo}: {(motivo_baixa or '').strip()}"

    if not motivo_atual:
        return motivo_novo

    if motivo_novo in motivo_atual.split("; "):
        return motivo_atual

    return f"{motivo_atual}; {motivo_novo}"
