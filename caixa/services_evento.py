from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from .models import DespesaOperacional, ReceitaOperacional
from .models_servico import EventoCustoServico
from .utils_financeiros import decimal_zero, quantizar_moeda


LIMITE_DECIMAL_12_2 = Decimal("9999999999.99")


def limitar_decimal(valor):
    valor = quantizar_moeda(valor)

    if valor > LIMITE_DECIMAL_12_2:
        return LIMITE_DECIMAL_12_2

    if valor < -LIMITE_DECIMAL_12_2:
        return -LIMITE_DECIMAL_12_2

    return valor


def recalcular_totais_realizados_evento(evento):
    total_recebido = decimal_zero(evento.receitas.aggregate(
        total=Sum("valor_recebido")
    )["total"])
    total_pago = decimal_zero(evento.despesas.aggregate(
        total=Sum("valor_pago")
    )["total"])

    evento.valor_total_realizado = quantizar_moeda(total_recebido)
    evento.custo_total_realizado = quantizar_moeda(total_pago)
    evento.lucro_realizado = quantizar_moeda(total_recebido - total_pago)

    evento.save(update_fields=[
        "valor_total_realizado",
        "custo_total_realizado",
        "lucro_realizado",
        "atualizado_em",
    ])


def recalcular_receita_prevista_evento(evento):
    total_previsto = decimal_zero(evento.receitas.aggregate(
        total=Sum("valor_previsto")
    )["total"])

    evento.valor_total_previsto = quantizar_moeda(total_previsto)
    evento.lucro_previsto = quantizar_moeda(
        evento.valor_total_previsto - evento.custo_total_previsto
    )

    evento.save(update_fields=[
        "valor_total_previsto",
        "lucro_previsto",
        "atualizado_em",
    ])


def recalcular_custo_previsto_evento(evento):
    total_previsto = decimal_zero(evento.despesas.aggregate(
        total=Sum("valor_previsto")
    )["total"])

    evento.custo_total_previsto = quantizar_moeda(total_previsto)
    evento.lucro_previsto = quantizar_moeda(
        evento.valor_total_previsto - evento.custo_total_previsto
    )

    evento.save(update_fields=[
        "custo_total_previsto",
        "lucro_previsto",
        "atualizado_em",
    ])


def gerar_movimentacoes_previstas_evento(evento):
    if evento.receitas.exists() or evento.despesas.exists():
        return

    ReceitaOperacional.objects.create(
        evento=evento,
        cliente=evento.cliente,
        descricao=f"Receita prevista do evento {evento.nome_evento}",
        valor_previsto=evento.valor_total_previsto,
        valor_recebido=Decimal("0.00"),
        data_vencimento=evento.data_inicio,
        status="pendente",
    )

    if not evento.orcamento:
        return

    itens = evento.orcamento.itens.all()

    total_mao_obra = sum(
        (item.custo_servico_total for item in itens),
        Decimal("0.00")
    )
    total_alimentacao = sum(
        (item.gasto_alimentacao_total for item in itens),
        Decimal("0.00")
    )
    total_transporte = sum(
        (item.gasto_transporte_total for item in itens),
        Decimal("0.00")
    )
    total_imposto = sum(
        (item.valor_imposto for item in itens),
        Decimal("0.00")
    )

    despesas = [
        ("mao_obra", "Mão de obra prevista", total_mao_obra, "diarias"),
        ("alimentacao", "Alimentação prevista", total_alimentacao, "alimentacao"),
        ("transporte", "Transporte previsto", total_transporte, "transporte"),
        ("imposto", "Imposto previsto", total_imposto, ""),
    ]

    for categoria, descricao, valor, tipo_custo_servico in despesas:
        if valor > Decimal("0.00"):
            despesa = DespesaOperacional(
                evento=evento,
                descricao=descricao,
                categoria=categoria,
                valor_previsto=valor,
                valor_pago=Decimal("0.00"),
                data_vencimento=evento.data_inicio,
                status="pendente",
                origem=(
                    DespesaOperacional.ORIGEM_CUSTO_SERVICO
                    if tipo_custo_servico
                    else DespesaOperacional.ORIGEM_MANUAL
                ),
                origem_custo_servico_tipo=tipo_custo_servico,
            )
            despesa.save(sincronizacao_origem=bool(tipo_custo_servico))


