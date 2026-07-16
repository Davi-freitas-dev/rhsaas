from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("caixa", "0041_remove_horas_cobradas_decimal_horas_dia"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="demo_seed_key",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=80,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="configuracaofinanceira",
            name="demo_seed_key",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=80,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="orcamento",
            name="demo_seed_key",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=80,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="servico",
            name="demo_seed_key",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=80,
                null=True,
                unique=True,
            ),
        ),
    ]
