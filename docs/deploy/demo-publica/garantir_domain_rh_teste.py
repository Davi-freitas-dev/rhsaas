from tenancy.models import Domain, Tenant


SCHEMA_NAME = "rh_teste"
DOMAIN_NAME = "api-demo-rh.taquiondev.com.br"


tenant = Tenant.objects.get(schema_name=SCHEMA_NAME)

conflict = (
    Domain.objects.select_related("tenant")
    .filter(domain=DOMAIN_NAME)
    .exclude(tenant=tenant)
    .first()
)
if conflict:
    raise SystemExit(
        f"ERRO: {DOMAIN_NAME} ja pertence ao tenant "
        f"{conflict.tenant.schema_name}"
    )

Domain.objects.update_or_create(
    domain=DOMAIN_NAME,
    defaults={
        "tenant": tenant,
        "is_primary": True,
    },
)

Domain.objects.filter(tenant=tenant).exclude(domain=DOMAIN_NAME).update(
    is_primary=False
)

print(f"OK: {DOMAIN_NAME} -> {tenant.schema_name}")
