from decimal import Decimal

from django.db import migrations, models
from django.db.models import OuterRef, Q, Subquery


def preencher_snapshots_diaria(apps, schema_editor):
    Servico = apps.get_model("caixa", "Servico")
    OrcamentoItem = apps.get_model("caixa", "OrcamentoItem")

    servico = Servico.objects.filter(pk=OuterRef("servico_id"))

    # Backfill historico limitado ao valor atual disponivel no cadastro do servico.
    # Se o servico ja foi alterado antes desta migration, o parametro original
    # usado na criacao do item pode nao ser recuperavel.
    OrcamentoItem.objects.update(
        horas_base_diaria_usada=Subquery(servico.values("horas_base_diaria")[:1]),
        percentual_hora_extra_usado=Subquery(
            servico.values("percentual_hora_extra")[:1]
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0037_servico_unidade_cobranca_hora"),
    ]

    operations = [
        migrations.AddField(
            model_name="orcamentoitem",
            name="horas_base_diaria_usada",
            field=models.PositiveIntegerField(default=8),
        ),
        migrations.AddField(
            model_name="orcamentoitem",
            name="percentual_hora_extra_usado",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1.50"),
                max_digits=5,
            ),
        ),
        migrations.RunPython(preencher_snapshots_diaria, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="orcamentoitem",
            constraint=models.CheckConstraint(
                condition=Q(horas_base_diaria_usada__gt=0),
                name="ck_orc_item_horas_base_usada_pos",
            ),
        ),
        migrations.AddConstraint(
            model_name="orcamentoitem",
            constraint=models.CheckConstraint(
                condition=Q(percentual_hora_extra_usado__gte=0),
                name="ck_orc_item_extra_usado_nn",
            ),
        ),
    ]
