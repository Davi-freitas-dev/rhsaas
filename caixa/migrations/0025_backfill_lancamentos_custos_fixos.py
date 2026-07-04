from decimal import Decimal

from django.db import migrations


ZERO = Decimal("0.00")


def backfill_lancamentos_custos_fixos(apps, schema_editor):
    CustoFixo = apps.get_model("caixa", "CustoFixo")
    LancamentoFinanceiro = apps.get_model("caixa", "LancamentoFinanceiro")
    lote = []

    for custo_fixo in CustoFixo.objects.filter(valor_pago__gt=ZERO).exclude(
        status="cancelado"
    ).iterator():
        lote.append(
            LancamentoFinanceiro(
                tipo="saida",
                fluxo="fco",
                natureza="despesa_operacional",
                valor=custo_fixo.valor_pago,
                data_lancamento=custo_fixo.data_pagamento
                or custo_fixo.data_vencimento,
                forma="",
                descricao=custo_fixo.descricao,
                observacao=custo_fixo.observacao,
                status="realizado",
                custo_fixo_id=custo_fixo.id,
            )
        )

        if len(lote) >= 500:
            LancamentoFinanceiro.objects.bulk_create(lote)
            lote = []

    if lote:
        LancamentoFinanceiro.objects.bulk_create(lote)


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0024_remove_lancamentofinanceiro_ck_lanc_fin_origem_unica_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_lancamentos_custos_fixos,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
