import json
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django_tenants.utils import schema_context

from caixa.demo_policy import (
    assert_demo_write_allowed,
    demo_object_flags,
    is_demo_seed_object,
)
from caixa.demo_seed import (
    DEMO_SEED_KEYS,
    DEMO_SEED_SPEC,
    inspect_demo_seed_readiness,
)
from caixa.constants_financeiros import TIPO_CUSTO_DIARIAS
from caixa.models import (
    Cliente,
    ConfiguracaoFinanceira,
    DespesaOperacional,
    Evento,
    Orcamento,
    OrcamentoItem,
    ReceitaOperacional,
    Servico,
)
from caixa.models_servico import EventoCustoServico
from caixa.models_pagamentos import PagamentoEventoCustoServico
from caixa.permissions import PERMISSION_PROFILES, sincronizar_grupos_permissoes
from caixa.services_cadastros import aprovar_orcamento
from caixa.services_obrigacoes import liquidar_custo_servico_evento
from caixa.views_orcamentos_api import _salvar_orcamento_from_payload
from tenancy.models import DemoTenantSlot
from tenancy.services_demo_pool import (
    DemoPoolUnavailable,
    _demo_allocation_transaction,
    allocate_demo_lease,
    mark_demo_slot_blocked,
    seed_demo_tenant,
    sync_demo_public_user,
)
from tenancy.test_helpers import MultiTenantTestCase


