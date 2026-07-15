from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0002_demotenantslot"),
    ]

    operations = [
        migrations.AddField(
            model_name="demotenantslot",
            name="visitor_key_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="demotenantslot",
            name="network_key_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="demotenantslot",
            name="exchange_token_digest",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="demotenantslot",
            name="exchange_token_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="demotenantslot",
            name="exchange_token_consumed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
