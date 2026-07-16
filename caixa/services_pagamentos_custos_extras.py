from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .demo_policy import assert_demo_write_allowed

from .models import DespesaOperacional
from .models_custos_extras import EventoCustoExtra
from .models_pagamentos import PagamentoEventoCustoExtra
from .services_custos_extras import sincronizar_despesas_custos_extras_evento
from .utils_forms import adicionar_erros_validacao
from .utils_financeiros import decimal_zero, quantizar_moeda


def atualizar_total_pago_custo_extra(custo_extra):
    total = decimal_zero(custo_extra.pagamentos.aggregate(
        total=Sum("valor_pagamento")
    )["total"])

    custo_extra.valor_pago = quantizar_moeda(total)
    custo_extra.save(
        update_fields=["valor_pago", "atualizado_em"],
        sincronizacao_pagamento=True,
    )


def sincronizar_pagamentos_custos_extras_com_despesas(evento):
    DespesaOperacional.objects.filter(
        evento=evento,
        categoria="outros",
        descricao="Custos extras previstos",
    ).delete()

    sincronizar_despesas_custos_extras_evento(evento)


def registrar_pagamento_custo_extra_com_lock(form, usuario):
    form.pagamento_registrado = False

    try:
        with transaction.atomic():
            custo_extra = (
                EventoCustoExtra.objects.select_for_update()
                .select_related("evento", "evento__cliente")
                .get(pk=form.cleaned_data["custo_extra"].pk)
            )

            assert_demo_write_allowed(
                usuario,
                custo_extra,
                operation="pay_event_extra_cost",
            )

            validar_custo_extra_pagavel(custo_extra)

            valor_pagamento = form.cleaned_data.get("valor_pagamento") or Decimal("0.00")
            if valor_pagamento > Decimal("0.00"):
                pagamento = PagamentoEventoCustoExtra(
                    custo_extra=custo_extra,
                    descricao=form.cleaned_data.get("descricao") or "",
                    valor_pagamento=valor_pagamento,
                    data_pagamento=form.cleaned_data["data_pagamento"],
                    observacao=form.cleaned_data.get("observacao") or "",
                    criado_por=usuario,
                    atualizado_por=usuario,
                )
                pagamento.save()

            if form.cleaned_data.get("baixar_saldo"):
                aplicar_baixa_custo_extra(
                    custo_extra,
                    form.cleaned_data.get("motivo_baixa"),
                    usuario,
                )
    except ValidationError as erro:
        adicionar_erros_validacao(form, erro)
        return form

    form.pagamento_registrado = True
    return form


def validar_custo_extra_pagavel(custo_extra):
    if custo_extra.quitado or custo_extra.saldo_a_pagar <= Decimal("0.00"):
        raise ValidationError({"custo_extra": "Este custo extra já foi quitado."})


def aplicar_baixa_custo_extra(custo_extra, motivo_baixa, usuario):
    custo_extra.quitado = True
    custo_extra.motivo_baixa = montar_motivo_baixa_simples(
        custo_extra.motivo_baixa,
        motivo_baixa,
    )
    custo_extra.atualizado_por = usuario
    custo_extra.save(
        update_fields=[
            "quitado",
            "motivo_baixa",
            "atualizado_por",
            "atualizado_em",
        ],
        sincronizacao_pagamento=True,
    )


def montar_motivo_baixa_simples(motivo_atual, motivo_baixa):
    motivo_atual = (motivo_atual or "").strip()
    motivo_novo = (motivo_baixa or "").strip()

    if not motivo_atual:
        return motivo_novo

    if motivo_novo in motivo_atual.split("; "):
        return motivo_atual

    return f"{motivo_atual}; {motivo_novo}"
