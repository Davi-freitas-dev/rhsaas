import json
from datetime import date
from decimal import Decimal
from threading import Event, Lock, Thread
from time import monotonic
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse

from tenancy.test_helpers import (
    MultiTenantTestCase,
    TenantAppTestCase,
    TenantTransactionTestCase,
)

from . import views_orcamentos_api
from .models import Cliente, ConfiguracaoFinanceira, Orcamento, Servico
from .views_configuracoes_financeiras_api import _salvar_configuracao_response


class MultiplasConfiguracoesFinanceirasAtivasTests(TenantAppTestCase):
    def setUp(self):
        super().setUp()
        self.usuario = get_user_model().objects.create_superuser(
            username="configuracoes-multiplas-ativas",
            email="configuracoes@example.com",
            password="senha-segura",
        )
        self.http = Client()
        self.http.force_login(self.usuario)
        self.cliente = Cliente.objects.create(
            nome_razao_social="Cliente Configuracoes",
            tipo_pessoa="PJ",
            cpf_cnpj="12.345.678/0001-99",
        )
        self.servico = Servico.objects.create(
            nome="Servico Configuracoes",
            codigo="servico-configuracoes",
            diaria_padrao=Decimal("100.00"),
            valor_unitario=Decimal("100.00"),
            horas_base_diaria=8,
            percentual_hora_extra=Decimal("2.00"),
        )

    def criar_configuracao(
        self,
        nome,
        *,
        alimentacao="10.00",
        transporte="5.00",
        margem="0.10",
        imposto="0.01",
        ativa=True,
    ):
        return ConfiguracaoFinanceira.objects.create(
            nome=nome,
            valor_alimentacao=Decimal(alimentacao),
            valor_transporte=Decimal(transporte),
            margem_lucro=Decimal(margem),
            aliquota_imposto=Decimal(imposto),
            ativa=ativa,
            data_inicio_vigencia=date(2026, 1, 1),
        )

    def configuracao_payload(self, configuracao, **overrides):
        payload = {
            "name": configuracao.nome,
            "mealAmount": f"{configuracao.valor_alimentacao:.2f}",
            "transportAmount": f"{configuracao.valor_transporte:.2f}",
            "profitMargin": f"{configuracao.margem_lucro:.2f}",
            "taxRate": f"{configuracao.aliquota_imposto:.2f}",
            "effectiveDate": configuracao.data_inicio_vigencia.isoformat(),
            "isActive": configuracao.ativa,
            "notes": configuracao.observacao,
        }
        payload.update(overrides)
        return payload

    def orcamento_payload(self, configuracao, numero, *, item=None):
        item_payload = {
            "serviceId": self.servico.id,
            "hoursPerDay": "8.00",
            "daysCount": 1,
            "peopleCount": 1,
        }
        if item is not None:
            item_payload.update(
                {
                    "id": item.id,
                    "hoursPerDay": f"{item.horas_por_dia:.2f}",
                    "daysCount": item.quantidade_dias,
                    "peopleCount": item.quantidade_pessoas,
                    "unitRateUsed": f"{item.valor_unitario_usado:.2f}",
                    "dailyRateUsed": f"{item.valor_diaria_usada:.2f}",
                    "mealAmountUsed": f"{item.valor_alimentacao_usado:.2f}",
                    "transportAmountUsed": f"{item.valor_transporte_usado:.2f}",
                    "profitMarginUsed": f"{item.margem_lucro_usada:.2f}",
                    "taxRateUsed": f"{item.aliquota_imposto_usada:.2f}",
                    "baseHoursUsed": item.horas_base_diaria_usada,
                    "overtimePercentUsed": f"{item.percentual_hora_extra_usado:.2f}",
                    "usesSpecialRule": item.usa_regra_especial,
                }
            )

        return {
            "clientId": self.cliente.id,
            "configurationId": configuracao.id,
            "number": numero,
            "eventName": f"Evento {numero}",
            "eventDate": "2026-05-20",
            "local": "Local",
            "validUntil": "2026-05-15",
            "status": "rascunho",
            "notes": "",
            "items": [item_payload],
            "extraCosts": [],
        }

    def post_orcamento(self, configuracao, numero):
        return self.http.post(
            reverse("caixa:api_orcamentos"),
            data=json.dumps(self.orcamento_payload(configuracao, numero)),
            content_type="application/json",
        )

    def put_orcamento(self, orcamento, configuracao, *, item=None):
        return self.http.put(
            reverse("caixa:api_orcamento_detalhe", args=[orcamento.id]),
            data=json.dumps(
                self.orcamento_payload(
                    configuracao,
                    orcamento.numero,
                    item=item or orcamento.itens.get(),
                )
            ),
            content_type="application/json",
        )

    def assert_item_uses_configuration(self, item, configuracao):
        self.assertEqual(item.valor_alimentacao_usado, configuracao.valor_alimentacao)
        self.assertEqual(item.valor_transporte_usado, configuracao.valor_transporte)
        self.assertEqual(item.margem_lucro_usada, configuracao.margem_lucro)
        self.assertEqual(item.aliquota_imposto_usada, configuracao.aliquota_imposto)

    def test_api_permite_tres_ativas_e_ativar_uma_nao_desativa_as_outras(self):
        configuracao_a = self.criar_configuracao("Configuracao A")
        configuracao_b = self.criar_configuracao("Configuracao B")
        configuracao_c = self.criar_configuracao("Configuracao C", ativa=False)

        response = self.http.put(
            reverse(
                "caixa:api_configuracao_financeira_detalhe",
                args=[configuracao_c.id],
            ),
            data=json.dumps(
                self.configuracao_payload(configuracao_c, isActive=True)
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        configuracao_a.refresh_from_db()
        configuracao_b.refresh_from_db()
        configuracao_c.refresh_from_db()
        self.assertTrue(configuracao_a.ativa)
        self.assertTrue(configuracao_b.ativa)
        self.assertTrue(configuracao_c.ativa)
        self.assertEqual(ConfiguracaoFinanceira.objects.filter(ativa=True).count(), 3)

    def test_api_desativar_uma_configuracao_nao_altera_as_demais(self):
        configuracao_a = self.criar_configuracao("Configuracao A")
        configuracao_b = self.criar_configuracao("Configuracao B")
        configuracao_c = self.criar_configuracao("Configuracao C")

        response = self.http.put(
            reverse(
                "caixa:api_configuracao_financeira_detalhe",
                args=[configuracao_b.id],
            ),
            data=json.dumps(
                self.configuracao_payload(configuracao_b, isActive=False)
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        configuracao_a.refresh_from_db()
        configuracao_b.refresh_from_db()
        configuracao_c.refresh_from_db()
        self.assertTrue(configuracao_a.ativa)
        self.assertFalse(configuracao_b.ativa)
        self.assertTrue(configuracao_c.ativa)

    def test_api_cria_orcamento_com_cada_configuracao_ativa_e_calculo_exato(self):
        configuracoes = [
            self.criar_configuracao("Configuracao A"),
            self.criar_configuracao(
                "Configuracao B",
                alimentacao="30.00",
                transporte="15.00",
                margem="0.20",
                imposto="0.05",
            ),
        ]

        for index, configuracao in enumerate(configuracoes, start=1):
            with self.subTest(configuracao=configuracao.nome):
                response = self.post_orcamento(configuracao, f"ORC-CONFIG-{index}")
                self.assertEqual(response.status_code, 201, response.content)
                orcamento = Orcamento.objects.get(numero=f"ORC-CONFIG-{index}")
                item = orcamento.itens.get()
                self.assert_item_uses_configuration(item, configuracao)
                self.assertEqual(
                    item.gasto_alimentacao_total,
                    configuracao.valor_alimentacao,
                )
                self.assertEqual(
                    item.gasto_transporte_total,
                    configuracao.valor_transporte,
                )
                expected_with_margin = item.arredondar2(
                    item.custo_total * (Decimal("1.00") + configuracao.margem_lucro)
                )
                expected_tax = item.arredondar2(
                    expected_with_margin * configuracao.aliquota_imposto
                )
                self.assertEqual(item.valor_com_margem, expected_with_margin)
                self.assertEqual(item.valor_imposto, expected_tax)
                self.assertEqual(
                    item.preco_venda,
                    item.arredondar2(expected_with_margin + expected_tax),
                )
                self.assertEqual(orcamento.total_venda, item.preco_venda)

    def test_api_rejeita_criacao_com_configuracao_inativa(self):
        configuracao = self.criar_configuracao("Configuracao inativa", ativa=False)

        response = self.post_orcamento(configuracao, "ORC-CONFIG-INATIVA")

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("configurationId", response.json()["errors"])
        self.assertFalse(Orcamento.objects.filter(numero="ORC-CONFIG-INATIVA").exists())

    def test_troca_ativa_preserva_negociados_snapshots_e_recalcula(self):
        configuracao_a = self.criar_configuracao("Configuracao A")
        configuracao_b = self.criar_configuracao(
            "Configuracao B",
            alimentacao="30.00",
            transporte="15.00",
            margem="0.20",
            imposto="0.05",
        )
        criada = self.post_orcamento(configuracao_a, "ORC-CONFIG-TROCA")
        self.assertEqual(criada.status_code, 201, criada.content)
        orcamento = Orcamento.objects.get(numero="ORC-CONFIG-TROCA")
        item = orcamento.itens.get()
        item.valor_unitario_usado = Decimal("161.00")
        item.valor_diaria_usada = Decimal("175.00")
        item.horas_base_diaria_usada = 7
        item.percentual_hora_extra_usado = Decimal("2.50")
        item.usa_regra_especial = True
        item.quantidade_dias = 2
        item.quantidade_pessoas = 3
        item.save()

        response = self.put_orcamento(orcamento, configuracao_b, item=item)

        self.assertEqual(response.status_code, 200, response.content)
        orcamento.refresh_from_db()
        item = orcamento.itens.get()
        self.assertEqual(orcamento.configuracao_financeira_id, configuracao_b.id)
        self.assert_item_uses_configuration(item, configuracao_b)
        self.assertEqual(item.valor_unitario_usado, Decimal("161.00"))
        self.assertEqual(item.valor_diaria_usada, Decimal("175.00"))
        self.assertEqual(item.horas_base_diaria_usada, 7)
        self.assertEqual(item.percentual_hora_extra_usado, Decimal("2.50"))
        self.assertTrue(item.usa_regra_especial)
        self.assertEqual(item.quantidade_dias, 2)
        self.assertEqual(item.quantidade_pessoas, 3)
        self.assertEqual(orcamento.total_venda, item.preco_venda)

    def test_api_rejeita_troca_para_configuracao_inativa_sem_alteracao_parcial(self):
        configuracao_ativa = self.criar_configuracao("Configuracao ativa")
        configuracao_inativa = self.criar_configuracao(
            "Configuracao inativa",
            alimentacao="90.00",
            ativa=False,
        )
        self.assertEqual(
            self.post_orcamento(configuracao_ativa, "ORC-TROCA-INATIVA").status_code,
            201,
        )
        orcamento = Orcamento.objects.get(numero="ORC-TROCA-INATIVA")
        item = orcamento.itens.get()
        state_before = (
            orcamento.configuracao_financeira_id,
            orcamento.total_venda,
            item.id,
            item.valor_alimentacao_usado,
        )

        response = self.put_orcamento(orcamento, configuracao_inativa, item=item)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("configurationId", response.json()["errors"])
        orcamento.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(
            (
                orcamento.configuracao_financeira_id,
                orcamento.total_venda,
                item.id,
                item.valor_alimentacao_usado,
            ),
            state_before,
        )

    def test_configuracao_historica_inativada_continua_visivel_e_editavel(self):
        configuracao_a = self.criar_configuracao("Configuracao historica")
        configuracao_b = self.criar_configuracao("Configuracao ativa B")
        configuracao_c = self.criar_configuracao("Configuracao inativa C", ativa=False)
        self.assertEqual(
            self.post_orcamento(configuracao_a, "ORC-HISTORICO-INATIVO").status_code,
            201,
        )
        orcamento = Orcamento.objects.get(numero="ORC-HISTORICO-INATIVO")
        item = orcamento.itens.get()
        snapshots_before = (
            item.valor_alimentacao_usado,
            item.valor_transporte_usado,
            item.margem_lucro_usada,
            item.aliquota_imposto_usada,
            orcamento.total_venda,
        )
        configuracao_a.ativa = False
        configuracao_a.save(update_fields=["ativa"])

        list_response = self.http.get(reverse("caixa:api_orcamentos"))
        detail_response = self.http.get(
            reverse("caixa:api_orcamento_detalhe", args=[orcamento.id])
        )

        self.assertEqual(list_response.status_code, 200, list_response.content)
        self.assertEqual(detail_response.status_code, 200, detail_response.content)
        list_options = list_response.json()["data"]["filterOptions"]["configurations"]
        detail_options = detail_response.json()["data"]["filterOptions"]["configurations"]
        self.assertEqual({option["id"] for option in list_options}, {configuracao_b.id})
        self.assertEqual(
            {option["id"] for option in detail_options},
            {configuracao_a.id, configuracao_b.id},
        )
        historical_option = next(
            option for option in detail_options if option["id"] == configuracao_a.id
        )
        self.assertFalse(historical_option["isActive"])
        self.assertNotIn(configuracao_c.id, {option["id"] for option in detail_options})

        response = self.put_orcamento(orcamento, configuracao_a, item=item)

        self.assertEqual(response.status_code, 200, response.content)
        orcamento.refresh_from_db()
        item = orcamento.itens.get()
        self.assertEqual(
            (
                item.valor_alimentacao_usado,
                item.valor_transporte_usado,
                item.margem_lucro_usada,
                item.aliquota_imposto_usada,
                orcamento.total_venda,
            ),
            snapshots_before,
        )
        self.assertFalse(
            response.json()["data"]["budget"]["configurationOption"]["isActive"]
        )

        inactive_switch = self.put_orcamento(
            orcamento,
            configuracao_c,
            item=item,
        )
        self.assertEqual(inactive_switch.status_code, 400, inactive_switch.content)
        orcamento.refresh_from_db()
        self.assertEqual(orcamento.configuracao_financeira_id, configuracao_a.id)

        active_switch = self.put_orcamento(
            orcamento,
            configuracao_b,
            item=orcamento.itens.get(),
        )
        self.assertEqual(active_switch.status_code, 200, active_switch.content)
        orcamento.refresh_from_db()
        item = orcamento.itens.get()
        self.assertEqual(orcamento.configuracao_financeira_id, configuracao_b.id)
        self.assert_item_uses_configuration(item, configuracao_b)

    def test_editar_configuracao_nao_recalcula_orcamento_existente(self):
        configuracao = self.criar_configuracao("Configuracao historica")
        self.assertEqual(
            self.post_orcamento(configuracao, "ORC-SEM-RETROATIVO").status_code,
            201,
        )
        orcamento = Orcamento.objects.get(numero="ORC-SEM-RETROATIVO")
        item = orcamento.itens.get()
        state_before = (
            item.valor_alimentacao_usado,
            item.valor_transporte_usado,
            item.margem_lucro_usada,
            item.aliquota_imposto_usada,
            orcamento.total_venda,
        )

        response = self.http.put(
            reverse(
                "caixa:api_configuracao_financeira_detalhe",
                args=[configuracao.id],
            ),
            data=json.dumps(
                self.configuracao_payload(
                    configuracao,
                    mealAmount="99.00",
                    transportAmount="88.00",
                    profitMargin="0.77",
                    taxRate="0.66",
                )
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        orcamento.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(
            (
                item.valor_alimentacao_usado,
                item.valor_transporte_usado,
                item.margem_lucro_usada,
                item.aliquota_imposto_usada,
                orcamento.total_venda,
            ),
            state_before,
        )

    def test_ciclo_a_b_a_b_nao_acumula_margem_ou_imposto(self):
        configuracao_a = self.criar_configuracao("Configuracao A")
        configuracao_b = self.criar_configuracao(
            "Configuracao B",
            alimentacao="30.00",
            transporte="15.00",
            margem="0.20",
            imposto="0.05",
        )
        self.assertEqual(
            self.post_orcamento(configuracao_a, "ORC-CICLO-CONFIG").status_code,
            201,
        )
        orcamento = Orcamento.objects.get(numero="ORC-CICLO-CONFIG")

        for target in (configuracao_b, configuracao_a, configuracao_b):
            item = orcamento.itens.get()
            response = self.put_orcamento(orcamento, target, item=item)
            self.assertEqual(response.status_code, 200, response.content)
            orcamento.refresh_from_db()

        item = orcamento.itens.get()
        self.assert_item_uses_configuration(item, configuracao_b)
        expected_with_margin = item.arredondar2(
            item.custo_total * (Decimal("1.00") + configuracao_b.margem_lucro)
        )
        expected_tax = item.arredondar2(
            expected_with_margin * configuracao_b.aliquota_imposto
        )
        self.assertEqual(item.valor_com_margem, expected_with_margin)
        self.assertEqual(item.valor_imposto, expected_tax)
        self.assertEqual(
            item.preco_venda,
            item.arredondar2(expected_with_margin + expected_tax),
        )

    def _assert_closed_budget_rejects_configuration_change(self, status):
        configuracao_a = self.criar_configuracao(f"Configuracao A {status}")
        configuracao_b = self.criar_configuracao(f"Configuracao B {status}")
        self.assertEqual(
            self.post_orcamento(configuracao_a, f"ORC-FECHADO-{status}").status_code,
            201,
        )
        orcamento = Orcamento.objects.get(numero=f"ORC-FECHADO-{status}")
        item = orcamento.itens.get()
        state_before = (
            orcamento.configuracao_financeira_id,
            item.id,
            item.valor_alimentacao_usado,
            orcamento.total_venda,
        )
        Orcamento.objects.filter(pk=orcamento.pk).update(status=status)
        orcamento.refresh_from_db()

        response = self.put_orcamento(orcamento, configuracao_b, item=item)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("status", response.json()["errors"])
        orcamento.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(
            (
                orcamento.configuracao_financeira_id,
                item.id,
                item.valor_alimentacao_usado,
                orcamento.total_venda,
            ),
            state_before,
        )

    def test_orcamento_aprovado_permanece_congelado(self):
        self._assert_closed_budget_rejects_configuration_change("aprovado")

    def test_orcamento_recusado_permanece_congelado(self):
        self._assert_closed_budget_rejects_configuration_change("recusado")

    def test_orcamento_cancelado_permanece_congelado(self):
        self._assert_closed_budget_rejects_configuration_change("cancelado")


class ConfiguracaoFinanceiraConcorrenciaPostgreSQLTests(TenantTransactionTestCase):
    def setUp(self):
        super().setUp()
        if connection.vendor != "postgresql":
            self.skipTest("Concorrencia de configuracao financeira exige PostgreSQL.")

        self.usuario = get_user_model().objects.create_superuser(
            username="configuracao-concorrente",
            email="configuracao-concorrente@example.com",
            password="senha-segura",
        )
        self.cliente = Cliente.objects.create(
            nome_razao_social="Cliente Concorrencia Configuracao",
            tipo_pessoa="PJ",
            cpf_cnpj="98.765.432/0001-10",
        )
        self.servico = Servico.objects.create(
            nome="Servico Concorrencia Configuracao",
            codigo="servico-configuracao-concorrente",
            diaria_padrao=Decimal("100.00"),
            valor_unitario=Decimal("100.00"),
            horas_base_diaria=8,
            percentual_hora_extra=Decimal("2.00"),
        )
        self.configuracao = ConfiguracaoFinanceira.objects.create(
            nome="Configuracao concorrente",
            valor_alimentacao=Decimal("10.00"),
            valor_transporte=Decimal("5.00"),
            margem_lucro=Decimal("0.10"),
            aliquota_imposto=Decimal("0.01"),
            ativa=True,
            data_inicio_vigencia=date(2026, 1, 1),
        )

    def _orcamento_payload(self):
        return {
            "clientId": self.cliente.pk,
            "configurationId": self.configuracao.pk,
            "number": "ORC-CONFIG-CONCORRENTE",
            "eventName": "Evento concorrente",
            "eventDate": "2026-05-20",
            "local": "Local",
            "validUntil": "2026-05-15",
            "status": "rascunho",
            "notes": "",
            "items": [
                {
                    "serviceId": self.servico.pk,
                    "hoursPerDay": "8.00",
                    "daysCount": 1,
                    "peopleCount": 1,
                }
            ],
            "extraCosts": [],
        }

    def _backend_waits_for_lock(self, backend_pid, finished):
        deadline = monotonic() + 10
        while monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                    [backend_pid],
                )
                row = cursor.fetchone()
            if row and row[0] == "Lock":
                return True
            if finished.wait(0.02):
                return False
        return False

    def test_inativacao_aguarda_orcamento_persistir_apos_validacao_com_lock(self):
        configuration_locked = Event()
        release_budget = Event()
        deactivation_backend_ready = Event()
        deactivation_finished = Event()
        result_lock = Lock()
        results = {}
        errors = []
        original_configuration_loader = (
            views_orcamentos_api._configuration_for_budget
        )

        def locked_configuration_loader(*args, **kwargs):
            configuration = original_configuration_loader(*args, **kwargs)
            configuration_locked.set()
            if not release_budget.wait(timeout=15):
                raise TimeoutError("O teste nao liberou a gravacao do orcamento.")
            return configuration

        def save_budget():
            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                user = get_user_model().objects.get(pk=self.usuario.pk)
                with patch.object(
                    views_orcamentos_api,
                    "_configuration_for_budget",
                    side_effect=locked_configuration_loader,
                ):
                    budget = views_orcamentos_api._salvar_orcamento_from_payload(
                        self._orcamento_payload(),
                        user=user,
                    )
                with result_lock:
                    results["budget_id"] = budget.pk
            except Exception as error:
                with result_lock:
                    errors.append(error)
            finally:
                close_old_connections()

        def deactivate_configuration():
            if not configuration_locked.wait(timeout=15):
                with result_lock:
                    errors.append(
                        TimeoutError("O orcamento nao bloqueou a configuracao.")
                    )
                deactivation_finished.set()
                return

            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                configuration = ConfiguracaoFinanceira.objects.get(
                    pk=self.configuracao.pk
                )
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_pid = cursor.fetchone()[0]
                with result_lock:
                    results["deactivation_backend_pid"] = backend_pid
                deactivation_backend_ready.set()

                configuration.ativa = False
                response = _salvar_configuracao_response(
                    configuration,
                    success_message="Configuracao financeira atualizada com sucesso.",
                )
                with result_lock:
                    results["deactivation_status"] = response.status_code
            except Exception as error:
                with result_lock:
                    errors.append(error)
            finally:
                deactivation_finished.set()
                close_old_connections()

        budget_thread = Thread(target=save_budget)
        deactivation_thread = Thread(target=deactivate_configuration)
        budget_thread.start()
        try:
            self.assertTrue(configuration_locked.wait(timeout=15))
            deactivation_thread.start()
            self.assertTrue(deactivation_backend_ready.wait(timeout=15))
            self.assertTrue(
                self._backend_waits_for_lock(
                    results["deactivation_backend_pid"],
                    deactivation_finished,
                ),
                "A inativacao deveria aguardar o row lock da configuracao.",
            )
        finally:
            release_budget.set()
            budget_thread.join(timeout=30)
            if deactivation_thread.ident is not None:
                deactivation_thread.join(timeout=30)

        self.assertFalse(budget_thread.is_alive())
        self.assertFalse(deactivation_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results["deactivation_status"], 200)

        self.configuracao.refresh_from_db()
        budget = Orcamento.objects.get(pk=results["budget_id"])
        self.assertFalse(self.configuracao.ativa)
        self.assertEqual(
            budget.configuracao_financeira_id,
            self.configuracao.pk,
        )


class ConfiguracoesFinanceirasMultiTenantTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, _ = cls.create_tenant(
            schema_name="tenant_b",
            name="Tenant B",
            domain="tenant-b.localhost",
        )
        cls.tenants = {
            "tenant_a": cls.primary_tenant,
            "tenant_b": cls.secondary_tenant,
        }
        cls.password = "senha-configuracoes-isoladas"
        cls.create_user(
            "tenant_a",
            "configuracoes-tenant-a",
            cls.password,
            is_superuser=True,
        )
        cls.create_user(
            "tenant_b",
            "configuracoes-tenant-b",
            cls.password,
            is_superuser=True,
        )
        with cls.in_schema("tenant_a"):
            ConfiguracaoFinanceira.objects.create(
                nome="Configuracao exclusiva Tenant A",
                ativa=True,
                data_inicio_vigencia=date(2026, 1, 1),
            )
        with cls.in_schema("tenant_b"):
            ConfiguracaoFinanceira.objects.create(
                nome="Configuracao exclusiva Tenant B",
                ativa=True,
                data_inicio_vigencia=date(2026, 1, 1),
            )

    def authenticated_client(self, schema_name):
        client = self.client_for_tenant(self.tenants[schema_name])
        response = client.post(
            "/api/auth/login/",
            data=json.dumps(
                {
                    "username": f"configuracoes-{schema_name.replace('_', '-')}",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return client

    def test_api_lista_somente_configuracoes_ativas_do_tenant_atual(self):
        response_a = self.authenticated_client("tenant_a").get("/api/orcamentos/")
        response_b = self.authenticated_client("tenant_b").get("/api/orcamentos/")

        self.assertEqual(response_a.status_code, 200, response_a.content)
        self.assertEqual(response_b.status_code, 200, response_b.content)
        names_a = {
            item["name"]
            for item in response_a.json()["data"]["filterOptions"]["configurations"]
        }
        names_b = {
            item["name"]
            for item in response_b.json()["data"]["filterOptions"]["configurations"]
        }
        self.assertEqual(names_a, {"Configuracao exclusiva Tenant A"})
        self.assertEqual(names_b, {"Configuracao exclusiva Tenant B"})
