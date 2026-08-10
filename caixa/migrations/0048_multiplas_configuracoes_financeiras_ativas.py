from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0047_jornada_mensal_servidores"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="configuracaofinanceira",
            name="uq_config_fin_ativa",
        ),
    ]
