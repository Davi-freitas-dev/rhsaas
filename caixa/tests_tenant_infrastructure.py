from django.db import connection
from django_tenants.utils import get_public_schema_name

from tenancy.test_helpers import MultiTenantTestCase, TenantAppTestCase

from .models import Cliente


class TenantAppTestCaseContractTests(TenantAppTestCase):
    def test_01_base_ativa_schema_dominio_e_cria_usuario_no_tenant(self):
        usuario = self.create_tenant_user("base-tenant-user")

        self.assertEqual(connection.schema_name, self.tenant.schema_name)
        self.assertEqual(self.tenant.schema_name, self.test_schema_name)
        self.assertEqual(self.domain.domain, self.test_tenant_domain)
        self.assertEqual(usuario._state.db, "default")
        self.assertTrue(usuario.is_active)

    def test_02_dados_do_teste_anterior_nao_persistem(self):
        self.assertFalse(
            self.tenant_user_model().objects.filter(
                username="base-tenant-user"
            ).exists()
        )

    @staticmethod
    def tenant_user_model():
        from django.contrib.auth import get_user_model

        return get_user_model()


class TenantSchemaIsolationTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, _ = cls.create_tenant(
            "tenant_infra_b",
            "Tenant Infra B",
            "tenant-infra-b.localhost",
        )

    def test_dados_operacionais_sao_isolados_entre_tenants(self):
        with self.in_schema(self.primary_tenant.schema_name):
            cliente_a = Cliente.objects.create(
                nome_razao_social="Cliente tenant A",
                cpf_cnpj="10.000.000/0001-10",
            )

        with self.in_schema(self.secondary_tenant.schema_name):
            cliente_b = Cliente.objects.create(
                nome_razao_social="Cliente tenant B",
                cpf_cnpj="10.000.000/0001-10",
            )
            self.assertEqual(
                list(Cliente.objects.values_list("nome_razao_social", flat=True)),
                ["Cliente tenant B"],
            )

        with self.in_schema(self.primary_tenant.schema_name):
            self.assertEqual(
                list(Cliente.objects.values_list("nome_razao_social", flat=True)),
                ["Cliente tenant A"],
            )
            self.assertEqual(cliente_a.pk, cliente_b.pk)

    def test_schema_public_nao_possui_tabelas_operacionais_caixa(self):
        public_tables = self.table_names(get_public_schema_name(), prefix="caixa_%")

        self.assertEqual(public_tables, [])
