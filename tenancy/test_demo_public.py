import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone
from django_tenants.utils import schema_context

from caixa.models import Cliente, Evento, Orcamento, Servico
from caixa.throttling import (
    DemoLeaseRateThrottle,
    DemoLeaseResumeRateThrottle,
    DemoStatusRateThrottle,
)
from tenancy.command_guards import DEMO_POOL_SCHEMA_NAMES
from tenancy.models import DemoTenantSlot, Domain, Tenant
from tenancy.services_demo_pool import (
    DemoLeaseResumeUnavailable,
    DemoNetworkLimitExceeded,
    allocate_demo_lease,
    expire_due_demo_leases,
    hash_demo_identifier,
)
from tenancy.test_helpers import MultiTenantTestCase


class DemoPublicFlowTests(MultiTenantTestCase):
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
        cls.demo4, _domain = cls.create_tenant(
            schema_name="demo4",
            name="Demo 4",
            domain="demo4.api-demo-rh.taquiondev.com.br",
        )

    def setUp(self):
        self._demo_settings = override_settings(
            DEMO_PUBLIC_LEASE_ENABLED=True,
            DEMO_PUBLIC_ENTRY_SCHEMA="demo1",
            DEMO_PERMANENT_TENANT_SCHEMA="demo1",
            DEMO_PUBLIC_POOL_SLOTS=("demo2",),
            DEMO_LEASE_DURATION_MINUTES=60,
            DEMO_EXCHANGE_TOKEN_TTL_SECONDS=300,
            DEMO_VISITOR_COOKIE_MAX_AGE=3600,
            DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2,
            SESSION_COOKIE_SECURE=False,
        )
        self._demo_settings.enable()
        super().setUp()
        connection.set_schema_to_public()
        DemoTenantSlot.objects.all().delete()
        DemoTenantSlot.objects.create(tenant=self.demo1, slot_code="demo1")
        DemoTenantSlot.objects.create(tenant=self.demo2, slot_code="demo2")
        cache.clear()

    def tearDown(self):
        try:
            super().tearDown()
        finally:
            self._demo_settings.disable()

    def _public_client(self, *, remote_addr="198.51.100.10"):
        return Client(
            enforce_csrf_checks=True,
            HTTP_HOST="demo1.api-demo-rh.taquiondev.com.br",
            REMOTE_ADDR=remote_addr,
        )

    def _tenant_client(self, slot_code="demo2"):
        return Client(
            enforce_csrf_checks=True,
            HTTP_HOST=f"{slot_code}.api-demo-rh.taquiondev.com.br",
            REMOTE_ADDR="198.51.100.10",
        )

    def _lease(self, client=None):
        client = client or self._public_client()
        response = client.post(
            "/api/demo/lease/",
            data=json.dumps({}),
            content_type="application/json",
        )
        return client, response

    def _status(self, client=None):
        client = client or self._public_client()
        return client, client.get("/api/demo/status/")

    def _exchange(self, client, token):
        csrf_response = client.get("/api/auth/csrf/")
        self.assertEqual(csrf_response.status_code, 200)
        return client.post(
            "/api/demo/exchange/",
            data=json.dumps({"exchangeToken": token}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_response.json()["csrfToken"],
        )

    def _add_network_limit_slots(self):
        connection.set_schema_to_public()
        DemoTenantSlot.objects.create(tenant=self.demo3, slot_code="demo3")
        DemoTenantSlot.objects.create(tenant=self.demo4, slot_code="demo4")

    def test_fluxo_publico_aloca_e_autentica_sem_senha(self):
        public_client, lease_response = self._lease()

        self.assertEqual(lease_response.status_code, 201)
        payload = lease_response.json()
        self.assertEqual(
            payload["apiBaseUrl"],
            "https://demo2.api-demo-rh.taquiondev.com.br/api",
        )
        self.assertIn("exchangeToken", payload)
        self.assertNotIn("password", payload)
        self.assertIn("rhsaas_demo_visitor", public_client.cookies)
        self.assertTrue(public_client.cookies["rhsaas_demo_visitor"]["httponly"])

        tenant_client = self._tenant_client()
        exchange_response = self._exchange(tenant_client, payload["exchangeToken"])

        self.assertEqual(exchange_response.status_code, 200)
        exchange_payload = exchange_response.json()
        self.assertTrue(exchange_payload["authenticated"])
        self.assertFalse(exchange_payload["user"]["isStaff"])
        self.assertFalse(exchange_payload["user"]["isSuperuser"])
        self.assertTrue(exchange_payload["user"]["canViewDashboard"])
        self.assertFalse(exchange_payload["user"]["canManageBackups"])

        session_response = tenant_client.get("/api/auth/session/")
        self.assertEqual(session_response.status_code, 200)
        self.assertTrue(session_response.json()["authenticated"])

        connection.set_schema_to_public()
        slot = DemoTenantSlot.objects.get(slot_code="demo2")
        self.assertEqual(slot.status, DemoTenantSlot.Status.OCUPADO)
        self.assertIsNone(slot.exchange_token_digest)
        self.assertIsNotNone(slot.exchange_token_consumed_at)
        self.assertNotIn(payload["exchangeToken"], str(slot.__dict__))

        self.assertEqual(
            DemoTenantSlot.objects.get(slot_code="demo1").status,
            DemoTenantSlot.Status.LIVRE,
        )

        with schema_context("demo2"):
            user = get_user_model().objects.get(username="demo")
            self.assertFalse(user.has_usable_password())
            self.assertEqual(
                set(user.groups.values_list("name", flat=True)),
                {"Demo Publica"},
            )
            self.assertFalse(user.user_permissions.exists())
            self.assertFalse(user.has_perm("caixa.delete_cliente"))

    def test_token_e_de_uso_unico_e_vinculado_ao_tenant(self):
        _client, lease_response = self._lease()
        token = lease_response.json()["exchangeToken"]

        wrong_tenant_response = self._exchange(self._tenant_client("demo1"), token)
        self.assertEqual(wrong_tenant_response.status_code, 401)

        valid_response = self._exchange(self._tenant_client("demo2"), token)
        self.assertEqual(valid_response.status_code, 200)

        replay_response = self._exchange(self._tenant_client("demo2"), token)
        self.assertEqual(replay_response.status_code, 401)

    def test_requisicao_repetida_reutiliza_slot_e_emite_nova_troca(self):
        client, first_response = self._lease()
        first_payload = first_response.json()
        _client, second_response = self._lease(client)
        second_payload = second_response.json()

        self.assertEqual(second_response.status_code, 201)
        self.assertTrue(second_payload["reused"])
        self.assertEqual(second_payload["apiBaseUrl"], first_payload["apiBaseUrl"])
        self.assertNotEqual(second_payload["exchangeToken"], first_payload["exchangeToken"])
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).count(),
            1,
        )

    def test_logout_e_nova_entrada_reutilizam_o_mesmo_lease(self):
        with (
            patch.object(DemoLeaseRateThrottle, "rate", "1/hour", create=True),
            patch.object(
                DemoLeaseResumeRateThrottle,
                "rate",
                "10/hour",
                create=True,
            ),
        ):
            public_client, first_response = self._lease()
            first_payload = first_response.json()
            tenant_client = self._tenant_client()
            self.assertEqual(
                self._exchange(
                    tenant_client,
                    first_payload["exchangeToken"],
                ).status_code,
                200,
            )
            csrf_response = tenant_client.get("/api/auth/csrf/")

            logout_response = tenant_client.post(
                "/api/auth/logout/",
                HTTP_X_CSRFTOKEN=csrf_response.json()["csrfToken"],
            )
            _client, second_response = self._lease(public_client)

        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(logout_response.json()["authenticated"])
        self.assertEqual(second_response.status_code, 201)
        self.assertTrue(second_response.json()["reused"])
        self.assertEqual(
            second_response.json()["apiBaseUrl"],
            first_payload["apiBaseUrl"],
        )
        self.assertEqual(
            second_response.json()["expiresAt"],
            first_payload["expiresAt"],
        )
        self.assertEqual(
            self._exchange(
                tenant_client,
                second_response.json()["exchangeToken"],
            ).status_code,
            200,
        )
        resumed_session = tenant_client.get("/api/auth/session/")
        self.assertTrue(resumed_session.json()["authenticated"])
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).count(),
            1,
        )

    def test_retomada_continua_protegida_por_throttle_proprio(self):
        with (
            patch.object(DemoLeaseRateThrottle, "rate", "1/hour", create=True),
            patch.object(
                DemoLeaseResumeRateThrottle,
                "rate",
                "1/hour",
                create=True,
            ),
        ):
            client, first_response = self._lease()
            _client, second_response = self._lease(client)
            _client, third_response = self._lease(client)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertTrue(second_response.json()["reused"])
        self.assertEqual(third_response.status_code, 429)
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).count(),
            1,
        )

    def test_retomada_explicita_nao_aloca_se_nao_houver_lease_ativo(self):
        client = self._public_client()
        response = client.post(
            "/api/demo/lease/",
            data=json.dumps({"resume": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "resume_unavailable")
        connection.set_schema_to_public()
        self.assertFalse(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).exists()
        )

    def test_retomada_explicita_preserva_slot_e_prazo(self):
        client, first_response = self._lease()
        first_payload = first_response.json()
        response = client.post(
            "/api/demo/lease/",
            data=json.dumps({"resume": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["reused"])
        self.assertEqual(response.json()["apiBaseUrl"], first_payload["apiBaseUrl"])
        self.assertEqual(response.json()["expiresAt"], first_payload["expiresAt"])
        self.assertNotEqual(
            response.json()["exchangeToken"],
            first_payload["exchangeToken"],
        )

    @override_settings(DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3"))
    def test_resume_only_nao_aloca_novo_slot_se_o_lease_expirar(self):
        connection.set_schema_to_public()
        DemoTenantSlot.objects.create(tenant=self.demo3, slot_code="demo3")
        first_grant = allocate_demo_lease(
            visitor_identifier="visitante-retomada-expirada",
            network_identifier="203.0.113.54",
        )
        DemoTenantSlot.objects.filter(slot_code=first_grant.slot_code).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )

        with self.assertRaises(DemoLeaseResumeUnavailable):
            allocate_demo_lease(
                visitor_identifier="visitante-retomada-expirada",
                network_identifier="203.0.113.54",
                resume_only=True,
            )

        self.assertEqual(
            DemoTenantSlot.objects.get(slot_code="demo3").status,
            DemoTenantSlot.Status.LIVRE,
        )

    @override_settings(
        DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3", "demo4"),
        DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2,
    )
    def test_dois_visitantes_da_mesma_rede_recebem_slots_isolados(self):
        self._add_network_limit_slots()
        first_client = self._public_client(remote_addr="203.0.113.50")
        second_client = self._public_client(remote_addr="203.0.113.50")

        _client, first_response = self._lease(first_client)
        _client, second_response = self._lease(second_client)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(
            {
                first_response.json()["apiBaseUrl"],
                second_response.json()["apiBaseUrl"],
            },
            {
                "https://demo2.api-demo-rh.taquiondev.com.br/api",
                "https://demo3.api-demo-rh.taquiondev.com.br/api",
            },
        )
        self.assertFalse(first_response.json()["reused"])
        self.assertFalse(second_response.json()["reused"])

    @override_settings(
        DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3", "demo4"),
        DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2,
    )
    def test_tres_clientes_sem_cookie_na_mesma_rede_respeitam_network_limit(self):
        self._add_network_limit_slots()
        responses = [
            self._lease(self._public_client(remote_addr="203.0.113.51"))[1]
            for _index in range(3)
        ]

        self.assertEqual([response.status_code for response in responses], [201, 201, 429])
        self.assertEqual(responses[2].json()["code"], "network_limit")
        self.assertNotIn("exchangeToken", responses[2].json())
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).count(),
            2,
        )
        self.assertEqual(
            DemoTenantSlot.objects.get(slot_code="demo4").status,
            DemoTenantSlot.Status.LIVRE,
        )

    @override_settings(
        DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3", "demo4"),
        DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2,
    )
    def test_lease_expirado_e_demo1_nao_contam_no_limite_de_rede(self):
        self._add_network_limit_slots()
        network_identifier = "203.0.113.52"
        first_grant = allocate_demo_lease(
            visitor_identifier="visitante-rede-1",
            network_identifier=network_identifier,
        )
        allocate_demo_lease(
            visitor_identifier="visitante-rede-2",
            network_identifier=network_identifier,
        )
        connection.set_schema_to_public()
        DemoTenantSlot.objects.filter(slot_code=first_grant.slot_code).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )
        demo1 = DemoTenantSlot.objects.get(slot_code="demo1")
        demo1.status = DemoTenantSlot.Status.OCUPADO
        demo1.network_key_hash = hash_demo_identifier("network", network_identifier)
        demo1.lease_started_at = timezone.now()
        demo1.lease_expires_at = timezone.now() + timedelta(hours=1)
        demo1.save()

        third_grant = allocate_demo_lease(
            visitor_identifier="visitante-rede-3",
            network_identifier=network_identifier,
        )

        self.assertEqual(third_grant.slot_code, "demo4")
        self.assertFalse(third_grant.reused)

    def test_identificadores_persistidos_sao_hmac_e_mudam_com_o_segredo(self):
        network_identifier = "203.0.113.53"
        grant = allocate_demo_lease(
            visitor_identifier="visitante-hash",
            network_identifier=network_identifier,
        )
        connection.set_schema_to_public()
        slot = DemoTenantSlot.objects.get(slot_code=grant.slot_code)
        current_hash = hash_demo_identifier("network", network_identifier)

        self.assertEqual(slot.network_key_hash, current_hash)
        self.assertNotEqual(slot.network_key_hash, network_identifier)
        self.assertNotIn(network_identifier, str(slot.__dict__))
        with override_settings(SECRET_KEY="outro-segredo-de-teste"):
            self.assertNotEqual(
                hash_demo_identifier("network", network_identifier),
                current_hash,
            )

    def test_pool_cheia_retorna_503_sem_expor_slots(self):
        now = timezone.now()
        connection.set_schema_to_public()
        DemoTenantSlot.objects.filter(slot_code="demo2").update(
            status=DemoTenantSlot.Status.OCUPADO,
            visitor_key_hash="a" * 64,
            network_key_hash="b" * 64,
            lease_started_at=now,
            lease_expires_at=now + timedelta(minutes=30),
        )

        _client, response = self._lease(
            self._public_client(remote_addr="203.0.113.20")
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "pool_full")
        serialized = response.content.decode("utf-8")
        self.assertNotIn("demo1", serialized)
        self.assertNotIn("demo2", serialized)

    def test_demo1_nao_expira_na_varredura_automatica(self):
        now = timezone.now()
        connection.set_schema_to_public()
        demo1_slot = DemoTenantSlot.objects.get(slot_code="demo1")
        demo1_slot.status = DemoTenantSlot.Status.OCUPADO
        demo1_slot.lease_started_at = now - timedelta(hours=2)
        demo1_slot.lease_expires_at = now - timedelta(hours=1)
        demo1_slot.save(
            update_fields=[
                "status",
                "lease_started_at",
                "lease_expires_at",
                "updated_at",
            ]
        )

        self.assertEqual(expire_due_demo_leases(), [])
        demo1_slot.refresh_from_db()
        self.assertEqual(demo1_slot.status, DemoTenantSlot.Status.OCUPADO)

    def test_manter_pool_demo_ignora_demo1_e_nao_reseta(self):
        connection.set_schema_to_public()
        demo1_slot = DemoTenantSlot.objects.get(slot_code="demo1")
        demo1_slot.status = DemoTenantSlot.Status.EXPIRADO
        demo1_slot.save(update_fields=["status", "updated_at"])
        output = StringIO()

        with patch(
            "tenancy.management.commands.manter_pool_demo.call_command"
        ) as reset_command:
            call_command(
                "manter_pool_demo",
                slot="demo1",
                stdout=output,
                verbosity=0,
            )

        reset_command.assert_not_called()
        demo1_slot.refresh_from_db()
        self.assertEqual(demo1_slot.status, DemoTenantSlot.Status.EXPIRADO)
        self.assertIn("tenant demo permanente", output.getvalue())

    def test_lease_rejeita_campos_e_nao_e_publicado_em_slot_demo(self):
        response = self._public_client().post(
            "/api/demo/lease/",
            data=json.dumps({"slot": "demo2"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        wrong_host_response = self._tenant_client("demo2").post(
            "/api/demo/lease/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(wrong_host_response.status_code, 404)

    def test_health_check_e_minimo_e_nao_expoe_pool(self):
        response = self._tenant_client("demo1").get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        serialized = response.content.decode("utf-8")
        self.assertNotIn("slots", serialized)
        self.assertNotIn("demo1", serialized)

    @override_settings(DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3", "demo4"))
    def test_status_informa_capacidade_agregada_sem_demo1(self):
        self._add_network_limit_slots()

        _client, response = self._status()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["enabled"], True)
        self.assertEqual(
            response.json()["capacity"],
            {"total": 3, "available": 3},
        )
        self.assertEqual(response.json()["activeLease"], {"exists": False})
        self.assertIn("no-store", response["Cache-Control"])
        serialized = response.content.decode("utf-8")
        self.assertNotIn("demo1", serialized)
        self.assertNotIn("visitor", serialized)
        self.assertNotIn("network", serialized)
        self.assertNotIn("exchange", serialized)

    @override_settings(DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3", "demo4"))
    def test_status_conta_somente_slots_livres_e_prontos(self):
        self._add_network_limit_slots()
        connection.set_schema_to_public()
        now = timezone.now()
        DemoTenantSlot.objects.filter(slot_code="demo2").update(
            status=DemoTenantSlot.Status.OCUPADO,
            lease_started_at=now,
            lease_expires_at=now + timedelta(minutes=30),
        )
        DemoTenantSlot.objects.filter(slot_code="demo3").update(
            status=DemoTenantSlot.Status.EXPIRADO,
        )

        _client, partial_response = self._status()
        DemoTenantSlot.objects.filter(slot_code="demo4").update(
            status=DemoTenantSlot.Status.BLOQUEADO,
        )
        _client, full_response = self._status()

        self.assertEqual(
            partial_response.json()["capacity"],
            {"total": 3, "available": 1},
        )
        self.assertEqual(
            full_response.json()["capacity"],
            {"total": 3, "available": 0},
        )

    def test_status_reconhece_so_o_proprio_lease_sem_muta_lo(self):
        visitor_client, lease_response = self._lease()
        lease_payload = lease_response.json()
        connection.set_schema_to_public()
        before = DemoTenantSlot.objects.filter(slot_code="demo2").values().get()

        _client, first_status = self._status(visitor_client)
        _client, second_status = self._status(visitor_client)
        _other_client, other_status = self._status(self._public_client())

        connection.set_schema_to_public()
        after = DemoTenantSlot.objects.filter(slot_code="demo2").values().get()
        self.assertEqual(before, after)
        self.assertEqual(first_status.status_code, 200)
        self.assertEqual(first_status.json(), second_status.json())
        self.assertEqual(first_status.json()["capacity"], {"total": 1, "available": 0})
        self.assertEqual(
            first_status.json()["activeLease"]["tenant"],
            "demo2",
        )
        self.assertEqual(
            first_status.json()["activeLease"]["expiresAt"],
            lease_payload["expiresAt"],
        )
        self.assertGreater(first_status.json()["activeLease"]["remainingSeconds"], 0)
        self.assertEqual(other_status.json()["activeLease"], {"exists": False})
        serialized = first_status.content.decode("utf-8")
        self.assertNotIn("exchangeToken", serialized)
        self.assertNotIn(lease_payload["exchangeToken"], serialized)

    def test_status_nao_apresenta_lease_expirado_nem_vaga_antes_do_reset(self):
        client, _lease_response = self._lease()
        connection.set_schema_to_public()
        DemoTenantSlot.objects.filter(slot_code="demo2").update(
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )

        _client, response = self._status(client)

        self.assertEqual(response.json()["activeLease"], {"exists": False})
        self.assertEqual(response.json()["capacity"], {"total": 1, "available": 0})

    def test_status_usa_throttle_separado_sem_consumir_lease(self):
        client = self._public_client(remote_addr="203.0.113.41")
        with (
            patch.object(DemoStatusRateThrottle, "rate", "2/hour", create=True),
            patch.object(DemoLeaseRateThrottle, "rate", "1/hour", create=True),
        ):
            first_status = self._status(client)[1]
            second_status = self._status(client)[1]
            third_status = self._status(client)[1]
            _client, lease_response = self._lease(client)

        self.assertEqual(first_status.status_code, 200)
        self.assertEqual(second_status.status_code, 200)
        self.assertEqual(third_status.status_code, 429)
        self.assertEqual(lease_response.status_code, 201)

    def test_status_nao_e_publicado_em_slot_temporario(self):
        response = self._tenant_client("demo2").get("/api/demo/status/")

        self.assertEqual(response.status_code, 404)

    def test_throttle_retorna_429_sem_metadata_da_pool(self):
        first_client = self._public_client(remote_addr="203.0.113.40")
        second_client = self._public_client(remote_addr="203.0.113.40")
        with patch.object(DemoLeaseRateThrottle, "rate", "1/hour", create=True):
            first_client.defaults["HTTP_X_FORWARDED_FOR"] = "192.0.2.1"
            _client, first_response = self._lease(first_client)
            second_client.defaults["HTTP_X_FORWARDED_FOR"] = "192.0.2.250"
            _client, second_response = self._lease(second_client)

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 429)
        self.assertIn("Retry-After", second_response)
        serialized = second_response.content.decode("utf-8")
        self.assertNotIn("demo1", serialized)
        self.assertNotIn("demo2", serialized)

    @override_settings(DEMO_PUBLIC_LEASE_ENABLED=False)
    def test_flag_desativada_falha_fechado(self):
        _client, response = self._lease()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "unavailable")
        connection.set_schema_to_public()
        self.assertFalse(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).exists()
        )

    def test_seed_e_ficticio_idempotente_e_isolado(self):
        allocate_demo_lease(
            visitor_identifier="visitante-seed",
            network_identifier="203.0.113.30",
        )
        allocate_demo_lease(
            visitor_identifier="visitante-seed",
            network_identifier="203.0.113.30",
        )

        with schema_context("demo2"):
            self.assertEqual(Cliente.objects.count(), 1)
            self.assertEqual(Servico.objects.count(), 2)
            self.assertEqual(Orcamento.objects.count(), 1)
            self.assertEqual(Evento.objects.count(), 1)
            self.assertTrue(Cliente.objects.get().email.endswith(".invalid"))
            self.assertTrue(Group.objects.filter(name="Demo Publica").exists())
        with schema_context("demo1"):
            self.assertEqual(Cliente.objects.count(), 0)

    def test_prepara_demo1_permanente_com_seed_e_usuario_minimo(self):
        connection.set_schema_to_public()
        DemoTenantSlot.objects.filter(slot_code="demo1").delete()

        with patch.dict(
            "os.environ",
            {"DEMO_PERMANENT_PASSWORD": "senha-permanente-segura"},
            clear=False,
        ):
            call_command(
                "preparar_demo_permanente",
                password_env="DEMO_PERMANENT_PASSWORD",
                verbosity=0,
            )

        connection.set_schema_to_public()
        self.assertFalse(DemoTenantSlot.objects.filter(slot_code="demo1").exists())
        with schema_context("demo1"):
            user = get_user_model().objects.get(username="demo")
            self.assertTrue(user.is_active)
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertTrue(user.check_password("senha-permanente-segura"))
            self.assertEqual(
                set(user.groups.values_list("name", flat=True)),
                {"Demo Publica"},
            )
            self.assertEqual(Cliente.objects.count(), 1)
            self.assertEqual(Servico.objects.count(), 2)

    def test_expiracao_remove_sessao_cache_token_e_desativa_usuario(self):
        _public_client, lease_response = self._lease()
        token = lease_response.json()["exchangeToken"]
        tenant_client = self._tenant_client("demo2")
        self.assertEqual(self._exchange(tenant_client, token).status_code, 200)

        with schema_context("demo2"):
            cache.set("demo-expiration-marker", "secret", timeout=60)
            AccessAttempt.objects.create(
                user_agent="test-agent",
                ip_address="192.0.2.10",
                username="demo",
                http_accept="application/json",
                path_info="/api/auth/login/",
                attempt_time=timezone.now(),
                get_data="",
                post_data="",
                failures_since_start=1,
            )
            self.assertTrue(Session.objects.exists())
        connection.set_schema_to_public()
        slot = DemoTenantSlot.objects.get(slot_code="demo2")
        slot.lease_expires_at = timezone.now() - timedelta(seconds=1)
        slot.save(update_fields=["lease_expires_at", "updated_at"])

        results = expire_due_demo_leases(slot_code="demo2")

        self.assertEqual(len(results), 1)
        self.assertGreaterEqual(results[0].axes_rows_removed, 1)
        connection.set_schema_to_public()
        slot.refresh_from_db()
        self.assertEqual(slot.status, DemoTenantSlot.Status.EXPIRADO)
        self.assertIsNone(slot.exchange_token_digest)
        with schema_context("demo2"):
            self.assertFalse(get_user_model().objects.get(username="demo").is_active)
            self.assertEqual(Session.objects.count(), 0)
            self.assertEqual(AccessAttempt.objects.count(), 0)
            self.assertIsNone(cache.get("demo-expiration-marker"))

    def test_falha_no_usuario_reverte_slot_e_seed(self):
        with patch(
            "tenancy.services_demo_pool.sync_demo_public_user",
            side_effect=RuntimeError("falha simulada"),
        ):
            with self.assertRaisesMessage(RuntimeError, "falha simulada"):
                allocate_demo_lease(
                    visitor_identifier="visitante-rollback",
                    network_identifier="203.0.113.31",
                )

        connection.set_schema_to_public()
        slot = DemoTenantSlot.objects.get(slot_code="demo2")
        self.assertEqual(slot.status, DemoTenantSlot.Status.LIVRE)
        self.assertEqual(slot.visitor_key_hash, "")
        with schema_context("demo2"):
            self.assertEqual(Cliente.objects.count(), 0)


class DemoPublicConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self._demo_settings = override_settings(
            DEMO_PUBLIC_LEASE_ENABLED=True,
            DEMO_PERMANENT_TENANT_SCHEMA="demo1",
            DEMO_PUBLIC_POOL_SLOTS=("demo2", "demo3", "demo4"),
            DEMO_LEASE_DURATION_MINUTES=60,
            DEMO_EXCHANGE_TOKEN_TTL_SECONDS=300,
            DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2,
        )
        self._demo_settings.enable()
        super().setUp()
        self._cleanup_demo_pool()
        call_command("provisionar_pool_demo", slots=4, verbosity=0)

    def tearDown(self):
        try:
            self._cleanup_demo_pool()
            super().tearDown()
        finally:
            self._demo_settings.disable()

    @staticmethod
    def _cleanup_demo_pool():
        connection.set_schema_to_public()
        Domain.objects.filter(
            domain__endswith=".api-demo-rh.taquiondev.com.br"
        ).delete()
        DemoTenantSlot.objects.filter(slot_code__in=DEMO_POOL_SCHEMA_NAMES).delete()
        for tenant in list(
            Tenant.objects.filter(schema_name__in=DEMO_POOL_SCHEMA_NAMES)
        ):
            tenant.delete(force_drop=True)
        connection.set_schema_to_public()

    @staticmethod
    def _allocate_in_thread():
        close_old_connections()
        try:
            connection.set_schema_to_public()
            grant = allocate_demo_lease(
                visitor_identifier="visitante-concorrente",
                network_identifier="198.51.100.77",
            )
            return grant.slot_code, grant.reused
        finally:
            close_old_connections()

    @staticmethod
    def _allocate_network_in_thread(index):
        close_old_connections()
        try:
            connection.set_schema_to_public()
            try:
                grant = allocate_demo_lease(
                    visitor_identifier=f"visitante-rede-concorrente-{index}",
                    network_identifier="198.51.100.79",
                )
                return "granted", grant.slot_code
            except DemoNetworkLimitExceeded:
                return "network_limit", None
        finally:
            close_old_connections()

    def test_mesmo_visitante_concorrente_recebe_um_unico_slot(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: self._allocate_in_thread(), range(2)))

        self.assertEqual({slot_code for slot_code, _reused in results}, {"demo2"})
        self.assertEqual(sorted(reused for _slot, reused in results), [False, True])
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).count(),
            1,
        )

    def test_tres_visitantes_concorrentes_da_mesma_rede_ocupam_no_maximo_dois_slots(self):
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(
                executor.map(self._allocate_network_in_thread, range(3))
            )

        self.assertEqual(
            sorted(outcome for outcome, _slot_code in results),
            ["granted", "granted", "network_limit"],
        )
        self.assertEqual(
            {slot_code for outcome, slot_code in results if outcome == "granted"},
            {"demo2", "demo3"},
        )
        connection.set_schema_to_public()
        self.assertEqual(
            DemoTenantSlot.objects.filter(status=DemoTenantSlot.Status.OCUPADO).count(),
            2,
        )

    def test_manutencao_expira_reseta_semeia_e_libera_slot(self):
        grant = allocate_demo_lease(
            visitor_identifier="visitante-manutencao",
            network_identifier="198.51.100.78",
        )
        connection.set_schema_to_public()
        slot = DemoTenantSlot.objects.get(slot_code=grant.slot_code)
        slot.lease_expires_at = timezone.now() - timedelta(seconds=1)
        slot.save(update_fields=["lease_expires_at", "updated_at"])

        call_command("manter_pool_demo", slot=grant.slot_code, verbosity=0)

        connection.set_schema_to_public()
        slot.refresh_from_db()
        self.assertEqual(slot.status, DemoTenantSlot.Status.LIVRE)
        self.assertEqual(slot.visitor_key_hash, "")
        self.assertIsNone(slot.lease_expires_at)
        with schema_context(grant.slot_code):
            self.assertFalse(get_user_model().objects.filter(username="demo").exists())
            self.assertEqual(Cliente.objects.count(), 1)
            self.assertEqual(Servico.objects.count(), 2)
            self.assertEqual(Orcamento.objects.count(), 1)
