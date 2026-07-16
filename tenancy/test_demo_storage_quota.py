import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import Client, override_settings
from django_tenants.utils import get_public_schema_name, schema_context

from caixa.models import Cliente
from tenancy.models import DemoTenantSlot
from tenancy.services_demo_pool import allocate_demo_lease, seed_demo_tenant, sync_demo_public_user
from tenancy.services_demo_storage import (
    DEMO_STORAGE_QUOTA_ERROR_CODE,
    DEMO_STORAGE_QUOTA_MESSAGE,
    demo_storage_quota_applies,
    get_cached_demo_storage_quota_status,
    get_demo_storage_quota_status,
)
from tenancy.test_helpers import MultiTenantTestCase


MEBIBYTE = 1024 * 1024


class DemoStorageQuotaTests(MultiTenantTestCase):
    primary_schema_name = "demo1"
    primary_tenant_name = "Demo 1"
    primary_domain = "demo1.api-demo-rh.taquiondev.com.br"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.demo1 = cls.primary_tenant
        cls.demo2, _domain = cls.create_tenant(
            schema_name="demo2",
            name="Demo 2",
            domain="demo2.api-demo-rh.taquiondev.com.br",
        )
        cls.demo3, _domain = cls.create_tenant(
            schema_name="demo3",
            name="Demo 3",
            domain="demo3.api-demo-rh.taquiondev.com.br",
        )
        cls.rh_teste, _domain = cls.create_tenant(
            schema_name="rh_teste",
            name="RH Teste",
            domain="rh-teste.api-demo-rh.taquiondev.com.br",
        )

    def setUp(self):
        self._settings = override_settings(
            DEMO_PUBLIC_LEASE_ENABLED=True,
            DEMO_PERMANENT_TENANT_SCHEMA="demo1",
            DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3"),
            DEMO_STORAGE_QUOTA_CACHE_SECONDS=15,
            SESSION_COOKIE_SECURE=False,
        )
        self._settings.enable()
        super().setUp()

        for schema_name in ("demo1", "demo2", "demo3"):
            seed_demo_tenant(schema_name)
            sync_demo_public_user(schema_name)

        connection.set_schema_to_public()
        DemoTenantSlot.objects.all().delete()
        DemoTenantSlot.objects.create(
            tenant=self.demo2,
            slot_code="demo2",
            max_storage_mb=50,
        )
        DemoTenantSlot.objects.create(
            tenant=self.demo3,
            slot_code="demo3",
            max_storage_mb=50,
        )
        cache.clear()

        self.demo1_client = self._authenticated_demo_client("demo1")
        self.demo2_client = self._authenticated_demo_client("demo2")
        self.demo3_client = self._authenticated_demo_client("demo3")
        self.superuser_client = self._superuser_client("demo2")
        self.rh_teste_client = self._rh_teste_client()

    def tearDown(self):
        try:
            super().tearDown()
        finally:
            self._settings.disable()

    def _client(self, schema_name):
        host_by_schema = {
            "demo1": "demo1.api-demo-rh.taquiondev.com.br",
            "demo2": "demo2.api-demo-rh.taquiondev.com.br",
            "demo3": "demo3.api-demo-rh.taquiondev.com.br",
            "rh_teste": "rh-teste.api-demo-rh.taquiondev.com.br",
        }
        return Client(HTTP_HOST=host_by_schema[schema_name])

    def _authenticated_demo_client(self, schema_name):
        client = self._client(schema_name)
        with schema_context(schema_name):
            user = get_user_model().objects.get(username="demo")
            client.force_login(user)
        return client

    def _superuser_client(self, schema_name):
        client = self._client(schema_name)
        with schema_context(schema_name):
            user = get_user_model().objects.create_superuser(
                username="quota-superuser",
                password="senha-segura",
                email="quota-superuser@example.com",
            )
            client.force_login(user)
        return client

    def _rh_teste_client(self):
        client = self._client("rh_teste")
        with schema_context("rh_teste"):
            user = get_user_model().objects.create_user(
                username="quota-rh-teste",
                password="senha-segura",
            )
            user.user_permissions.add(
                *Permission.objects.filter(
                    content_type__app_label="caixa",
                    codename__in=("view_cliente", "add_cliente", "change_cliente"),
                )
            )
            client.force_login(user)
        return client

    def _client_payload(self, suffix):
        return {
            "name": f"Cliente quota {suffix}",
            "tradeName": f"Quota {suffix}",
            "personType": "PJ",
            "document": f"45.000.000/0001-{int(suffix):02d}",
            "phone": "",
            "email": "",
            "responsible": "",
            "address": "",
            "notes": "",
            "isActive": True,
        }

    def _post_client(self, client, suffix):
        return client.post(
            "/api/clientes/",
            data=json.dumps(self._client_payload(suffix)),
            content_type="application/json",
        )

    def _assert_quota_response(self, response):
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json()["code"], DEMO_STORAGE_QUOTA_ERROR_CODE)
        self.assertEqual(response.json()["detail"], DEMO_STORAGE_QUOTA_MESSAGE)
        self.assertIn("no-store", response["Cache-Control"])

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=1 * MEBIBYTE)
    def test_schema_abaixo_do_limite_continua_gravando_com_uma_medicao(self, measure):
        response = self._post_client(self.demo2_client, "01")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(measure.call_count, 1)
        with schema_context("demo2"):
            self.assertTrue(Cliente.objects.filter(nome_razao_social="Cliente quota 01").exists())

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_schema_acima_do_limite_bloqueia_criacao_e_reverte(self, _measure):
        response = self._post_client(self.demo2_client, "02")

        self._assert_quota_response(response)
        with schema_context("demo2"):
            self.assertFalse(Cliente.objects.filter(nome_razao_social="Cliente quota 02").exists())

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_schema_acima_do_limite_bloqueia_edicao_e_reverte(self, _measure):
        with schema_context("demo2"):
            client = Cliente.objects.create(
                nome_razao_social="Cliente antes da quota",
                tipo_pessoa="PJ",
                cpf_cnpj="45.000.000/0001-03",
            )

        payload = self._client_payload("03")
        payload["name"] = "Cliente editado acima da quota"
        response = self.demo2_client.put(
            f"/api/clientes/{client.pk}/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self._assert_quota_response(response)
        with schema_context("demo2"):
            client.refresh_from_db()
            self.assertEqual(client.nome_razao_social, "Cliente antes da quota")

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes")
    def test_leituras_nao_medem_quota_nem_sao_bloqueadas(self, measure):
        for _index in range(3):
            response = self.demo2_client.get("/api/clientes/")
            self.assertEqual(response.status_code, 200, response.content)
        measure.assert_not_called()

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_superusuario_nao_e_afetado(self, measure):
        response = self._post_client(self.superuser_client, "04")

        self.assertEqual(response.status_code, 201, response.content)
        measure.assert_not_called()

    def test_schema_publico_nao_e_afetado(self):
        with schema_context("demo2"):
            demo_user = get_user_model().objects.get(username="demo")
        with schema_context(get_public_schema_name()):
            self.assertFalse(demo_storage_quota_applies(demo_user))

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_rh_teste_nao_e_afetado(self, measure):
        response = self._post_client(self.rh_teste_client, "05")

        self.assertEqual(response.status_code, 201, response.content)
        measure.assert_not_called()

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_demo1_permanente_nao_e_afetado(self, measure):
        response = self._post_client(self.demo1_client, "06")

        self.assertEqual(response.status_code, 201, response.content)
        measure.assert_not_called()

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_status_expoe_somente_quota_do_tenant_atual(self, _measure):
        response = self.demo2_client.get("/api/demo/storage/")

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()["storageQuota"]
        self.assertTrue(payload["applies"])
        self.assertTrue(payload["exceeded"])
        self.assertEqual(payload["maxStorageMb"], 50)
        self.assertNotIn("schema", payload)
        self.assertNotIn("demo3", response.content.decode("utf-8"))

    def test_isolamento_bloqueia_demo2_sem_afetar_demo3(self):
        def usage_for_schema(schema_name):
            return 60 * MEBIBYTE if schema_name == "demo2" else 1 * MEBIBYTE

        with patch(
            "tenancy.services_demo_storage.measure_schema_storage_bytes",
            side_effect=usage_for_schema,
        ):
            blocked = self._post_client(self.demo2_client, "07")
            allowed = self._post_client(self.demo3_client, "08")

        self._assert_quota_response(blocked)
        self.assertEqual(allowed.status_code, 201, allowed.content)
        with schema_context("demo2"):
            self.assertFalse(Cliente.objects.filter(nome_razao_social="Cliente quota 07").exists())
        with schema_context("demo3"):
            self.assertTrue(Cliente.objects.filter(nome_razao_social="Cliente quota 08").exists())

    @patch("tenancy.services_demo_storage.measure_schema_storage_bytes", return_value=60 * MEBIBYTE)
    def test_cache_acima_do_limite_bloqueia_antes_de_nova_medicao(self, measure):
        with schema_context("demo2"):
            status = get_demo_storage_quota_status(use_cache=False)
            self.assertTrue(status.exceeded)
        measure.reset_mock()

        response = self._post_client(self.demo2_client, "09")

        self._assert_quota_response(response)
        measure.assert_not_called()

    def test_reset_limpa_quota_e_slot_aceita_novo_lease(self):
        with schema_context("demo2"), patch(
            "tenancy.services_demo_storage.measure_schema_storage_bytes",
            return_value=60 * MEBIBYTE,
        ):
            self.assertTrue(get_demo_storage_quota_status(use_cache=False).exceeded)
            self.assertIsNotNone(get_cached_demo_storage_quota_status())

        connection.set_schema_to_public()
        DemoTenantSlot.objects.filter(slot_code="demo2").update(
            status=DemoTenantSlot.Status.EXPIRADO,
        )
        with (
            patch(
                "tenancy.management.commands.resetar_tenant_demo.Command._drop_schema"
            ),
            patch(
                "tenancy.management.commands.resetar_tenant_demo.Command._recreate_schema"
            ),
            patch(
                "tenancy.management.commands.resetar_tenant_demo.Command._validate_recreated_schema"
            ),
            patch(
                "tenancy.management.commands.resetar_tenant_demo.Command._sync_minimal_seed"
            ),
            patch(
                "tenancy.management.commands.resetar_tenant_demo.Command._delete_tenant_artifacts",
                return_value=0,
            ),
        ):
            call_command(
                "resetar_tenant_demo",
                slot="demo2",
                confirm="RESETAR demo2",
                verbosity=0,
            )

        with schema_context("demo2"), patch(
            "tenancy.services_demo_storage.measure_schema_storage_bytes",
            return_value=1 * MEBIBYTE,
        ):
            self.assertIsNone(get_cached_demo_storage_quota_status())
            status = get_demo_storage_quota_status(use_cache=False)
            self.assertTrue(status.applies)
            self.assertFalse(status.exceeded)

        grant = allocate_demo_lease(
            visitor_identifier="quota-reset-visitor",
            network_identifier="198.51.100.210",
        )
        self.assertEqual(grant.slot_code, "demo2")
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.get(slot_code="demo2").status,
            DemoTenantSlot.Status.OCUPADO,
        )
