from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0038_orcamentoitem_snapshots_diaria"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="orcamento",
            options={
                "ordering": ["-criado_em"],
                "permissions": [
                    ("approve_orcamento", "Pode aprovar orçamento"),
                ],
                "verbose_name": "Orçamento",
                "verbose_name_plural": "Orçamentos",
            },
        ),
    ]
