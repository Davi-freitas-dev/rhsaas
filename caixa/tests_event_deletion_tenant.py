from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.db import transaction
from django.db.models.signals import post_delete
from django.test import RequestFactory

from tenancy.test_helpers import MultiTenantTestCase

from .admin import EventoAdmin
from .constants_financeiros import TIPO_CUSTO_DIARIAS
from .models import (
    Cliente,
    DespesaOperacional,
    Evento,
    ObrigacaoFinanceira,
    ReceitaOperacional,
    Servico,
)
from .models_custos_extras import EventoCustoExtra
from .models_pagamentos import (
    PagamentoEventoCustoExtra,
    PagamentoEventoCustoServico,
)
from .models_servico import EventoCustoServico
from .signal_utils import exclusao_originada_por_evento


class EventDeletionTenantTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, _ = cls.create_tenant(
            "event_delete_b",
            "Event Delete B",
            "event-delete-b.localhost",
        )

    def setUp(self):
        super().setUp()
        self.primary_schema = self.primary_tenant.schema_name
        self.secondary_schema = self.secondary_tenant.schema_name
        self.switch_to_tenant(self.primary_tenant)
        self._sequence = 0

    def _create_event(self, schema_name=None, suffix="primary"):
        schema_name = schema_name or self.primary_schema
        with self.in_schema(schema_name):
            self._sequence += 1
            cliente = Cliente.objects.create(
                nome_razao_social=f"Cliente delete {suffix} {self._sequence}",
                cpf_cnpj=f"77.777.777/0001-{self._sequence:02d}",
            )
            return Evento.objects.create(
                cliente=cliente,
                numero=f"EVT-DELETE-{suffix}-{self._sequence}",
                nome_evento=f"Evento delete {suffix} {self._sequence}",
                data_inicio=date(2026, 9, 1),
                data_fim=date(2026, 9, 1),
            )

    def _create_service_cost(self, evento, suffix="primary"):
        servico = Servico.objects.create(
            nome=f"Servico delete {suffix} {evento.pk}",
            codigo=f"servico-delete-{suffix}-{evento.pk}",
            diaria_padrao=Decimal("100.00"),
        )
        return EventoCustoServico.objects.create(
            evento=evento,
            servico=servico,
            valor_diarias=Decimal("100.00"),
            valor_alimentacao=Decimal("20.00"),
            valor_transporte=Decimal("10.00"),
        )

    def _create_extra_cost(self, evento):
        return EventoCustoExtra.objects.create(
            evento=evento,
            categoria="logistica",
            descricao="Frete delete",
            valor_previsto=Decimal("50.00"),
            data_vencimento=evento.data_inicio,
        )

    def _create_payments(self, service_cost, extra_cost):
        service_payment = PagamentoEventoCustoServico.objects.bulk_create(
            [
                PagamentoEventoCustoServico(
                    custo_servico=service_cost,
                    tipo=TIPO_CUSTO_DIARIAS,
                    descricao="Pagamento servico delete",
                    valor_pagamento=Decimal("10.00"),
                    data_pagamento=service_cost.evento.data_inicio,
                )
            ]
        )[0]
        extra_payment = PagamentoEventoCustoExtra.objects.bulk_create(
            [
                PagamentoEventoCustoExtra(
                    custo_extra=extra_cost,
                    descricao="Pagamento extra delete",
                    valor_pagamento=Decimal("10.00"),
                    data_pagamento=extra_cost.evento.data_inicio,
                )
            ]
        )[0]
        return service_payment, extra_payment

    def _assert_no_event_residue(self, evento_id):
        self.assertFalse(Evento.objects.filter(pk=evento_id).exists())
        self.assertFalse(ReceitaOperacional.objects.filter(evento_id=evento_id).exists())
        self.assertFalse(DespesaOperacional.objects.filter(evento_id=evento_id).exists())
        self.assertFalse(EventoCustoServico.objects.filter(evento_id=evento_id).exists())
        self.assertFalse(EventoCustoExtra.objects.filter(evento_id=evento_id).exists())
        self.assertFalse(
            PagamentoEventoCustoServico.objects.filter(
                custo_servico__evento_id=evento_id
            ).exists()
        )
        self.assertFalse(
            PagamentoEventoCustoExtra.objects.filter(
                custo_extra__evento_id=evento_id
            ).exists()
        )
        self.assertFalse(ObrigacaoFinanceira.objects.filter(evento_id=evento_id).exists())
        self.assertEqual(ReceitaOperacional.objects.count(), 0)
        self.assertEqual(DespesaOperacional.objects.count(), 0)
        self.assertEqual(EventoCustoServico.objects.count(), 0)
        self.assertEqual(EventoCustoExtra.objects.count(), 0)
        self.assertEqual(PagamentoEventoCustoServico.objects.count(), 0)
        self.assertEqual(PagamentoEventoCustoExtra.objects.count(), 0)
        self.assertEqual(ObrigacaoFinanceira.objects.count(), 0)

    def test_helper_reconhece_instancia_e_queryset_de_evento(self):
        evento = self._create_event()

        self.assertTrue(exclusao_originada_por_evento(evento))
        self.assertTrue(
            exclusao_originada_por_evento(Evento.objects.filter(pk=evento.pk))
        )
        self.assertFalse(exclusao_originada_por_evento(None))
        self.assertFalse(
            exclusao_originada_por_evento(Cliente.objects.filter(pk=evento.cliente_id))
        )

    def test_delete_instance_without_costs_removes_event(self):
        evento = self._create_event()
        evento_id = evento.pk

        evento.delete()

        self._assert_no_event_residue(evento_id)

    def test_delete_instance_with_service_cost_does_not_recreate_expenses(self):
        evento = self._create_event()
        evento_id = evento.pk
        self._create_service_cost(evento)
        self.assertTrue(DespesaOperacional.objects.filter(evento=evento).exists())

        evento.delete()

        self._assert_no_event_residue(evento_id)

    def test_delete_instance_with_extra_cost_does_not_recreate_expenses(self):
        evento = self._create_event()
        evento_id = evento.pk
        self._create_extra_cost(evento)
        self.assertTrue(DespesaOperacional.objects.filter(evento=evento).exists())

        evento.delete()

        self._assert_no_event_residue(evento_id)

    def test_delete_instance_with_both_costs_does_not_recreate_expenses(self):
        evento = self._create_event()
        evento_id = evento.pk
        self._create_service_cost(evento)
        self._create_extra_cost(evento)

        evento.delete()

        self._assert_no_event_residue(evento_id)

    def test_delete_instance_with_payments_removes_all_financial_records(self):
        evento = self._create_event()
        evento_id = evento.pk
        service_cost = self._create_service_cost(evento)
        extra_cost = self._create_extra_cost(evento)
        self._create_payments(service_cost, extra_cost)

        with (
            patch(
                "caixa.signals.sincronizar_pagamento_servico_e_recalcular_evento"
            ) as service_sync,
            patch(
                "caixa.signals_pagamentos.atualizar_total_pago_custo_extra_service"
            ) as extra_sync,
            patch(
                "caixa.signals.sincronizar_obrigacoes_custo_servico_canonicas"
            ) as service_obligation_sync,
            patch(
                "caixa.signals.sincronizar_obrigacao_custo_extra_canonica"
            ) as extra_obligation_sync,
        ):
            evento.delete()

        service_sync.assert_not_called()
        extra_sync.assert_not_called()
        service_obligation_sync.assert_not_called()
        extra_obligation_sync.assert_not_called()
        self._assert_no_event_residue(evento_id)

    def test_delete_event_with_movements_does_not_recalculate_during_cascade(self):
        evento = self._create_event(suffix="movements")
        evento_id = evento.pk
        ReceitaOperacional.objects.create(
            evento=evento,
            cliente=evento.cliente,
            descricao="Receita cascade delete",
            valor_previsto=Decimal("100.00"),
            data_vencimento=evento.data_inicio,
        )
        DespesaOperacional.objects.create(
            evento=evento,
            descricao="Despesa cascade delete",
            categoria="outros",
            valor_previsto=Decimal("20.00"),
            data_vencimento=evento.data_inicio,
        )

        with (
            patch("caixa.signals.recalcular_evento_realizado_apos_commit") as realized,
            patch(
                "caixa.signals.recalcular_evento_receita_prevista_apos_commit"
            ) as revenue,
            patch(
                "caixa.signals.recalcular_evento_custo_previsto_apos_commit"
            ) as expense,
        ):
            evento.delete()

        realized.assert_not_called()
        revenue.assert_not_called()
        expense.assert_not_called()
        self._assert_no_event_residue(evento_id)

    def test_delete_queryset_with_costs_does_not_recreate_expenses(self):
        evento = self._create_event()
        evento_id = evento.pk
        self._create_service_cost(evento)
        self._create_extra_cost(evento)

        Evento.objects.filter(pk=evento_id).delete()

        self._assert_no_event_residue(evento_id)

    def test_direct_cost_deletion_still_synchronizes(self):
        evento_servico = self._create_event(suffix="service")
        service_cost = self._create_service_cost(evento_servico, suffix="service")
        with patch("caixa.signals.sincronizar_evento_financeiro") as sync:
            service_cost.delete()
        sync.assert_called_once()

        evento_extra = self._create_event(suffix="extra")
        extra_cost = self._create_extra_cost(evento_extra)
        with patch("caixa.signals.sincronizar_evento_financeiro") as sync:
            extra_cost.delete()
        sync.assert_called_once()

    def test_direct_payment_deletion_still_synchronizes(self):
        evento = self._create_event()
        service_cost = self._create_service_cost(evento)
        extra_cost = self._create_extra_cost(evento)
        service_payment, extra_payment = self._create_payments(service_cost, extra_cost)

        with (
            patch(
                "caixa.signals.sincronizar_pagamento_servico_e_recalcular_evento"
            ) as service_sync,
            patch(
                "caixa.signals.sincronizar_obrigacoes_custo_servico_canonicas"
            ) as service_obligation_sync,
        ):
            service_payment.delete()
        service_sync.assert_called_once()
        service_obligation_sync.assert_called_once()

        with (
            patch(
                "caixa.signals_pagamentos.atualizar_total_pago_custo_extra_service"
            ) as extra_sync,
            patch(
                "caixa.signals.sincronizar_obrigacao_custo_extra_canonica"
            ) as extra_obligation_sync,
        ):
            extra_payment.delete()
        extra_sync.assert_called_once()
        extra_obligation_sync.assert_called_once()

    def test_direct_revenue_and_expense_deletion_still_recalculate_event(self):
        evento = self._create_event()
        receita = ReceitaOperacional.objects.create(
            evento=evento,
            cliente=evento.cliente,
            descricao="Receita manual delete",
            valor_previsto=Decimal("100.00"),
            data_vencimento=evento.data_inicio,
        )
        despesa = DespesaOperacional.objects.create(
            evento=evento,
            descricao="Despesa manual delete",
            categoria="outros",
            valor_previsto=Decimal("20.00"),
            data_vencimento=evento.data_inicio,
        )

        with (
            patch("caixa.signals.recalcular_evento_realizado_apos_commit") as realized,
            patch(
                "caixa.signals.recalcular_evento_receita_prevista_apos_commit"
            ) as revenue,
            patch(
                "caixa.signals.recalcular_evento_custo_previsto_apos_commit"
            ) as expense,
        ):
            receita.delete()
            despesa.delete()

        self.assertEqual(realized.call_count, 2)
        revenue.assert_called_once_with(evento.pk)
        expense.assert_called_once_with(evento.pk)

    def test_delete_is_isolated_between_tenants(self):
        primary_event = self._create_event(suffix="tenant-a")
        primary_id = primary_event.pk
        self._create_service_cost(primary_event, suffix="tenant-a")

        secondary_event = self._create_event(
            schema_name=self.secondary_schema,
            suffix="tenant-b",
        )
        secondary_id = secondary_event.pk
        with self.in_schema(self.secondary_schema):
            self._create_service_cost(secondary_event, suffix="tenant-b")

        with self.in_schema(self.primary_schema):
            Evento.objects.get(pk=primary_id).delete()
            self._assert_no_event_residue(primary_id)

        with self.in_schema(self.secondary_schema):
            self.assertTrue(Evento.objects.filter(pk=secondary_id).exists())
            self.assertTrue(
                EventoCustoServico.objects.filter(evento_id=secondary_id).exists()
            )
            self.assertTrue(DespesaOperacional.objects.filter(evento_id=secondary_id).exists())

    def test_admin_deletes_manual_event_with_costs(self):
        evento = self._create_event(suffix="admin")
        evento_id = evento.pk
        self._create_service_cost(evento, suffix="admin")
        self._create_extra_cost(evento)
        request = RequestFactory().post("/admin/caixa/evento/")

        EventoAdmin(Evento, AdminSite()).delete_model(request, evento)

        self._assert_no_event_residue(evento_id)

    def test_delete_rolls_back_when_another_receiver_fails(self):
        evento = self._create_event(suffix="rollback")
        evento_id = evento.pk
        self._create_service_cost(evento, suffix="rollback")
        self._create_extra_cost(evento)
        counts_before = {
            "events": Evento.objects.filter(pk=evento_id).count(),
            "expenses": DespesaOperacional.objects.filter(evento_id=evento_id).count(),
            "service_costs": EventoCustoServico.objects.filter(evento_id=evento_id).count(),
            "extra_costs": EventoCustoExtra.objects.filter(evento_id=evento_id).count(),
            "obligations": ObrigacaoFinanceira.objects.filter(evento_id=evento_id).count(),
        }

        def fail_after_event_delete(sender, instance, **kwargs):
            raise RuntimeError("falha injetada apos excluir evento")

        dispatch_uid = "test_event_delete_rollback_receiver"
        post_delete.connect(
            fail_after_event_delete,
            sender=Evento,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        try:
            with self.assertRaisesMessage(RuntimeError, "falha injetada"):
                with transaction.atomic():
                    Evento.objects.get(pk=evento_id).delete()
        finally:
            post_delete.disconnect(sender=Evento, dispatch_uid=dispatch_uid)

        counts_after = {
            "events": Evento.objects.filter(pk=evento_id).count(),
            "expenses": DespesaOperacional.objects.filter(evento_id=evento_id).count(),
            "service_costs": EventoCustoServico.objects.filter(evento_id=evento_id).count(),
            "extra_costs": EventoCustoExtra.objects.filter(evento_id=evento_id).count(),
            "obligations": ObrigacaoFinanceira.objects.filter(evento_id=evento_id).count(),
        }
        self.assertEqual(counts_after, counts_before)
