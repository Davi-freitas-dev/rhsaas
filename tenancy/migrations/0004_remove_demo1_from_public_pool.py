from django.db import migrations


def remove_demo1_pool_slot(apps, schema_editor):
    DemoTenantSlot = apps.get_model("tenancy", "DemoTenantSlot")
    DemoTenantSlot.objects.filter(slot_code="demo1").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0003_demo_public_lease_access"),
    ]

    operations = [
        migrations.RunPython(
            remove_demo1_pool_slot,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
