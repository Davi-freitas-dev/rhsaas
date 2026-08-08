from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations
from django.db.models import Sum


ZERO = Decimal("0.00")


def quantizar_moeda(valor):
    return Decimal(valor or ZERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def recalcular_totais_orcamentos_editaveis(apps, schema_editor):
    Orcamento = apps.get_model("caixa", "Orcamento")
    OrcamentoItem = apps.get_model("caixa", "OrcamentoItem")
    OrcamentoCustoExtra = apps.get_model("caixa", "OrcamentoCustoExtra")

    orcamentos = list(
        Orcamento.objects.filter(status__in=["rascunho", "enviado"]).order_by("id")
    )
    if not orcamentos:
        return

    orcamentos_ids = [orcamento.id for orcamento in orcamentos]
    totais_itens = {
        item["orcamento_id"]: item
        for item in (
            OrcamentoItem.objects.filter(orcamento_id__in=orcamentos_ids)
            .values("orcamento_id")
            .annotate(
                subtotal_custos=Sum("custo_total"),
                total_impostos=Sum("valor_imposto"),
                total_venda_itens=Sum("preco_venda"),
            )
        )
    }
    totais_extras = {
        item["orcamento_id"]: quantizar_moeda(item["total"])
        for item in (
            OrcamentoCustoExtra.objects.filter(orcamento_id__in=orcamentos_ids)
            .values("orcamento_id")
            .annotate(total=Sum("valor_previsto"))
        )
    }

    for orcamento in orcamentos:
        totais_item = totais_itens.get(orcamento.id, {})
        subtotal_custos = quantizar_moeda(totais_item.get("subtotal_custos"))
        total_impostos = quantizar_moeda(totais_item.get("total_impostos"))
        total_custos_extras = totais_extras.get(orcamento.id, ZERO)
        total_venda = quantizar_moeda(
            quantizar_moeda(totais_item.get("total_venda_itens"))
            + total_custos_extras
        )

        orcamento.subtotal_custos = subtotal_custos
        orcamento.total_impostos = total_impostos
        orcamento.total_lucro = quantizar_moeda(
            total_venda
            - subtotal_custos
            - total_custos_extras
            - total_impostos
        )
        orcamento.total_venda = total_venda

    Orcamento.objects.bulk_update(
        orcamentos,
        ["subtotal_custos", "total_impostos", "total_lucro", "total_venda"],
    )


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0045_participacoes_escala_diaria"),
    ]

    operations = [
        migrations.RunPython(
            recalcular_totais_orcamentos_editaveis,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
