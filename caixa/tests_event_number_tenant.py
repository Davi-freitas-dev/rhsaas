from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from tenancy.test_helpers import MultiTenantTestCase

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
from .models_servico import EventoCustoServico
from .utils_eventos import gerar_numero_evento_orcamento


class EventNumberTenantTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, _ = cls.create_tenant(
            "event_number_b",
            "Event Number B",
            "event-number-b.localhost",
        )

    def setUp(self):
        super().setUp()
        self.primary_schema = self.primary_tenant.schema_name
        self.secondary_schema = self.secondary_tenant.schema_name

    def _criar_orcamento(self, schema_name, numero):
        with self.in_schema(schema_name):
            cliente = Cliente.objects.create(
                nome_razao_social=f"Cliente {schema_name}",
                cpf_cnpj="11.111.111/0001-11",
            )
            configuracao = ConfiguracaoFinanceira.objects.create(
                nome=f"Configuração {schema_name}",
                valor_alimentacao=Decimal("20.00"),
                valor_transporte=Decimal("10.00"),
                margem_lucro=Decimal("0.30"),
                aliquota_imposto=Decimal("0.05"),
                data_inicio_vigencia=date(2026, 1, 1),
            )
            servico = Servico.objects.create(
                nome=f"Serviço {schema_name}",
                codigo=f"servico-{schema_name.replace('_', '-')}",
                diaria_padrao=Decimal("100.00"),
            )
            orcamento = Orcamento.objects.create(
                cliente=cliente,
                configuracao_financeira=configuracao,
                numero=numero,
                nome_evento=f"Evento {schema_name}",
                data_evento=date(2026, 8, 20),
            )
            OrcamentoItem.objects.create(
                orcamento=orcamento,
                servico=servico,
                horas_por_dia=8,
                quantidade_dias=1,
                quantidade_pessoas=1,
            )
            return orcamento.pk

    def _assert_aprova_numero(self, tamanho, caractere):
        numero = caractere * tamanho
        orcamento_id = self._criar_orcamento(self.primary_schema, numero)

        with self.in_schema(self.primary_schema):
            orcamento = Orcamento.objects.get(pk=orcamento_id)
            evento = orcamento.aprovar_e_gerar_evento()
            orcamento.refresh_from_db()

            self.assertEqual(orcamento.status, "aprovado")
            self.assertEqual(evento.numero, gerar_numero_evento_orcamento(numero))
            self.assertEqual(len(evento.numero), tamanho + 4)
            self.assertEqual(Evento._meta.get_field("numero").max_length, 34)
            self.assertEqual(Evento.history.model._meta.get_field("numero").max_length, 34)

    def test_aprova_orcamento_com_numero_de_26_caracteres(self):
        self._assert_aprova_numero(26, "A")

    def test_aprova_orcamento_com_numero_de_27_caracteres(self):
        self._assert_aprova_numero(27, "B")

    def test_aprova_orcamento_com_numero_de_30_caracteres(self):
        self._assert_aprova_numero(30, "C")

    def test_reaprovacao_nao_duplica_evento_nem_movimentacoes(self):
        numero = "R" * 30
        orcamento_id = self._criar_orcamento(self.primary_schema, numero)

        with self.in_schema(self.primary_schema):
            orcamento = Orcamento.objects.get(pk=orcamento_id)
            primeiro_evento = orcamento.aprovar_e_gerar_evento()
            contagens = {
                "eventos": Evento.objects.filter(orcamento=orcamento).count(),
                "receitas": ReceitaOperacional.objects.filter(evento=primeiro_evento).count(),
                "despesas": DespesaOperacional.objects.filter(evento=primeiro_evento).count(),
                "custos": EventoCustoServico.objects.filter(evento=primeiro_evento).count(),
                "obrigacoes": ObrigacaoFinanceira.objects.filter(evento=primeiro_evento).count(),
            }

            segundo_evento = orcamento.aprovar_e_gerar_evento()

            self.assertEqual(segundo_evento.pk, primeiro_evento.pk)
            self.assertEqual(
                contagens,
                {
                    "eventos": Evento.objects.filter(orcamento=orcamento).count(),
                    "receitas": ReceitaOperacional.objects.filter(evento=primeiro_evento).count(),
                    "despesas": DespesaOperacional.objects.filter(evento=primeiro_evento).count(),
                    "custos": EventoCustoServico.objects.filter(evento=primeiro_evento).count(),
                    "obrigacoes": ObrigacaoFinanceira.objects.filter(evento=primeiro_evento).count(),
                },
            )

    def test_colisao_com_evento_manual_retorna_erro_de_dominio(self):
        numero = "M" * 30
        orcamento_id = self._criar_orcamento(self.primary_schema, numero)

        with self.in_schema(self.primary_schema):
            orcamento = Orcamento.objects.get(pk=orcamento_id)
            evento_manual = Evento.objects.create(
                cliente=orcamento.cliente,
                numero=gerar_numero_evento_orcamento(numero),
                nome_evento="Evento manual conflitante",
                data_inicio=orcamento.data_evento,
                data_fim=orcamento.data_evento,
            )

            with self.assertRaises(ValidationError) as contexto:
                orcamento.aprovar_e_gerar_evento()

            self.assertIn("numero", contexto.exception.message_dict)
            self.assertIn("não pertence a este orçamento", str(contexto.exception))
            self.assertTrue(Evento.objects.filter(pk=evento_manual.pk).exists())

    def test_colisao_reverte_status_e_nao_cria_registros_parciais(self):
        numero = "X" * 30
        orcamento_id = self._criar_orcamento(self.primary_schema, numero)

        with self.in_schema(self.primary_schema):
            orcamento = Orcamento.objects.get(pk=orcamento_id)
            evento_manual = Evento.objects.create(
                cliente=orcamento.cliente,
                numero=gerar_numero_evento_orcamento(numero),
                nome_evento="Evento manual para rollback",
                data_inicio=orcamento.data_evento,
                data_fim=orcamento.data_evento,
            )

            with self.assertRaises(ValidationError):
                orcamento.aprovar_e_gerar_evento()

            orcamento.refresh_from_db()
            self.assertEqual(orcamento.status, "rascunho")
            self.assertFalse(Evento.objects.filter(orcamento=orcamento).exists())
            self.assertEqual(ReceitaOperacional.objects.filter(evento=evento_manual).count(), 0)
            self.assertEqual(DespesaOperacional.objects.filter(evento=evento_manual).count(), 0)
            self.assertEqual(EventoCustoServico.objects.filter(evento=evento_manual).count(), 0)
            self.assertEqual(ObrigacaoFinanceira.objects.filter(evento=evento_manual).count(), 0)

    def test_mesmo_numero_pode_ser_aprovado_em_tenants_distintos(self):
        numero = "T" * 30
        orcamento_a_id = self._criar_orcamento(self.primary_schema, numero)
        orcamento_b_id = self._criar_orcamento(self.secondary_schema, numero)

        with self.in_schema(self.primary_schema):
            evento_a = Orcamento.objects.get(pk=orcamento_a_id).aprovar_e_gerar_evento()
            self.assertEqual(evento_a.numero, gerar_numero_evento_orcamento(numero))
            self.assertEqual(Evento.objects.count(), 1)

        with self.in_schema(self.secondary_schema):
            orcamento_b = Orcamento.objects.get(pk=orcamento_b_id)
            self.assertEqual(orcamento_b.status, "rascunho")
            self.assertEqual(Evento.objects.count(), 0)
            evento_b = orcamento_b.aprovar_e_gerar_evento()
            self.assertEqual(evento_b.numero, gerar_numero_evento_orcamento(numero))
            self.assertEqual(Evento.objects.count(), 1)

        with self.in_schema(self.primary_schema):
            self.assertEqual(Evento.objects.count(), 1)

    def test_numero_curto_existente_continua_valido(self):
        numero = "0463/26"
        orcamento_id = self._criar_orcamento(self.primary_schema, numero)

        with self.in_schema(self.primary_schema):
            evento = Orcamento.objects.get(pk=orcamento_id).aprovar_e_gerar_evento()
            self.assertEqual(evento.numero, "EVT-0463/26")
