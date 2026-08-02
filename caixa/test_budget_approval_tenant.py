from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from tenancy.test_helpers import MultiTenantTestCase, public_schema

from .models import (
    Cliente,
    ConfiguracaoFinanceira,
    DespesaOperacional,
    Evento,
    ObrigacaoFinanceira,
    Orcamento,
    OrcamentoItem,
    ReceitaOperacional,
    Servico,
)
from .models_custos_extras import EventoCustoExtra, OrcamentoCustoExtra
from .models_servico import EventoCustoServico
from .permissions import APPROVE_BUDGET_PERMISSION, can_approve_budget
from .views_orcamentos_api import api_aprovar_orcamento


class BudgetApprovalTenantTests(MultiTenantTestCase):
    """Cobre aprovação no schema tenant.

    caixa.tests.OrcamentosApiTests continua em TestCase e ainda executa no
    public; não é uma cobertura válida do fluxo tenant nesta etapa.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, _ = cls.create_tenant(
            "tenant_b",
            "Tenant B",
            "tenant-b.localhost",
        )

    def setUp(self):
        super().setUp()
        self.primary_schema_name = self.primary_tenant.schema_name
        self.secondary_schema_name = self.secondary_tenant.schema_name
        self.primary_client = self.client_for_tenant(self.primary_tenant)

        with self.in_schema(self.primary_schema_name):
            self.cliente = Cliente.objects.create(
                nome_razao_social="Cliente aprovação tenant",
                cpf_cnpj="11.111.111/0001-11",
            )
            self.configuracao = ConfiguracaoFinanceira.objects.create(
                nome="Configuração aprovação tenant",
                valor_alimentacao=Decimal("20.00"),
                valor_transporte=Decimal("10.00"),
                margem_lucro=Decimal("0.30"),
                aliquota_imposto=Decimal("0.05"),
                data_inicio_vigencia=date(2026, 1, 1),
            )
            self.servico = Servico.objects.create(
                nome="Serviço aprovação tenant",
                codigo="servico-aprovacao-tenant",
                diaria_padrao=Decimal("100.00"),
            )
            self.orcamento = Orcamento.objects.create(
                cliente=self.cliente,
                configuracao_financeira=self.configuracao,
                numero="ORC-APROVACAO-TENANT",
                nome_evento="Evento aprovação tenant",
                data_evento=date(2026, 6, 20),
            )
            OrcamentoItem.objects.create(
                orcamento=self.orcamento,
                servico=self.servico,
                horas_por_dia=8,
                quantidade_dias=1,
                quantidade_pessoas=1,
            )
            OrcamentoCustoExtra.objects.create(
                orcamento=self.orcamento,
                categoria="logistica",
                descricao="Frete aprovação tenant",
                valor_previsto=Decimal("50.00"),
                data_vencimento=self.orcamento.data_evento,
            )

            self.approve_permission = Permission.objects.get(
                content_type__app_label="caixa",
                codename="approve_orcamento",
            )
            view_permission = Permission.objects.get(
                content_type__app_label="caixa",
                codename="view_orcamento",
            )
            change_permission = Permission.objects.get(
                content_type__app_label="caixa",
                codename="change_orcamento",
            )

            self.approver = self.create_user(
                self.primary_schema_name,
                "approver-tenant",
            )
            self.approver.user_permissions.add(view_permission, self.approve_permission)

            self.change_only_user = self.create_user(
                self.primary_schema_name,
                "change-only-tenant",
            )
            self.change_only_user.user_permissions.add(view_permission, change_permission)

            self.view_only_user = self.create_user(
                self.primary_schema_name,
                "view-only-tenant",
            )
            self.view_only_user.user_permissions.add(view_permission)

        # TenantTestCase restaura a conexão para public ao sair de schema_context.
        # Force_login atualiza last_login, portanto deve rodar no schema do usuário.
        self.switch_to_tenant(self.primary_tenant)

    def _url(self):
        return reverse("caixa:api_aprovar_orcamento", args=[self.orcamento.pk])

    def _permissions_payload(self, user):
        self.primary_client.force_login(user)
        response = self.primary_client.get(reverse("caixa:api_orcamentos"))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["data"]["permissions"]

    def _assert_no_partial_approval(self):
        self.orcamento.refresh_from_db()
        self.assertEqual(self.orcamento.status, "rascunho")
        self.assertFalse(Evento.objects.filter(orcamento=self.orcamento).exists())
        self.assertEqual(ReceitaOperacional.objects.count(), 0)
        self.assertEqual(DespesaOperacional.objects.count(), 0)
        self.assertEqual(EventoCustoServico.objects.count(), 0)
        self.assertEqual(EventoCustoExtra.objects.count(), 0)
        self.assertEqual(ObrigacaoFinanceira.objects.count(), 0)

    def _approve_as_authorized_user(self):
        self.primary_client.force_login(self.approver)
        response = self.primary_client.post(self._url())
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def test_permission_payload_uses_dedicated_permission_and_administrator_profile(self):
        self.assertEqual(APPROVE_BUDGET_PERMISSION, "caixa.approve_orcamento")
        self.assertTrue(can_approve_budget(self.approver))
        self.assertFalse(can_approve_budget(self.change_only_user))
        self.assertFalse(can_approve_budget(self.view_only_user))
        self.assertTrue(
            Group.objects.get(name="Administrador").permissions.filter(
                pk=self.approve_permission.pk
            ).exists()
        )

        self.assertTrue(self._permissions_payload(self.approver)["canApprove"])
        self.assertFalse(self._permissions_payload(self.change_only_user)["canApprove"])
        self.assertFalse(self._permissions_payload(self.view_only_user)["canApprove"])

    def test_change_permission_without_approval_returns_403(self):
        self.primary_client.force_login(self.change_only_user)
        response = self.primary_client.post(self._url())

        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json(), {"detail": "Permission denied."})
        self._assert_no_partial_approval()

    def test_authorized_user_approves_in_its_tenant_without_superuser(self):
        self.assertFalse(self.approver.is_staff)
        self.assertFalse(self.approver.is_superuser)
        self.assertTrue(self._permissions_payload(self.approver)["canApprove"])

        payload = self._approve_as_authorized_user().json()["data"]

        self.orcamento.refresh_from_db()
        evento = Evento.objects.get(orcamento=self.orcamento)
        self.assertEqual(self.orcamento.status, "aprovado")
        self.assertEqual(payload["event"]["id"], evento.id)
        self.assertTrue(ReceitaOperacional.objects.filter(evento=evento).exists())
        self.assertTrue(DespesaOperacional.objects.filter(evento=evento).exists())
        self.assertTrue(EventoCustoServico.objects.filter(evento=evento).exists())
        self.assertTrue(EventoCustoExtra.objects.filter(evento=evento).exists())
        self.assertTrue(ObrigacaoFinanceira.objects.filter(evento=evento).exists())

        with self.in_schema(self.secondary_schema_name):
            self.assertEqual(Orcamento.objects.count(), 0)
            self.assertEqual(Evento.objects.count(), 0)
            self.assertEqual(ReceitaOperacional.objects.count(), 0)
            self.assertEqual(DespesaOperacional.objects.count(), 0)
            self.assertEqual(EventoCustoServico.objects.count(), 0)
            self.assertEqual(EventoCustoExtra.objects.count(), 0)
            self.assertEqual(ObrigacaoFinanceira.objects.count(), 0)

    def test_public_schema_cannot_execute_operational_approval(self):
        request = APIRequestFactory().post(self._url())
        force_authenticate(request, user=self.approver)

        with public_schema():
            response = api_aprovar_orcamento(request, self.orcamento.pk)

        self.assertEqual(response.status_code, 403)

        with self.in_schema(self.primary_schema_name):
            self._assert_no_partial_approval()

    def test_failure_during_event_creation_rolls_back_and_allows_retry(self):
        self.primary_client.force_login(self.approver)
        with patch(
            "caixa.services_orcamentos.criar_ou_atualizar_evento_do_orcamento",
            side_effect=RuntimeError("falha injetada na criação do evento"),
        ):
            with self.assertLogs("caixa.services_cadastros", level="ERROR") as logs:
                response = self.primary_client.post(self._url())

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "Não foi possível aprovar o orçamento. "
                    "Tente novamente ou contate o suporte."
                )
            },
        )
        self.assertIn("budget_approval_failed", "\n".join(logs.output))
        self._assert_no_partial_approval()

        self._approve_as_authorized_user()
        self.orcamento.refresh_from_db()
        self.assertEqual(self.orcamento.status, "aprovado")

    def test_failure_during_cost_synchronization_rolls_back_all_records(self):
        self.primary_client.force_login(self.approver)
        with patch.object(
            Orcamento,
            "sincronizar_custos_servicos_evento",
            side_effect=RuntimeError("falha injetada na sincronização de custos"),
        ):
            with self.assertLogs("caixa.services_cadastros", level="ERROR"):
                response = self.primary_client.post(self._url())

        self.assertEqual(response.status_code, 400, response.content)
        self._assert_no_partial_approval()

    def test_failure_in_event_signal_recalculation_rolls_back_all_records(self):
        self.primary_client.force_login(self.approver)
        with patch.object(
            Evento,
            "recalcular_receita_prevista",
            side_effect=RuntimeError("falha injetada no signal de receita"),
        ):
            with self.assertLogs("caixa.services_cadastros", level="ERROR"):
                response = self.primary_client.post(self._url())

        self.assertEqual(response.status_code, 400, response.content)
        self._assert_no_partial_approval()

    def test_reapproval_is_rejected_without_changing_event_or_movements(self):
        self._approve_as_authorized_user()
        evento = Evento.objects.get(orcamento=self.orcamento)
        counts_before = {
            "events": Evento.objects.filter(orcamento=self.orcamento).count(),
            "revenues": ReceitaOperacional.objects.filter(evento=evento).count(),
            "expenses": DespesaOperacional.objects.filter(evento=evento).count(),
            "service_costs": EventoCustoServico.objects.filter(evento=evento).count(),
            "extra_costs": EventoCustoExtra.objects.filter(evento=evento).count(),
            "obligations": ObrigacaoFinanceira.objects.filter(evento=evento).count(),
        }

        self.primary_client.force_login(self.approver)
        response = self.primary_client.post(self._url())

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("rascunho ou enviados", response.json()["detail"])
        self.assertEqual(
            counts_before,
            {
                "events": Evento.objects.filter(orcamento=self.orcamento).count(),
                "revenues": ReceitaOperacional.objects.filter(evento=evento).count(),
                "expenses": DespesaOperacional.objects.filter(evento=evento).count(),
                "service_costs": EventoCustoServico.objects.filter(evento=evento).count(),
                "extra_costs": EventoCustoExtra.objects.filter(evento=evento).count(),
                "obligations": ObrigacaoFinanceira.objects.filter(evento=evento).count(),
            },
        )