def sincronizar_despesas_operacionais_evento(evento, recalcular=True):
    custos = list(
        EventoCustoServico.objects.filter(evento=evento).prefetch_related("pagamentos")
    )

    total_diarias = limitar_decimal(sum(
        (custo.valor_diarias for custo in custos),
        Decimal("0.00"),
    ))
    total_alimentacao = limitar_decimal(sum(
        (custo.valor_alimentacao for custo in custos),
        Decimal("0.00"),
    ))
    total_transporte = limitar_decimal(sum(
        (custo.valor_transporte for custo in custos),
        Decimal("0.00"),
    ))
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

    with transaction.atomic():
        atualizar_ou_criar_despesa_evento(
            evento=evento,
            descricao="Mão de obra prevista",
            categoria="mao_obra",
            valor=total_diarias,
            quitado=diarias_quitadas,
            motivo_baixa=motivo_diarias,
        )

        atualizar_ou_criar_despesa_evento(
            evento=evento,
            descricao="Alimentação prevista",
            categoria="alimentacao",
            valor=total_alimentacao,
            quitado=alimentacao_quitada,
            motivo_baixa=motivo_alimentacao,
        )

        atualizar_ou_criar_despesa_evento(
            evento=evento,
            descricao="Transporte previsto",
            categoria="transporte",
            valor=total_transporte,
            quitado=transporte_quitado,
            motivo_baixa=motivo_transporte,
        )

    if recalcular:
        evento.recalcular_custo_previsto()
        evento.recalcular_realizado()


def motivo_baixa_custos_servico(custos, campo_quitado):
    motivos = [
        custo.motivo_baixa.strip()
        for custo in custos
        if getattr(custo, campo_quitado) and custo.motivo_baixa.strip()
    ]
    return "; ".join(motivos) or "Baixa manual informada nos custos do evento."


def atualizar_ou_criar_despesa_evento(
    evento,
    descricao,
    categoria,
    valor,
    quitado=False,
    motivo_baixa="",
):
    tipo_custo_servico = DespesaOperacional.CUSTOS_SERVICO_DERIVADOS[categoria][2]
    despesas = list(
        DespesaOperacional.objects.filter(
            evento=evento,
            categoria=categoria,
            origem=DespesaOperacional.ORIGEM_CUSTO_SERVICO,
            origem_custo_servico_tipo=tipo_custo_servico,
        ).order_by("id")
    )
    despesas_legadas_reservadas = list(
        DespesaOperacional.objects.filter(
            evento=evento,
            categoria=categoria,
            origem=DespesaOperacional.ORIGEM_MANUAL,
            descricao=descricao,
        ).order_by("id")
    )

    if despesas:
        despesa_principal = despesas[0]
        despesas_duplicadas = despesas[1:] + despesas_legadas_reservadas
    elif despesas_legadas_reservadas:
        despesa_principal = despesas_legadas_reservadas[0]
        despesas_duplicadas = despesas_legadas_reservadas[1:]
    else:
        despesa_principal = None
        despesas_duplicadas = []

    valor_pago_total = sum(
        (
            decimal_zero(despesa.valor_pago)
            for despesa in [despesa_principal, *despesas_duplicadas]
            if despesa is not None
        ),
        Decimal("0.00")
    )

    valor = limitar_decimal(valor)
    valor_pago_total = limitar_decimal(valor_pago_total)

    if despesa_principal is None:
        despesa_principal = DespesaOperacional(
            evento=evento,
            descricao=descricao,
            categoria=categoria,
            data_vencimento=evento.data_inicio,
        )

    despesa_principal.descricao = descricao
    despesa_principal.data_vencimento = evento.data_inicio
    despesa_principal.valor_previsto = valor
    despesa_principal.baixado_manualmente = quitado
    despesa_principal.motivo_baixa = motivo_baixa if quitado else ""
    despesa_principal.origem = DespesaOperacional.ORIGEM_CUSTO_SERVICO
    despesa_principal.origem_custo_servico_tipo = tipo_custo_servico
    despesa_principal.origem_custo_extra = None

    if valor == Decimal("0.00") and valor_pago_total == Decimal("0.00"):
        despesa_principal.valor_pago = Decimal("0.00")
        despesa_principal.status = "cancelado"
    else:
        # Permite refletir custo real acima do previsto
        valor_pago_ajustado = valor_pago_total
        despesa_principal.valor_pago = limitar_decimal(valor_pago_ajustado)

        if quitado:
            despesa_principal.status = "pago"
        elif valor_pago_ajustado <= Decimal("0.00"):
            despesa_principal.status = "pendente"
        elif valor_pago_ajustado < valor:
            despesa_principal.status = "parcial"
        else:
            despesa_principal.status = "pago"

    despesa_principal.save(sincronizacao_origem=True)

    if despesas_duplicadas:
        DespesaOperacional.objects.filter(
            id__in=[despesa.id for despesa in despesas_duplicadas]
        ).delete()
