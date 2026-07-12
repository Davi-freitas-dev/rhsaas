from decimal import Decimal

from django.db import migrations, models
from django.db.models import F, Q


def preencher_unidades_cobranca(apps, schema_editor):
    Servico = apps.get_model("caixa", "Servico")
    OrcamentoItem = apps.get_model("caixa", "OrcamentoItem")

    Servico.objects.update(
        unidade_cobranca="diaria",
        valor_unitario=F("diaria_padrao"),
    )
    OrcamentoItem.objects.update(
        unidade_cobranca_usada="diaria",
        valor_unitario_usado=F("valor_diaria_usada"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0036_servico_unicidade_case_insensitive"),
    ]

    operations = [
        migrations.AddField(
            model_name="servico",
            name="unidade_cobranca",
            field=models.CharField(
                choices=[("diaria", "Diaria"), ("hora", "Hora")],
                default="diaria",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="servico",
            name="valor_unitario",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="orcamentoitem",
            name="unidade_cobranca_usada",
            field=models.CharField(
                choices=[("diaria", "Diaria"), ("hora", "Hora")],
                default="diaria",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="orcamentoitem",
            name="valor_unitario_usado",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="orcamentoitem",
            name="quantidade_horas_cobradas",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=8,
            ),
        ),
        migrations.RunPython(
            preencher_unidades_cobranca,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="orcamentoitem",
            name="ck_orc_item_valores_nn",
        ),
        migrations.AddConstraint(
            model_name="orcamentoitem",
            constraint=models.CheckConstraint(
                condition=(
                    Q(valor_diaria_usada__gte=0)
                    & Q(valor_unitario_usado__gte=0)
                    & Q(quantidade_horas_cobradas__gte=0)
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
        migrations.AddConstraint(
            model_name="servico",
            constraint=models.CheckConstraint(
                condition=Q(unidade_cobranca__in=["diaria", "hora"]),
                name="ck_servico_unidade_cobranca",
            ),
        ),
        migrations.AddConstraint(
            model_name="servico",
            constraint=models.CheckConstraint(
                condition=Q(valor_unitario__gte=0),
                name="ck_servico_valor_unit_nn",
            ),
        ),
        migrations.AddConstraint(
            model_name="orcamentoitem",
            constraint=models.CheckConstraint(
                condition=Q(unidade_cobranca_usada__in=["diaria", "hora"]),
                name="ck_orc_item_unidade_cobranca",
            ),
        ),
        migrations.AddConstraint(
            model_name="orcamentoitem",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(unidade_cobranca_usada="hora")
                    | Q(quantidade_horas_cobradas__gt=0)
                ),
                name="ck_orc_item_hora_qtd_pos",
            ),
        ),
    ]