class DemoSeedProtectionTests(MultiTenantTestCase):
    primary_schema_name = "demo2"
    primary_tenant_name = "Demo 2"
    primary_domain = "demo2.api-demo-rh.taquiondev.com.br"

    def setUp(self):
        self._demo_settings = override_settings(
            DEMO_PUBLIC_LEASE_ENABLED=True,
            DEMO_PERMANENT_TENANT_SCHEMA="demo1",
            DEMO_PUBLIC_POOL_SLOTS=("demo2",),
            DEMO_LEASE_DURATION_MINUTES=60,
            DEMO_EXCHANGE_TOKEN_TTL_SECONDS=300,
            DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2,
            SESSION_COOKIE_SECURE=False,
        )
        self._demo_settings.enable()
        super().setUp()
        seed_demo_tenant("demo2")
        self.demo_user = sync_demo_public_user("demo2")
        connection.set_schema_to_public()
        DemoTenantSlot.objects.all().delete()
        DemoTenantSlot.objects.create(
            tenant=self.primary_tenant,
            slot_code="demo2",
            status=DemoTenantSlot.Status.LIVRE,
        )
        self.tenant_client = self.client_for_tenant(self.primary_tenant)
        self.switch_to_tenant(self.primary_tenant)
        self.tenant_client.force_login(self.demo_user)

    def tearDown(self):
        try:
            super().tearDown()
        finally:
            self._demo_settings.disable()

    def _clear_seed_roots(self):
        with schema_context("demo2"):
            Evento.objects.all().delete()
            Orcamento.objects.all().delete()
            Servico.objects.all().delete()
            Cliente.objects.all().delete()
            ConfiguracaoFinanceira.objects.all().delete()

    def _common_budget_payload(self, budget, item):
        return {
            "clientId": budget.cliente_id,
            "configurationId": budget.configuracao_financeira_id,
            "number": budget.numero,
            "eventName": budget.nome_evento,
            "eventDate": budget.data_evento.isoformat(),
            "local": budget.local,
            "validUntil": budget.validade.isoformat() if budget.validade else "",
            "status": budget.status,
            "notes": budget.observacoes,
            "items": [
                {
                    "id": item.pk,
                    "serviceId": item.servico_id,
                    "hoursPerDay": "6.00",
                    "daysCount": 2,
                    "peopleCount": 3,
                }
            ],
            "extraCosts": [],
        }

    def test_models_expose_internal_nullable_unique_non_editable_key(self):
        for model in (ConfiguracaoFinanceira, Cliente, Servico, Orcamento):
            field = model._meta.get_field("demo_seed_key")
            self.assertTrue(field.null)
            self.assertTrue(field.blank)
            self.assertTrue(field.unique)
            self.assertFalse(field.editable)

        with schema_context("demo2"):
            configuration = ConfiguracaoFinanceira.objects.create(
                nome="Configuracao comum",
                data_inicio_vigencia=date(2026, 7, 16),
                ativa=False,
            )
            client = Cliente.objects.create(
                nome_razao_social="Cliente sem seed key",
                cpf_cnpj="33.333.333/0001-33",
            )
            service = Servico.objects.create(
                nome="Servico sem seed key",
                codigo="servico-sem-seed-key",
                diaria_padrao=Decimal("100.00"),
            )
            budget = Orcamento.objects.create(
                cliente=client,
                configuracao_financeira=configuration,
                numero="COMMON-NULL-001",
                nome_evento="Evento sem seed key",
                data_evento=date(2026, 9, 1),
            )

            for common in (configuration, client, service, budget):
                self.assertIsNone(common.demo_seed_key)

    def test_seed_has_exactly_five_canonical_keys_and_is_idempotent(self):
        first = seed_demo_tenant("demo2")
        second = seed_demo_tenant("demo2")

        self.assertEqual(first, second)
        with schema_context("demo2"):
            readiness = inspect_demo_seed_readiness()
            self.assertTrue(readiness.ready, readiness.errors)
            self.assertEqual(set(readiness.objects), set(DEMO_SEED_KEYS))
            self.assertEqual(len(readiness.objects), 5)

    def test_seed_is_atomic_when_second_item_creation_fails(self):
        self._clear_seed_roots()
        original_create = OrcamentoItem.objects.create
        calls = 0

        def fail_second_item(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("falha atomica simulada")
            return original_create(*args, **kwargs)

        with patch.object(OrcamentoItem.objects, "create", side_effect=fail_second_item):
            with self.assertRaisesMessage(RuntimeError, "falha atomica simulada"):
                seed_demo_tenant("demo2")

        with schema_context("demo2"):
            self.assertEqual(ConfiguracaoFinanceira.objects.count(), 0)
            self.assertEqual(Cliente.objects.count(), 0)
            self.assertEqual(Servico.objects.count(), 0)
            self.assertEqual(Orcamento.objects.count(), 0)

    def test_payload_cannot_expose_set_or_change_seed_key(self):
        response = self.tenant_client.post(
            reverse("caixa:api_clientes"),
            data=json.dumps(
                {
                    "name": "Cliente comum",
                    "document": "22.222.222/0001-22",
                    "personType": "PJ",
                    "demoSeedKey": DEMO_SEED_KEYS[0],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        serialized = json.dumps(response.json())
        self.assertNotIn("demoSeedKey", serialized)
        with schema_context("demo2"):
            common = Cliente.objects.get(cpf_cnpj="22.222.222/0001-22")
            self.assertIsNone(common.demo_seed_key)

        update_response = self.tenant_client.put(
            reverse("caixa:api_cliente_detalhe", args=[common.pk]),
            data=json.dumps(
                {
                    "name": "Cliente comum atualizado",
                    "document": "22.222.222/0001-22",
                    "personType": "PJ",
                    "demoSeedKey": DEMO_SEED_SPEC["client"]["key"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.content)
        self.assertNotIn("demoSeedKey", json.dumps(update_response.json()))
        with schema_context("demo2"):
            common.refresh_from_db()
            self.assertEqual(common.nome_razao_social, "Cliente comum atualizado")
            self.assertIsNone(common.demo_seed_key)

    def test_seed_client_is_visible_flagged_and_cannot_be_changed(self):
        response = self.tenant_client.get(reverse("caixa:api_clientes"))
        self.assertEqual(response.status_code, 200, response.content)
        seed_payload = next(
            item for item in response.json()["data"]["clients"] if item["isSeed"]
        )
        self.assertTrue(seed_payload["isReadOnly"])
        self.assertNotIn("demoSeedKey", json.dumps(seed_payload))

        with schema_context("demo2"):
            seed_client = Cliente.objects.get(demo_seed_key__isnull=False)
            original_name = seed_client.nome_razao_social
        update_response = self.tenant_client.put(
            reverse("caixa:api_cliente_detalhe", args=[seed_client.pk]),
            data=json.dumps(
                {
                    "name": "Tentativa de alteracao",
                    "document": seed_client.cpf_cnpj,
                    "personType": "PJ",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 403, update_response.content)
        with schema_context("demo2"):
            seed_client.refresh_from_db()
            self.assertEqual(seed_client.nome_razao_social, original_name)

    def test_seed_roots_and_derivatives_cannot_be_changed_through_direct_api(self):
        with schema_context("demo2"):
            seed_service = Servico.objects.get(
                demo_seed_key=DEMO_SEED_SPEC["daily_service"]["key"]
            )
            seed_configuration = ConfiguracaoFinanceira.objects.get(
                demo_seed_key=DEMO_SEED_SPEC["configuration"]["key"]
            )
            seed_budget = Orcamento.objects.get(
                demo_seed_key=DEMO_SEED_SPEC["budget"]["key"]
            )
            seed_event = seed_budget.evento
            seed_revenue = ReceitaOperacional.objects.filter(evento=seed_event).first()
            seed_expense = DespesaOperacional.objects.filter(evento=seed_event).first()
            original = {
                "service_name": seed_service.nome,
                "configuration_name": seed_configuration.nome,
                "budget_name": seed_budget.nome_evento,
                "event_name": seed_event.nome_evento,
                "revenue_description": seed_revenue.descricao,
                "expense_description": seed_expense.descricao,
            }

        attempts = (
            ("api_servico_detalhe", seed_service.pk),
            ("api_configuracao_financeira_detalhe", seed_configuration.pk),
            ("api_orcamento_detalhe", seed_budget.pk),
            ("api_evento_detalhe", seed_event.pk),
            ("api_receita_detalhe", seed_revenue.pk),
            ("api_despesa_detalhe", seed_expense.pk),
        )
        for route_name, object_id in attempts:
            response = self.tenant_client.put(
                reverse(f"caixa:{route_name}", args=[object_id]),
                data=json.dumps({}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 403, (route_name, response.content))

        with schema_context("demo2"):
            seed_service.refresh_from_db()
            seed_configuration.refresh_from_db()
            seed_budget.refresh_from_db()
            seed_event.refresh_from_db()
            seed_revenue.refresh_from_db()
            seed_expense.refresh_from_db()
            self.assertEqual(seed_service.nome, original["service_name"])
            self.assertEqual(seed_configuration.nome, original["configuration_name"])
            self.assertEqual(seed_budget.nome_evento, original["budget_name"])
            self.assertEqual(seed_event.nome_evento, original["event_name"])
            self.assertEqual(seed_revenue.descricao, original["revenue_description"])
            self.assertEqual(seed_expense.descricao, original["expense_description"])

    def test_common_object_is_editable_and_seed_references_do_not_taint_budget(self):
        with schema_context("demo2"):
            seed_client = Cliente.objects.get(demo_seed_key__isnull=False)
            seed_configuration = ConfiguracaoFinanceira.objects.get(
                demo_seed_key__isnull=False
            )
            seed_service = Servico.objects.filter(demo_seed_key__isnull=False).first()
            budget = Orcamento.objects.create(
                cliente=seed_client,
                configuracao_financeira=seed_configuration,
                numero="COMMON-001",
                nome_evento="Evento comum",
                data_evento=date(2026, 8, 20),
                status="rascunho",
            )
            item = OrcamentoItem.objects.create(
                orcamento=budget,
                servico=seed_service,
                horas_por_dia=Decimal("8.00"),
                quantidade_dias=1,
                quantidade_pessoas=1,
            )
            self.assertFalse(is_demo_seed_object(budget))
            assert_demo_write_allowed(self.demo_user, budget)

            old_item_id = item.pk
            saved = _salvar_orcamento_from_payload(
                self._common_budget_payload(budget, item),
                orcamento=budget,
                user=self.demo_user,
            )
            self.assertEqual(saved.itens.count(), 1)
            self.assertNotEqual(saved.itens.get().pk, old_item_id)
            self.assertEqual(saved.itens.get().quantidade_dias, 2)

    def test_seed_nested_replace_all_is_blocked_before_children_change(self):
        with schema_context("demo2"):
            seed_budget = Orcamento.objects.get(demo_seed_key__isnull=False)
            item_ids = list(seed_budget.itens.values_list("pk", flat=True))
            payload = self._common_budget_payload(seed_budget, seed_budget.itens.first())

            with self.assertRaises(PermissionDenied):
                _salvar_orcamento_from_payload(
                    payload,
                    orcamento=seed_budget,
                    user=self.demo_user,
                )

            self.assertEqual(
                list(seed_budget.itens.values_list("pk", flat=True)),
                item_ids,
            )

    def test_derived_seed_objects_are_protected_from_direct_and_indirect_write(self):
        with schema_context("demo2"):
            budget = Orcamento.objects.get(demo_seed_key__isnull=False)
            event = budget.evento
            objects = [
                event,
                ReceitaOperacional.objects.filter(evento=event).first(),
                DespesaOperacional.objects.filter(evento=event).first(),
                EventoCustoServico.objects.filter(evento=event).first(),
            ]
            for obj in objects:
                self.assertTrue(is_demo_seed_object(obj))
                self.assertEqual(
                    demo_object_flags(obj),
                    {"isSeed": True, "isReadOnly": True},
                )
                with self.assertRaises(PermissionDenied):
                    assert_demo_write_allowed(self.demo_user, obj)

    def test_seed_service_cost_cannot_be_settled_or_paid_indirectly(self):
        with schema_context("demo2"):
            budget = Orcamento.objects.get(demo_seed_key__isnull=False)
            service_cost = EventoCustoServico.objects.filter(
                evento=budget.evento
            ).first()
            payment_count = PagamentoEventoCustoServico.objects.filter(
                custo_servico=service_cost
            ).count()
            original_paid = service_cost.total_pago_diarias
            original_settled = service_cost.diarias_quitadas

            with self.assertRaises(PermissionDenied):
                liquidar_custo_servico_evento(
                    service_cost.pk,
                    TIPO_CUSTO_DIARIAS,
                    {
                        "realizedAmount": "1.00",
                        "paymentDate": date(2026, 7, 16).isoformat(),
                    },
                    self.demo_user,
                )

            service_cost.refresh_from_db()
            self.assertEqual(
                PagamentoEventoCustoServico.objects.filter(
                    custo_servico=service_cost
                ).count(),
                payment_count,
            )
            self.assertEqual(service_cost.total_pago_diarias, original_paid)
            self.assertEqual(service_cost.diarias_quitadas, original_settled)

    def test_approval_allows_common_budget_but_rejects_seed_and_reapproval(self):
        with schema_context("demo2"):
            seed_budget = Orcamento.objects.get(demo_seed_key__isnull=False)
            seed_result = aprovar_orcamento(seed_budget, self.demo_user)
            self.assertFalse(seed_result["ok"])
            self.assertEqual(seed_result["codigo"], "permission_denied")

            common_client = Cliente.objects.create(
                nome_razao_social="Cliente aprovacao comum",
                cpf_cnpj="33.333.333/0001-33",
            )
            configuration = ConfiguracaoFinanceira.objects.get(
                demo_seed_key__isnull=False
            )
            service = Servico.objects.filter(demo_seed_key__isnull=False).first()
            budget = Orcamento.objects.create(
                cliente=common_client,
                configuracao_financeira=configuration,
                numero="COMMON-APPROVE-001",
                nome_evento="Evento aprovavel",
                data_evento=date(2026, 9, 1),
            )
            OrcamentoItem.objects.create(
                orcamento=budget,
                servico=service,
                horas_por_dia=8,
                quantidade_dias=1,
                quantidade_pessoas=1,
            )

            first = aprovar_orcamento(budget, self.demo_user)
            self.assertTrue(first["ok"])
            event_id = first["evento"].pk
            counts = (
                Evento.objects.count(),
                ReceitaOperacional.objects.count(),
                DespesaOperacional.objects.count(),
            )
            second = aprovar_orcamento(budget, self.demo_user)
            self.assertFalse(second["ok"])
            self.assertEqual(second["codigo"], "invalid_state")
            self.assertEqual(
                counts,
                (
                    Evento.objects.count(),
                    ReceitaOperacional.objects.count(),
                    DespesaOperacional.objects.count(),
                ),
            )
            self.assertTrue(Evento.objects.filter(pk=event_id).exists())

    def test_legacy_schema_fails_closed_and_slot_block_is_persisted(self):
        with schema_context("demo2"):
            Cliente.objects.filter(demo_seed_key__isnull=False).update(
                nome_razao_social="Alteracao legada que nao pode ser sobrescrita"
            )
            legacy_client = Cliente.objects.get(demo_seed_key__isnull=False)
            for entry in DEMO_SEED_SPEC.values():
                entry["model"].objects.update(demo_seed_key=None)

        write_response = self.tenant_client.put(
            reverse("caixa:api_cliente_detalhe", args=[legacy_client.pk]),
            data=json.dumps(
                {
                    "name": "Escrita que deve falhar fechada",
                    "document": legacy_client.cpf_cnpj,
                    "personType": "PJ",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(write_response.status_code, 403, write_response.content)
        with schema_context("demo2"):
            legacy_client.refresh_from_db()
            self.assertEqual(
                legacy_client.nome_razao_social,
                "Alteracao legada que nao pode ser sobrescrita",
            )

        connection.set_schema_to_public()
        with self.assertRaises(DemoPoolUnavailable) as captured_error:
            allocate_demo_lease(
                visitor_identifier="legacy-visitor",
                network_identifier="192.0.2.10",
            )

        slot = DemoTenantSlot.objects.get(slot_code="demo2")
        self.assertEqual(
            slot.status,
            DemoTenantSlot.Status.BLOQUEADO,
            f"error={captured_error.exception!r}; "
            f"cause={captured_error.exception.__cause__!r}; notes={slot.notes!r}",
        )
        self.assertEqual(slot.visitor_key_hash, "")
        with schema_context("demo2"):
            self.assertFalse(inspect_demo_seed_readiness().ready)
            self.assertTrue(
                Cliente.objects.filter(
                    nome_razao_social=(
                        "Alteracao legada que nao pode ser sobrescrita"
                    )
                ).exists()
            )

    def test_slot_block_survives_later_allocation_transaction_rollback(self):
        connection.set_schema_to_public()
        slot = DemoTenantSlot.objects.get(slot_code="demo2")
        blocked_slot_ids = set()

        with self.assertRaisesMessage(RuntimeError, "falha posterior simulada"):
            with _demo_allocation_transaction(blocked_slot_ids):
                locked_slot = DemoTenantSlot.objects.select_for_update().get(pk=slot.pk)
                mark_demo_slot_blocked(
                    locked_slot,
                    "Bloqueio que deve sobreviver ao rollback.",
                )
                blocked_slot_ids.add(locked_slot.pk)
                raise RuntimeError("falha posterior simulada")

        slot.refresh_from_db()
        self.assertEqual(slot.status, DemoTenantSlot.Status.BLOQUEADO)
        self.assertEqual(slot.visitor_key_hash, "")

    def test_backfill_requires_dry_run_or_strong_confirmation(self):
        with self.assertRaises(CommandError):
            call_command(
                "backfill_demo_seed_keys",
                schema="public",
                dry_run=True,
                verbosity=0,
            )
        with self.assertRaises(CommandError):
            call_command(
                "backfill_demo_seed_keys",
                schema="rh_teste",
                dry_run=True,
                verbosity=0,
            )
        with self.assertRaises(CommandError):
            call_command(
                "backfill_demo_seed_keys",
                schema="demo2",
                confirm="demo2",
                verbosity=0,
            )

        with schema_context("demo2"):
            for entry in DEMO_SEED_SPEC.values():
                entry["model"].objects.update(demo_seed_key=None)

        output = StringIO()
        call_command(
            "backfill_demo_seed_keys",
            schema="demo2",
            dry_run=True,
            stdout=output,
            verbosity=0,
        )
        self.assertIn("DRY-RUN", output.getvalue())
        with schema_context("demo2"):
            self.assertFalse(inspect_demo_seed_readiness().ready)

        call_command(
            "backfill_demo_seed_keys",
            schema="demo2",
            confirm="MARCAR-SEED demo2",
            verbosity=0,
        )
        with schema_context("demo2"):
            self.assertTrue(inspect_demo_seed_readiness().ready)

    def test_permissions_remain_exact_and_missing_codename_fails_explicitly(self):
        with schema_context("demo2"):
            sincronizar_grupos_permissoes()
            group = Group.objects.get(name="Demo Publica")
            expected = set(PERMISSION_PROFILES["Demo Publica"])
            actual = set(group.permissions.values_list("codename", flat=True))
            self.assertEqual(actual, expected)
            self.assertEqual(len(actual), 22)
            self.assertFalse(any(name.startswith("delete_") for name in actual))
            self.assertFalse(self.demo_user.user_permissions.exists())
            self.assertFalse(self.demo_user.is_staff)
            self.assertFalse(self.demo_user.is_superuser)

            broken_profile = [*PERMISSION_PROFILES["Demo Publica"], "missing_demo_perm"]
            with patch.dict(
                PERMISSION_PROFILES,
                {"Demo Publica": broken_profile},
            ):
                with self.assertRaises(ImproperlyConfigured):
                    sincronizar_grupos_permissoes()
