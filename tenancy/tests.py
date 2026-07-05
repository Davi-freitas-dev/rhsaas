from django.contrib.auth.models import Group
from django.db import connection
from django_tenants.utils import get_public_schema_name

from tenancy.models import Domain, Tenant
from tenancy.test_helpers import MultiTenantTestCase, OPERATIONAL_GROUPS


class TenantIsolationInfrastructureTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, cls.secondary_domain = cls.create_tenant(
            schema_name="tenant_b",
            name="Tenant B",
            domain="tenant-b.localhost",
        )
        cls.add_allowed_host("tenant-inexistente.localhost")
        cls.tenants = {
            cls.primary_tenant.schema_name: cls.primary_tenant,
            cls.secondary_tenant.schema_name: cls.secondary_tenant,
        }

    def test_cria_dois_tenants_e_dominios(self):
        self.switch_to_public()

        self.assertEqual(
            set(Tenant.objects.values_list("schema_name", flat=True)),
            {"tenant_a", "tenant_b"},
        )
        self.assertEqual(
            set(Domain.objects.values_list("domain", flat=True)),
            {"tenant-a.localhost", "tenant-b.localhost"},
        )

    def test_resolve_schema_correto_por_host(self):
        for schema_name, host in (
            ("tenant_a", "tenant-a.localhost"),
            ("tenant_b", "tenant-b.localhost"),
        ):
            with self.subTest(host=host):
                response = self.client_for_tenant(self.tenants[schema_name]).get(
                    "/manifest.webmanifest"
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.wsgi_request.tenant.schema_name, schema_name)
                self.assertEqual(connection.schema_name, schema_name)

    def test_host_inexistente_retorna_404(self):
        response = self.client.get(
            "/manifest.webmanifest",
            HTTP_HOST="tenant-inexistente.localhost",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(connection.schema_name, get_public_schema_name())

    def test_public_continua_sem_tabelas_caixa(self):
        self.switch_to_public()

        self.assertEqual(self.public_table_names(prefix="caixa_"), [])

    def test_grupos_operacionais_existem_apenas_nos_tenants(self):
        self.switch_to_public()
        public_groups = set(
            Group.objects.filter(name__in=OPERATIONAL_GROUPS).values_list(
                "name",
                flat=True,
            )
        )
        self.assertEqual(public_groups, set())

        for schema_name in self.tenants:
            with self.subTest(schema_name=schema_name):
                with self.in_schema(schema_name):
                    tenant_groups = set(
                        Group.objects.filter(
                            name__in=OPERATIONAL_GROUPS
                        ).values_list("name", flat=True)
                    )

                self.assertEqual(tenant_groups, set(OPERATIONAL_GROUPS))
