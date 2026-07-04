# Generated manually for PM-40.1 on 2026-06-18

from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Lower


def _formatar_duplicados(Servico, campo, valor_normalizado):
    itens = (
        Servico.objects.annotate(valor_ci=Lower(campo))
        .filter(valor_ci=valor_normalizado)
        .values_list("id", campo)
        .order_by("id")
    )
    return ", ".join(f"id={item_id} {campo}={valor!r}" for item_id, valor in itens)


def validar_sem_duplicados_case_insensitive(apps, schema_editor):
    Servico = apps.get_model("caixa", "Servico")
    mensagens = []

    for campo in ("nome", "codigo"):
        duplicados = (
            Servico.objects.annotate(valor_ci=Lower(campo))
            .values("valor_ci")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .order_by("valor_ci")
        )
        for duplicado in duplicados:
            valor_normalizado = duplicado["valor_ci"]
            mensagens.append(
                f"{campo}={valor_normalizado!r}: "
                f"{_formatar_duplicados(Servico, campo, valor_normalizado)}"
            )

    if mensagens:
        detalhe = "; ".join(mensagens)
        raise RuntimeError(
            "Nao e possivel aplicar a migration de unicidade case-insensitive "
            f"de Servico antes de resolver duplicados existentes: {detalhe}"
        )


def normalizar_codigos_existentes(apps, schema_editor):
    Servico = apps.get_model("caixa", "Servico")

    for servico in Servico.objects.only("id", "codigo").iterator():
        codigo_normalizado = (servico.codigo or "").strip().lower()
        if servico.codigo != codigo_normalizado:
            Servico.objects.filter(pk=servico.pk).update(codigo=codigo_normalizado)


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0035_remove_contrato_operacional"),
    ]

    operations = [
        migrations.RunPython(
            validar_sem_duplicados_case_insensitive,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            normalizar_codigos_existentes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="servico",
            constraint=models.UniqueConstraint(
                Lower("nome"),
                name="uq_servico_nome_ci",
            ),
        ),
        migrations.AddConstraint(
            model_name="servico",
            constraint=models.UniqueConstraint(
                Lower("codigo"),
                name="uq_servico_codigo_ci",
            ),
        ),
    ]
