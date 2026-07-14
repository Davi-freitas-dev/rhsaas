from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0040_alter_evento_numero_alter_historicalevento_numero"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="orcamentoitem",
            name="ck_orc_item_hora_qtd_pos",
        ),
        migrations.RemoveConstraint(
            model_name="orcamentoitem",
            name="ck_orc_item_valores_nn",
        ),
        migrations.RemoveField(
            model_name="orcamentoitem",
            name="quantidade_horas_cobradas",
        ),
        migrations.AlterField(
            model_name="orcamentoitem",
            name="horas_por_dia",
            field=models.DecimalField(decimal_places=2, max_digits=4),
        ),
        migrations.AddConstraint(
            model_name="orcamentoitem",
            constraint=models.CheckConstraint(
                condition=(
                    Q(valor_diaria_usada__gte=0)
                    & Q(valor_unitario_usado__gte=0)
                    & Q(valor_alimentacao_usado__gte=0)
                    & Q(valor_transporte_usado__gte=0)
                    & Q(margem_lucro_usada__gte=0)
                    & Q(aliquota_imposto_usada__gte=0)
                    & Q(valor_dia_por_pessoa__gte=0)
                    & Q(custo_servico_total__gte=0)
                    & Q(gasto_alimentacao_total__gte=0)
                    & Q(gasto_transporte_total__gte=0)
                    & Q(valor_horas_extras_total__gte=0)
                    & Q(custo_total__gte=0)
                    & Q(valor_com_margem__gte=0)
                    & Q(valor_imposto__gte=0)
                    & Q(lucro__gte=0)
                    & Q(preco_venda__gte=0)
                ),
                name="ck_orc_item_valores_nn",
            ),
        ),
    ]
