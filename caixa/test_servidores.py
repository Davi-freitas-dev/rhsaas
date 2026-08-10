from datetime import date
from decimal import Decimal
from io import StringIO
from threading import Barrier, Lock, Thread
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import (
    IntegrityError,
    close_old_connections,
    connection,
    transaction,
)
from django.db.models import Sum
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from tenancy.test_helpers import (
    MultiTenantTestCase,
    TenantAppTestCase,
    TenantTransactionTestCase,
)

from .models import (
    Cliente,
    DespesaOperacional,
    Evento,
    LancamentoFinanceiro,
    ObrigacaoFinanceira,
    Servico,
)
from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PAGO,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
)
from .models_custo_fixo import (
    AuditoriaCustoRecorrente,
    CustoFixo,
    PlanoCustoRecorrente,
)
from .models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from .models_servidores import (
    HistoricoJornadaMensalServidor,
    HistoricoSalarialServidor,
    ParticipacaoServidorEvento,
    Servidor,
    ServidorEventoDiaTrabalhado,
    ServidorServico,
)
from .models_servico import EventoCustoServico
from .selectors_custos_servidores import custos_por_servidor
from .selectors_servidores import filtrar_servidores
from .serializers_dashboard import _distribuicoes_servidores_por_evento
from .serializers_participacoes_servidores import serializar_participacao
from .serializers_servidores import serializar_servidor
from .services_participacoes_servidores import (
    atualizar_evento_com_periodo,
    atualizar_participacao,
    criar_participacao,
    excluir_participacao,
    recalcular_evento,
    restaurar_calculo_participacao,
)
from .services_servidores import atualizar_servidor, criar_servidor, excluir_servidor
from .services_ativacao_mensalistas import ativar_mensalista_existente


class ServidoresFixtureMixin:
    def setUp(self):
        super().setUp()
        self.usuario = get_user_model().objects.create_superuser(
            username="admin-servidores",
            email="admin@example.com",
            password="senha-segura",
        )
        self.cliente = Cliente.objects.create(
            nome_razao_social="Cliente Teste",
            cpf_cnpj="12345678000190",
        )
        self.evento = Evento.objects.create(
            cliente=self.cliente,
            numero="EVT-SRV-001",
            nome_evento="Evento Servidores",
            data_inicio=date(2026, 7, 20),
            data_fim=date(2026, 7, 20),
            status="planejado",
        )
        self.servico = Servico.objects.create(
            nome="Segurança",
            codigo="seguranca",
            diaria_padrao=Decimal("100.00"),
            valor_unitario=Decimal("100.00"),
            horas_base_diaria=8,
        )
        self.outro_servico = Servico.objects.create(
            nome="Recepção",
            codigo="recepcao",
            diaria_padrao=Decimal("80.00"),
            valor_unitario=Decimal("80.00"),
            horas_base_diaria=8,
        )
        self.custo = EventoCustoServico.objects.create(
            evento=self.evento,
            servico=self.servico,
            valor_diarias=Decimal("100.00"),
        )
        self.outro_custo = EventoCustoServico.objects.create(
            evento=self.evento,
            servico=self.outro_servico,
            valor_diarias=Decimal("90.00"),
        )

    def dados_servidor(self, indice, **extras):
        dados = {
            "nome": f"Servidor {indice}",
            "tipo_documento": "CPF",
            "documento": f"000000000{indice:02d}",
            "tipo_vinculo": Servidor.VINCULO_DIARISTA,
            "salario_mensal": None,
        }
        dados.update(extras)
        return dados

    def criar_diarista(self, indice, servico=None):
        return criar_servidor(
            dados=self.dados_servidor(indice),
            servicos_ids=[(servico or self.servico).id],
            usuario=self.usuario,
        )

    def participar(
        self,
        servidor,
        *,
        servico=None,
        dias=1,
        horas=Decimal("0.00"),
        datas_trabalhadas=None,
    ):
        return criar_participacao(
            evento=self.evento,
            servidor=servidor,
            servico=servico or self.servico,
            quantidade_dias=dias,
            quantidade_horas=horas,
            datas_trabalhadas=datas_trabalhadas,
            usuario=self.usuario,
        )


class ConcorrenciaSalarialPostgreSQLTests(
    ServidoresFixtureMixin,
    TenantTransactionTestCase,
):
    def setUp(self):
        super().setUp()
        if connection.vendor != "postgresql":
            self.skipTest("Concorrência salarial exige PostgreSQL.")

    def executar_em_paralelo(self, operacoes):
        barreira = Barrier(len(operacoes))
        lock = Lock()
        resultados = []
        erros = []

        def executar(operacao):
            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                barreira.wait(timeout=10)
                resultado = operacao()
                with lock:
                    resultados.append(resultado)
            except Exception as error:
                with lock:
                    erros.append(error)
            finally:
                close_old_connections()

        threads = [Thread(target=executar, args=(operacao,)) for operacao in operacoes]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(erros, [])
        return resultados

    def criar_mensalista(self, *, autorizado=True):
        return criar_servidor(
            dados=self.dados_servidor(
                91,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("1000.00"),
                carga_horaria_mensal=Decimal("160.00"),
                data_inicio_contrato=date(2026, 7, 1),
                dia_pagamento_salario=5,
                data_autorizacao_custo_salarial=(
                    date(2026, 7, 1) if autorizado else None
                ),
            ),
            servicos_ids=[self.servico.pk],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
            data_vigencia_jornada=date(2026, 7, 1),
        )

    def test_alteracoes_salariais_simultaneas_preservam_uma_vigencia_aberta(self):
        servidor = self.criar_mensalista()

        def alterar(valor):
            def operacao():
                servidor_thread = Servidor.objects.get(pk=servidor.pk)
                usuario_thread = get_user_model().objects.get(pk=self.usuario.pk)
                atualizado = atualizar_servidor(
                    servidor_thread,
                    dados={"salario_mensal": valor},
                    servicos_ids=[self.servico.pk],
                    usuario=usuario_thread,
                    data_vigencia_salario=date(2026, 8, 1),
                )
                return atualizado.salario_mensal

            return operacao

        resultados = self.executar_em_paralelo(
            [alterar(Decimal("1500.00")), alterar(Decimal("1750.00"))]
        )

        servidor.refresh_from_db()
        vigencias = list(
            HistoricoSalarialServidor.objects.filter(
                servidor=servidor
            ).order_by("data_inicio", "id")
        )
        self.assertEqual(len(vigencias), 2)
        self.assertEqual(vigencias[0].data_fim, date(2026, 7, 31))
        self.assertEqual(vigencias[1].data_inicio, date(2026, 8, 1))
        self.assertIsNone(vigencias[1].data_fim)
        self.assertEqual(
            HistoricoSalarialServidor.objects.filter(
                servidor=servidor,
                data_fim__isnull=True,
            ).count(),
            1,
        )
        self.assertEqual(servidor.salario_mensal, vigencias[1].valor)
        self.assertIn(servidor.salario_mensal, resultados)

    def test_ativacao_simultanea_cria_um_plano_e_uma_ocorrencia(self):
        servidor = self.criar_mensalista(autorizado=False)

        def ativar():
            servidor_thread = Servidor.objects.get(pk=servidor.pk)
            usuario_thread = get_user_model().objects.get(pk=self.usuario.pk)
            return ativar_mensalista_existente(
                servidor_thread,
                data_corte=date(2026, 7, 1),
                correlation_id=uuid.uuid4(),
                usuario=usuario_thread,
            )

        resultados = self.executar_em_paralelo([ativar, ativar])

        self.assertEqual(
            sorted(resultado["status"] for resultado in resultados),
            ["activated", "alreadyConfigured"],
        )
        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).count(),
            1,
        )
        self.assertEqual(
            CustoFixo.objects.filter(
                plano_recorrente__servidor=servidor,
                competencia=date(2026, 7, 1),
            ).count(),
            1,
        )

    def test_alteracoes_de_jornada_simultaneas_preservam_uma_vigencia_aberta(self):
        servidor = self.criar_mensalista(autorizado=False)

        def alterar(horas):
            def operacao():
                servidor_thread = Servidor.objects.get(pk=servidor.pk)
                usuario_thread = get_user_model().objects.get(pk=self.usuario.pk)
                atualizado = atualizar_servidor(
                    servidor_thread,
                    dados={"carga_horaria_mensal": horas},
                    servicos_ids=[self.servico.pk],
                    usuario=usuario_thread,
                    data_vigencia_jornada=date(2026, 8, 1),
                )
                return atualizado.carga_horaria_mensal

            return operacao

        resultados = self.executar_em_paralelo(
            [alterar(Decimal("176.00")), alterar(Decimal("180.00"))]
        )

        servidor.refresh_from_db()
        vigencias = list(
            HistoricoJornadaMensalServidor.objects.filter(
                servidor=servidor
            ).order_by("data_inicio", "id")
        )
        self.assertEqual(len(vigencias), 2)
        self.assertEqual(vigencias[0].data_fim, date(2026, 7, 31))
        self.assertEqual(vigencias[1].data_inicio, date(2026, 8, 1))
        self.assertIsNone(vigencias[1].data_fim)
        self.assertEqual(
            HistoricoJornadaMensalServidor.objects.filter(
                servidor=servidor,
                data_fim__isnull=True,
            ).count(),
            1,
        )
        self.assertEqual(servidor.carga_horaria_mensal, vigencias[1].horas_mensais)
        self.assertIn(servidor.carga_horaria_mensal, resultados)


class ServidoresDominioTests(ServidoresFixtureMixin, TenantAppTestCase):

    def test_admin_bulk_delete_de_custo_eh_atomico_quando_um_grupo_esta_protegido(self):
        custo_livre = EventoCustoServico.objects.get(
            evento=self.evento,
            servico=self.servico,
        )
        custo_protegido = EventoCustoServico.objects.get(
            evento=self.evento,
            servico=self.outro_servico,
        )
        self.participar(
            self.criar_diarista(9, servico=self.outro_servico),
            servico=self.outro_servico,
        )
        request = RequestFactory().post("/admin/caixa/eventocustoservico/")
        request.user = self.usuario
        custo_admin = site._registry[EventoCustoServico]

        with self.assertRaises(ValidationError):
            custo_admin.delete_queryset(
                request,
                EventoCustoServico.objects.filter(
                    pk__in=[custo_livre.pk, custo_protegido.pk]
                ),
            )

        self.assertTrue(EventoCustoServico.objects.filter(pk=custo_livre.pk).exists())
        self.assertTrue(EventoCustoServico.objects.filter(pk=custo_protegido.pk).exists())

    def test_cria_servidor_com_multiplos_servicos_e_autoria(self):
        servidor = criar_servidor(
            dados=self.dados_servidor(1),
            servicos_ids=[self.servico.id, self.outro_servico.id],
            usuario=self.usuario,
        )
        self.assertEqual(servidor.documento, "00000000001")
        self.assertEqual(servidor.criado_por, self.usuario)
        self.assertEqual(servidor.vinculos_servicos.count(), 2)
        self.assertEqual(ServidorServico.history.filter(servidor_id=servidor.id).count(), 2)

    def test_documento_duplicado_e_servico_inativo_sao_bloqueados(self):
        self.criar_diarista(2)
        with self.assertRaises(ValidationError):
            criar_servidor(
                dados=self.dados_servidor(2, nome="Duplicado"),
                servicos_ids=[self.servico.id],
                usuario=self.usuario,
            )
        self.outro_servico.ativo = False
        self.outro_servico.save(update_fields=["ativo"])
        with self.assertRaises(ValidationError):
            criar_servidor(
                dados=self.dados_servidor(3),
                servicos_ids=[self.outro_servico.id],
                usuario=self.usuario,
            )

    def test_mensalista_cria_e_preserva_historico_salarial(self):
        servidor = criar_servidor(
            dados=self.dados_servidor(
                4,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("3000.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 1, 1),
        )
        atualizar_servidor(
            servidor,
            dados=self.dados_servidor(
                4,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("3500.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        vigencias = list(servidor.historicos_salariais.order_by("data_inicio"))
        self.assertEqual(len(vigencias), 2)
        self.assertEqual(vigencias[0].data_fim, date(2026, 6, 30))
        self.assertEqual(vigencias[1].valor, Decimal("3500.00"))

    def test_rateio_de_cem_reais_em_tres_fecha_centavos(self):
        participacoes = [self.participar(self.criar_diarista(indice)) for indice in (10, 11, 12)]
        valores = [
            ParticipacaoServidorEvento.objects.get(pk=item.pk).valor_final
            for item in participacoes
        ]
        self.assertEqual(sum(valores), Decimal("100.00"))
        self.assertEqual(valores, [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])

    def test_quatro_servidores_dividem_custo_em_partes_iguais(self):
        participacoes = [self.participar(self.criar_diarista(indice)) for indice in (40, 41, 42, 43)]
        valores = list(
            ParticipacaoServidorEvento.objects.filter(
                id__in=[item.id for item in participacoes]
            ).order_by("id").values_list("valor_final", flat=True)
        )
        self.assertEqual(valores, [Decimal("25.00")] * 4)

    def test_rateio_proporcional_por_dias_e_horas_equivalentes(self):
        primeira = self.participar(self.criar_diarista(13), dias=2)
        segunda = self.participar(self.criar_diarista(14), dias=1)
        primeira.refresh_from_db()
        segunda.refresh_from_db()
        self.assertEqual(primeira.valor_final, Decimal("66.67"))
        self.assertEqual(segunda.valor_final, Decimal("33.33"))

    def test_rateio_por_horas_diferentes(self):
        primeira = self.participar(self.criar_diarista(44), dias=0, horas=Decimal("2.00"))
        segunda = self.participar(self.criar_diarista(45), dias=0, horas=Decimal("6.00"))
        primeira.refresh_from_db()
        segunda.refresh_from_db()
        self.assertEqual(primeira.valor_final, Decimal("25.00"))
        self.assertEqual(segunda.valor_final, Decimal("75.00"))

    def test_rateios_sao_separados_por_servico(self):
        seguranca = self.participar(self.criar_diarista(15))
        recepcao = self.participar(
            self.criar_diarista(16, self.outro_servico),
            servico=self.outro_servico,
        )
        seguranca.refresh_from_db()
        recepcao.refresh_from_db()
        self.assertEqual(seguranca.valor_final, Decimal("100.00"))
        self.assertEqual(recepcao.valor_final, Decimal("90.00"))

    def test_alterar_custo_estruturado_recalcula_o_grupo_e_preserva_manual(self):
        manual = self.participar(self.criar_diarista(151))
        automatico = self.participar(self.criar_diarista(152))
        atualizar_participacao(
            manual,
            servico=self.servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("0.00"),
            valor_final=Decimal("40.00"),
            motivo_edicao="Valor acordado",
            usuario=self.usuario,
        )

        self.custo.valor_diarias = Decimal("150.00")
        self.custo.atualizado_por = self.usuario
        self.custo.save(update_fields=["valor_diarias", "atualizado_por"])

        manual.refresh_from_db()
        automatico.refresh_from_db()
        self.assertEqual(manual.valor_final, Decimal("40.00"))
        self.assertEqual(automatico.valor_calculado, Decimal("75.00"))
        self.assertEqual(automatico.valor_final, Decimal("110.00"))
        self.assertEqual(manual.valor_final + automatico.valor_final, Decimal("150.00"))

    def test_fonte_de_custo_com_participacao_nao_pode_ser_removida_ou_trocada(self):
        self.participar(self.criar_diarista(153))
        with self.assertRaises(ValidationError):
            self.custo.delete()

        self.custo.servico = self.outro_servico
        with self.assertRaises(ValidationError):
            self.custo.save(update_fields=["servico"])

        self.custo.refresh_from_db()
        self.assertEqual(self.custo.servico_id, self.servico.id)

    def test_snapshots_do_servidor_sao_immutaveis_e_servico_muda_somente_explicito(self):
        servidor = criar_servidor(
            dados=self.dados_servidor(154),
            servicos_ids=[self.servico.id, self.outro_servico.id],
            usuario=self.usuario,
        )
        participacao = self.participar(servidor)
        nome_snapshot = participacao.servidor_nome_snapshot
        identificador_snapshot = participacao.servidor_identificador_snapshot

        atualizar_servidor(
            servidor,
            dados=self.dados_servidor(154, nome="Servidor renomeado"),
            servicos_ids=[self.servico.id, self.outro_servico.id],
            usuario=self.usuario,
        )
        participacao = atualizar_participacao(
            participacao,
            servico=self.outro_servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("0.00"),
            usuario=self.usuario,
        )
        recalcular_evento(self.evento, usuario=self.usuario)
        participacao.refresh_from_db()

        self.assertEqual(participacao.servidor_nome_snapshot, nome_snapshot)
        self.assertEqual(
            participacao.servidor_identificador_snapshot,
            identificador_snapshot,
        )
        self.assertEqual(participacao.servico_nome_snapshot, self.outro_servico.nome)
        self.assertEqual(participacao.servico_codigo_snapshot, self.outro_servico.codigo)

    def test_valor_manual_e_preservado_e_restante_redistribuido(self):
        primeira = self.participar(self.criar_diarista(17))
        segunda = self.participar(self.criar_diarista(18))
        terceira = self.participar(self.criar_diarista(19))
        primeira = atualizar_participacao(
            primeira,
            servico=self.servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("0.00"),
            valor_final=Decimal("40.00"),
            motivo_edicao="Ajuste acordado",
            usuario=self.usuario,
        )
        segunda.refresh_from_db()
        terceira.refresh_from_db()
        self.assertEqual(primeira.valor_final, Decimal("40.00"))
        self.assertEqual(primeira.valor_calculado, Decimal("33.34"))
        self.assertEqual(seconda := segunda.valor_final, Decimal("30.00"))
        self.assertEqual(terceira.valor_final, Decimal("30.00"))
        self.assertEqual(seconda + terceira.valor_final + primeira.valor_final, Decimal("100.00"))

    def test_valor_manual_acima_do_total_faz_rollback(self):
        participacao = self.participar(self.criar_diarista(20))
        with self.assertRaises(ValidationError):
            atualizar_participacao(
                participacao,
                servico=self.servico,
                quantidade_dias=1,
                quantidade_horas=Decimal("0.00"),
                valor_final=Decimal("101.00"),
                motivo_edicao="Inválido",
                usuario=self.usuario,
            )
        participacao.refresh_from_db()
        self.assertFalse(participacao.valor_editado_manualmente)
        self.assertEqual(participacao.valor_final, Decimal("100.00"))

    def test_restaurar_calculo_automatico(self):
        primeira = self.participar(self.criar_diarista(21))
        self.participar(self.criar_diarista(22))
        primeira = atualizar_participacao(
            primeira,
            servico=self.servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("0.00"),
            valor_final=Decimal("60.00"),
            motivo_edicao="Acordo",
            usuario=self.usuario,
        )
        primeira = restaurar_calculo_participacao(primeira, usuario=self.usuario)
        self.assertFalse(primeira.valor_editado_manualmente)
        self.assertEqual(primeira.valor_final, Decimal("50.00"))

    def test_remover_participacao_redistribui_o_total(self):
        primeira = self.participar(self.criar_diarista(46))
        segunda = self.participar(self.criar_diarista(47))
        excluir_participacao(primeira, usuario=self.usuario)
        segunda.refresh_from_db()
        self.assertFalse(ParticipacaoServidorEvento.objects.filter(pk=primeira.pk).exists())
        self.assertEqual(segunda.valor_final, Decimal("100.00"))

    def test_mudar_servico_recalcula_os_dois_grupos(self):
        servidor = criar_servidor(
            dados=self.dados_servidor(48),
            servicos_ids=[self.servico.id, self.outro_servico.id],
            usuario=self.usuario,
        )
        participacao = self.participar(servidor)
        participacao = atualizar_participacao(
            participacao,
            servico=self.outro_servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("0.00"),
            usuario=self.usuario,
        )
        self.assertEqual(participacao.servico_id, self.outro_servico.id)
        self.assertEqual(participacao.valor_final, Decimal("90.00"))

    def test_mensalista_participa_sem_gerar_diaria(self):
        servidor = criar_servidor(
            dados=self.dados_servidor(
                23,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2500.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        participacao = self.participar(servidor)
        self.assertEqual(participacao.valor_calculado, Decimal("0.00"))
        self.assertEqual(participacao.valor_final, Decimal("0.00"))
        self.assertEqual(self.custo.valor_diarias, Decimal("100.00"))

    def test_exclusao_preserva_participacao_snapshots_valores_e_historico(self):
        servidor = self.criar_diarista(24)
        participacao = self.participar(servidor)
        quantidade = excluir_servidor(servidor, usuario=self.usuario)
        self.assertEqual(quantidade, 1)
        participacao.refresh_from_db()
        self.assertIsNone(participacao.servidor_id)
        self.assertEqual(participacao.servidor_nome_snapshot, "Servidor 24")
        self.assertEqual(participacao.valor_final, Decimal("100.00"))
        self.assertEqual(participacao.servidor_excluido_por, self.usuario)
        self.assertTrue(Servidor.history.filter(id=servidor.id, history_type="-").exists())
        self.assertTrue(
            ServidorServico.history.filter(
                servidor_id=servidor.id,
                history_type="-",
                history_user=self.usuario,
            ).exists()
        )

    def test_exclusao_sem_participacao_preserva_auditoria(self):
        servidor = self.criar_diarista(49)
        self.assertEqual(excluir_servidor(servidor, usuario=self.usuario), 0)
        self.assertFalse(Servidor.objects.filter(pk=servidor.pk).exists())
        historico = Servidor.history.filter(id=servidor.id, history_type="-").get()
        self.assertEqual(historico.history_user, self.usuario)

    def test_servidor_inativo_nao_pode_entrar_em_evento(self):
        servidor = self.criar_diarista(50)
        servidor.ativo = False
        servidor.save(update_fields=["ativo"])
        with self.assertRaises(ValidationError):
            self.participar(servidor)

    def test_lista_servidores_evita_n_mais_um(self):
        for indice in range(51, 59):
            self.criar_diarista(indice)
        with CaptureQueriesContext(connection) as consultas:
            itens = [
                serializar_servidor(item, pode_ver_salario=True, pode_ver_sensiveis=True)
                for item in filtrar_servidores()
            ]
        self.assertEqual(len(itens), 8)
        self.assertLessEqual(len(consultas), 2)

    def test_relatorio_aplica_filtros_sem_somar_salario_indevido(self):
        seguranca = self.criar_diarista(59)
        recepcao = self.criar_diarista(60, self.outro_servico)
        self.participar(seguranca)
        self.participar(recepcao, servico=self.outro_servico)
        resultado = custos_por_servidor(
            data_inicial=date(2026, 7, 1),
            data_final=date(2026, 7, 31),
            usuario=self.usuario,
            servico_id=str(self.outro_servico.id),
            tipo_vinculo=Servidor.VINCULO_DIARISTA,
            existencia="existing",
        )
        self.assertEqual(resultado["summary"]["serverCount"], 1)
        self.assertEqual(resultado["summary"]["totalPeriod"], "90.00")
        self.assertEqual(resultado["servers"][0]["serverId"], recepcao.id)

    def test_evento_concluido_bloqueia_mutacoes_e_recalculo(self):
        servidor = self.criar_diarista(25)
        self.evento.status = "concluido"
        self.evento.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.participar(servidor)
        with self.assertRaises(ValidationError):
            recalcular_evento(self.evento, usuario=self.usuario)

    def test_relatorio_separa_salario_e_participacao(self):
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                26,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2000.00"),
                data_inicio_contrato=date(2026, 7, 1),
                dia_pagamento_salario=5,
                data_autorizacao_custo_salarial=date(2026, 7, 1),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        self.participar(mensalista)
        resultado = custos_por_servidor(
            data_inicial=date(2026, 7, 1),
            data_final=date(2026, 7, 31),
            usuario=self.usuario,
        )
        grupo = next(item for item in resultado["servers"] if item["serverId"] == mensalista.id)
        self.assertEqual(grupo["participationCostTotal"], "0.00")
        self.assertEqual(grupo["salaryCostTotal"], "2000.00")
        self.assertFalse(resultado["summary"]["managerialAppropriationCalculated"])

    def test_servico_inativo_bloqueia_nova_participacao_mesmo_com_vinculo_ativo(self):
        servidor = self.criar_diarista(70)
        self.servico.ativo = False
        self.servico.save(update_fields=["ativo"])

        with self.assertRaises(ValidationError):
            self.participar(servidor)

        self.assertFalse(
            ParticipacaoServidorEvento.objects.filter(servidor=servidor).exists()
        )

    def test_mensalista_sem_custo_estruturado_faz_rollback(self):
        self.custo.delete()
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                71,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2500.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )

        with self.assertRaises(ValidationError):
            self.participar(mensalista)

        self.assertFalse(
            ParticipacaoServidorEvento.objects.filter(servidor=mensalista).exists()
        )

    def test_mensalista_nao_aceita_valor_final_manual(self):
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                72,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2600.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        participacao = self.participar(mensalista)

        with self.assertRaises(ValidationError):
            atualizar_participacao(
                participacao,
                servico=self.servico,
                quantidade_dias=1,
                quantidade_horas=Decimal("0.00"),
                valor_final=Decimal("10.00"),
                motivo_edicao="Valor indevido",
                usuario=self.usuario,
            )

        participacao.refresh_from_db()
        self.assertFalse(participacao.valor_editado_manualmente)
        self.assertEqual(participacao.valor_final, Decimal("0.00"))

    def test_horas_negativas_sao_bloqueadas_no_modelo_servico_e_banco(self):
        servidor = self.criar_diarista(73)
        with self.assertRaises(ValidationError):
            self.participar(servidor, dias=1, horas=Decimal("-1.00"))

        participacao = self.participar(servidor)
        participacao.quantidade_horas = Decimal("-1.00")
        with self.assertRaises(ValidationError):
            participacao.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ParticipacaoServidorEvento.objects.filter(pk=participacao.pk).update(
                    quantidade_horas=Decimal("-1.00")
                )

    def test_falha_no_rateio_reverte_criacao_da_participacao(self):
        servidor = self.criar_diarista(74)
        with patch(
            "caixa.services_participacoes_servidores._recalcular_grupo_bloqueado",
            side_effect=ValidationError({"distribution": "Falha forçada"}),
        ):
            with self.assertRaises(ValidationError):
                self.participar(servidor)

        self.assertFalse(
            ParticipacaoServidorEvento.objects.filter(servidor=servidor).exists()
        )

    def test_distribuicao_sem_participantes_expoe_diferenca_integral(self):
        distribuicao = _distribuicoes_servidores_por_evento([self.evento.id])[
            self.evento.id
        ]
        grupo = next(
            item
            for item in distribuicao["services"]
            if item["serviceId"] == self.servico.id
        )

        self.assertEqual(grupo["participants"], [])
        self.assertEqual(grupo["distributedAmount"], 0.0)
        self.assertEqual(grupo["differenceAmount"], 100.0)
        self.assertEqual(distribuicao["distributed"], Decimal("0.00"))
        self.assertEqual(distribuicao["difference"], Decimal("190.00"))

    def test_exclusao_serializa_nome_snapshot_sem_sufixo_duplicado(self):
        servidor = self.criar_diarista(75)
        participacao = self.participar(servidor)
        excluir_servidor(servidor, usuario=self.usuario)
        participacao.refresh_from_db()

        payload = serializar_participacao(participacao)
        self.assertEqual(payload["serverName"], "Servidor 75")
        self.assertTrue(payload["serverDeleted"])

    def test_operacoes_de_servidores_nao_criam_movimentos_financeiros(self):
        modelos = (
            DespesaOperacional,
            PagamentoEventoCustoServico,
            PagamentoEventoCustoExtra,
            ObrigacaoFinanceira,
            LancamentoFinanceiro,
            CustoFixo,
        )
        estado_inicial = tuple(modelo.objects.count() for modelo in modelos)
        custo_inicial = EventoCustoServico.objects.aggregate(total=Sum("valor_diarias"))[
            "total"
        ]

        servidor = self.criar_diarista(76)
        self.participar(servidor)
        excluir_servidor(servidor, usuario=self.usuario)

        self.assertEqual(
            tuple(modelo.objects.count() for modelo in modelos),
            estado_inicial,
        )
        self.assertEqual(
            EventoCustoServico.objects.aggregate(total=Sum("valor_diarias"))["total"],
            custo_inicial,
        )


class CustosPorServidorEvolucaoTests(ServidoresFixtureMixin, TenantAppTestCase):
    def criar_mensalista_configurado(self, indice, salario="2000.00"):
        return criar_servidor(
            dados=self.dados_servidor(
                indice,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal(salario),
                data_inicio_contrato=date(2026, 7, 1),
                dia_pagamento_salario=5,
                data_autorizacao_custo_salarial=date(2026, 7, 1),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )

    def relatorio(self, **filtros):
        return custos_por_servidor(
            data_inicial=date(2026, 7, 1),
            data_final=date(2026, 7, 31),
            usuario=self.usuario,
            **filtros,
        )

    def test_zero_real_e_somente_diaristas(self):
        vazio = self.relatorio()
        resumo = vazio["summary"]
        self.assertEqual(resumo["diaristCostState"], "calculated")
        self.assertEqual(resumo["diaristCostTotal"], "0.00")
        self.assertEqual(resumo["monthlySalaryState"], "calculated")
        self.assertEqual(resumo["monthlySalaryTotal"], "0.00")
        self.assertEqual(resumo["teamCostState"], "calculated")
        self.assertEqual(resumo["teamCostTotal"], "0.00")

        self.participar(self.criar_diarista(201))
        diaristas = self.relatorio(tipo_vinculo=Servidor.VINCULO_DIARISTA)
        resumo = diaristas["summary"]
        self.assertEqual(resumo["diaristCostTotal"], "100.00")
        self.assertEqual(resumo["monthlySalaryState"], "outOfFilter")
        self.assertIsNone(resumo["monthlySalaryTotal"])
        self.assertEqual(resumo["teamCostState"], "calculated")
        self.assertEqual(resumo["teamCostTotal"], "100.00")
        self.assertEqual(resumo["totalPeriod"], "100.00")

    def test_somente_mensalistas_usa_previsto_materializado(self):
        mensalista = self.criar_mensalista_configurado(202, "2300.00")
        self.participar(mensalista)

        resultado = self.relatorio(tipo_vinculo=Servidor.VINCULO_MENSALISTA)
        resumo = resultado["summary"]
        self.assertEqual(resumo["diaristCostState"], "outOfFilter")
        self.assertIsNone(resumo["diaristCostTotal"])
        self.assertEqual(resumo["monthlySalaryState"], "calculated")
        self.assertEqual(resumo["monthlySalaryTotal"], "2300.00")
        self.assertEqual(resumo["teamCostTotal"], "2300.00")
        self.assertEqual(resumo["totalPeriod"], "2300.00")
        self.assertEqual(resultado["meta"]["salaryPeriodBasis"], "dueDate")
        self.assertEqual(
            resultado["meta"]["salaryValueBasis"],
            "plannedMaterializedAmount",
        )

    def test_diarista_e_mensalista_nao_duplicam_salario_na_participacao(self):
        self.participar(self.criar_diarista(203))
        mensalista = self.criar_mensalista_configurado(204, "2000.00")
        participacao = self.participar(mensalista)
        self.assertEqual(participacao.valor_final, Decimal("0.00"))
        estado_antes = (
            CustoFixo.objects.count(),
            list(
                ParticipacaoServidorEvento.objects.order_by("pk").values_list(
                    "pk",
                    "valor_final",
                )
            ),
        )

        resultado = self.relatorio()
        resumo = resultado["summary"]
        self.assertEqual(resumo["diaristCostTotal"], "100.00")
        self.assertEqual(resumo["monthlySalaryTotal"], "2000.00")
        self.assertEqual(resumo["teamCostTotal"], "2100.00")
        self.assertEqual(resumo["totalPeriod"], "2100.00")
        self.assertEqual(
            (
                CustoFixo.objects.count(),
                list(
                    ParticipacaoServidorEvento.objects.order_by("pk").values_list(
                        "pk",
                        "valor_final",
                    )
                ),
            ),
            estado_antes,
        )

    def test_status_pendente_parcial_e_pago_entram_pelo_previsto(self):
        servidores = [
            self.criar_mensalista_configurado(205, "1000.00"),
            self.criar_mensalista_configurado(206, "2000.00"),
            self.criar_mensalista_configurado(207, "3000.00"),
        ]
        ocorrencias = [
            CustoFixo.objects.get(servidor_salario=servidor)
            for servidor in servidores
        ]
        CustoFixo.objects.filter(pk=ocorrencias[0].pk).update(
            status=STATUS_PENDENTE,
            valor_pago=Decimal("0.00"),
        )
        CustoFixo.objects.filter(pk=ocorrencias[1].pk).update(
            status=STATUS_PARCIAL,
            valor_pago=Decimal("500.00"),
        )
        CustoFixo.objects.filter(pk=ocorrencias[2].pk).update(
            status=STATUS_PAGO,
            valor_pago=Decimal("3000.00"),
        )

        resumo = self.relatorio()["summary"]
        self.assertEqual(resumo["monthlySalaryState"], "calculated")
        self.assertEqual(resumo["monthlySalaryTotal"], "6000.00")
        self.assertEqual(resumo["teamCostTotal"], "6000.00")

    def test_cancelado_e_inativo_ficam_fora_sem_tornar_cobertura_incompleta(self):
        cancelado = self.criar_mensalista_configurado(208, "1100.00")
        inativo = self.criar_mensalista_configurado(209, "1200.00")
        valido = self.criar_mensalista_configurado(210, "1300.00")
        CustoFixo.objects.filter(servidor_salario=cancelado).update(
            status=STATUS_CANCELADO
        )
        CustoFixo.objects.filter(servidor_salario=inativo).update(ativo=False)

        resultado = self.relatorio()
        resumo = resultado["summary"]
        self.assertEqual(resumo["monthlySalaryState"], "calculated")
        self.assertEqual(resumo["monthlySalaryTotal"], "1300.00")
        self.assertEqual(resumo["teamCostTotal"], "1300.00")
        self.assertEqual(resumo["totalPeriod"], "1300.00")
        self.assertEqual(
            [item["serverId"] for item in resultado["servers"]],
            [valido.id],
        )

    def test_ocorrencia_esperada_ausente_e_configuracao_ausente_sao_incompletas(self):
        configurado = self.criar_mensalista_configurado(211, "2500.00")
        CustoFixo.objects.filter(servidor_salario=configurado).delete()
        resultado = self.relatorio()
        resumo = resultado["summary"]
        self.assertEqual(resumo["monthlySalaryState"], "incomplete")
        self.assertEqual(
            resumo["monthlySalaryReason"],
            "SALARY_OCCURRENCE_MISSING",
        )
        self.assertIsNone(resumo["monthlySalaryTotal"])
        self.assertEqual(resumo["teamCostState"], "incomplete")
        self.assertIsNone(resumo["teamCostTotal"])
        self.assertEqual(resumo["totalPeriod"], "0.00")
        mensalistas_incompletos = self.relatorio(
            tipo_vinculo=Servidor.VINCULO_MENSALISTA
        )["summary"]
        self.assertEqual(mensalistas_incompletos["teamCostState"], "incomplete")
        self.assertIsNone(mensalistas_incompletos["teamCostTotal"])

        criar_servidor(
            dados=self.dados_servidor(
                212,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2600.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        mensalista_sem_config = Servidor.objects.get(nome="Servidor 212")
        resultado = self.relatorio(servidor_id=str(mensalista_sem_config.pk))
        self.assertEqual(
            resultado["summary"]["monthlySalaryReason"],
            "SALARY_CONFIGURATION_MISSING",
        )

    def test_filtros_incompativeis_e_vinculos_explicitos(self):
        diarista = self.criar_diarista(213)
        self.participar(diarista)
        self.criar_mensalista_configurado(214, "2700.00")

        casos = [
            ({"evento_id": str(self.evento.pk)}, "EVENT_SCOPE_REQUIRES_MONTHLY_ALLOCATION"),
            ({"servico_id": str(self.servico.pk)}, "SERVICE_SCOPE_REQUIRES_MONTHLY_ALLOCATION"),
            ({"valor_editado": "false"}, "PARTICIPATION_FILTER_NOT_APPLICABLE_TO_SALARY"),
            (
                {
                    "evento_id": str(self.evento.pk),
                    "servico_id": str(self.servico.pk),
                    "valor_editado": "false",
                },
                "EVENT_SCOPE_REQUIRES_MONTHLY_ALLOCATION",
            ),
        ]
        for filtros, motivo in casos:
            with self.subTest(filtros=filtros):
                resumo = self.relatorio(**filtros)["summary"]
                self.assertEqual(resumo["monthlySalaryState"], "notApplicable")
                self.assertEqual(resumo["monthlySalaryReason"], motivo)
                self.assertEqual(resumo["teamCostState"], "notApplicable")
                self.assertIsNone(resumo["teamCostTotal"])

        diaristas = self.relatorio(
            tipo_vinculo=Servidor.VINCULO_DIARISTA,
            evento_id=str(self.evento.pk),
        )["summary"]
        self.assertEqual(diaristas["monthlySalaryState"], "outOfFilter")
        self.assertEqual(diaristas["teamCostTotal"], "100.00")

        mensalistas = self.relatorio(
            tipo_vinculo=Servidor.VINCULO_MENSALISTA
        )["summary"]
        self.assertEqual(mensalistas["diaristCostState"], "outOfFilter")
        self.assertEqual(mensalistas["monthlySalaryTotal"], "2700.00")
        self.assertEqual(mensalistas["teamCostTotal"], "2700.00")

        mensalistas_por_evento = self.relatorio(
            tipo_vinculo=Servidor.VINCULO_MENSALISTA,
            evento_id=str(self.evento.pk),
        )["summary"]
        self.assertEqual(
            mensalistas_por_evento["monthlySalaryState"],
            "notApplicable",
        )
        self.assertEqual(
            mensalistas_por_evento["teamCostState"],
            "notApplicable",
        )
        self.assertIsNone(mensalistas_por_evento["teamCostTotal"])

        periodo_extenso = custos_por_servidor(
            data_inicial=date(2000, 1, 1),
            data_final=date(2026, 7, 31),
            usuario=self.usuario,
        )["summary"]
        self.assertEqual(periodo_extenso["monthlySalaryState"], "incomplete")
        self.assertEqual(
            periodo_extenso["monthlySalaryReason"],
            "SALARY_COVERAGE_PERIOD_EXCEEDS_LIMIT",
        )

    def test_mudanca_de_vinculo_preserva_naturezas_historicas_sem_duplicar(self):
        servidor = self.criar_diarista(216)
        self.participar(servidor)
        atualizar_servidor(
            servidor,
            dados=self.dados_servidor(
                216,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2800.00"),
                data_inicio_contrato=date(2026, 7, 1),
                dia_pagamento_salario=5,
                data_autorizacao_custo_salarial=date(2026, 7, 1),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )

        resultado = self.relatorio()
        self.assertEqual(resultado["summary"]["diaristCostTotal"], "100.00")
        self.assertEqual(resultado["summary"]["monthlySalaryTotal"], "2800.00")
        self.assertEqual(resultado["summary"]["teamCostTotal"], "2900.00")
        self.assertEqual(len(resultado["servers"]), 1)
        grupo = resultado["servers"][0]
        self.assertEqual(grupo["linkType"], "MIXED")
        self.assertEqual(grupo["linkTypes"], ["DIARISTA", "MENSALISTA"])
        self.assertEqual(grupo["participationCostTotal"], "100.00")
        self.assertEqual(grupo["salaryCostTotal"], "2800.00")

        diaristas = self.relatorio(tipo_vinculo="DIARISTA")["servers"][0]
        self.assertEqual(diaristas["linkType"], "DIARISTA")
        mensalistas = self.relatorio(tipo_vinculo="MENSALISTA")["servers"][0]
        self.assertEqual(mensalistas["linkType"], "MENSALISTA")

    def test_bases_historicas_explicitas_preservam_inicio_do_evento_e_estado_atual(self):
        servidor = self.criar_diarista(217)
        self.evento.data_inicio = date(2026, 6, 30)
        self.evento.data_fim = date(2026, 7, 1)
        self.evento.save(update_fields=["data_inicio", "data_fim"])
        self.participar(
            servidor,
            datas_trabalhadas=[
                {"data": date(2026, 7, 1), "quantidade_horas": Decimal("6.00")}
            ],
        )
        servidor.ativo = False
        servidor.save(update_fields=["ativo"])

        julho = self.relatorio(ativo="false")
        self.assertEqual(julho["summary"]["diaristCostTotal"], "0.00")
        self.assertEqual(julho["servers"], [])
        self.assertEqual(julho["meta"]["diaristPeriodBasis"], "eventStartDate")
        self.assertEqual(julho["meta"]["activeFilterBasis"], "currentRegistrationState")
        self.assertEqual(
            julho["meta"]["serverFilterBasis"],
            "currentIdOrHistoricalSnapshotId",
        )

        junho = custos_por_servidor(
            data_inicial=date(2026, 6, 1),
            data_final=date(2026, 6, 30),
            ativo="false",
            usuario=self.usuario,
        )
        self.assertEqual(junho["summary"]["diaristCostTotal"], "100.00")

    def test_servidor_excluido_permanece_identificado_por_snapshot(self):
        servidor = self.criar_diarista(218)
        referencia = servidor.pk
        nome = servidor.nome
        self.participar(servidor)
        excluir_servidor(servidor, usuario=self.usuario)

        resultado = self.relatorio(existencia="deleted")
        self.assertEqual(len(resultado["servers"]), 1)
        grupo = resultado["servers"][0]
        self.assertIsNone(grupo["serverId"])
        self.assertEqual(grupo["serverReferenceId"], referencia)
        self.assertEqual(grupo["serverName"], nome)
        self.assertTrue(grupo["serverDeleted"])

    def test_legado_parcial_nao_quebra_nem_entra_no_total(self):
        referencia = self.criar_diarista(215)
        CustoFixo.objects.create(
            descricao="Salário legado parcial",
            categoria="salario",
            valor_previsto=Decimal("9999.00"),
            data_vencimento=date(2026, 7, 5),
            origem_recorrencia="legado",
            servidor_salario=referencia,
        )

        resultado = self.relatorio()
        resumo = resultado["summary"]
        self.assertEqual(resumo["monthlySalaryState"], "incomplete")
        self.assertEqual(
            resumo["monthlySalaryReason"],
            "LEGACY_SALARY_UNCORRELATED",
        )
        self.assertIsNone(resumo["monthlySalaryTotal"])
        self.assertIsNone(resumo["teamCostTotal"])
        self.assertEqual(resumo["totalPeriod"], "0.00")
        self.assertEqual(resultado["servers"], [])

    def test_openapi_usa_um_enum_canonico_para_estados_dos_cards(self):
        schema = SchemaGenerator().get_schema(public=True)
        componentes = schema["components"]["schemas"]
        self.assertEqual(
            componentes["ServerCostStateEnum"]["enum"],
            [
                "calculated",
                "restricted",
                "incomplete",
                "notApplicable",
                "outOfFilter",
            ],
        )
        propriedades = componentes["CustosPorServidorSummary"]["properties"]
        for campo in (
            "diaristCostState",
            "monthlySalaryState",
            "teamCostState",
        ):
            self.assertEqual(
                propriedades[campo]["$ref"],
                "#/components/schemas/ServerCostStateEnum",
            )


class JornadaMensalServidorTests(ServidoresFixtureMixin, TenantAppTestCase):
    def dados_mensalista(self, indice, jornada):
        return self.dados_servidor(
            indice,
            tipo_vinculo=Servidor.VINCULO_MENSALISTA,
            salario_mensal=Decimal("3000.00"),
            carga_horaria_mensal=jornada,
        )

    def test_jornada_sem_default_cria_e_fecha_vigencias_explicitas(self):
        sem_jornada = criar_servidor(
            dados=self.dados_mensalista(220, None),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 1, 1),
        )
        self.assertIsNone(sem_jornada.carga_horaria_mensal)
        self.assertFalse(
            HistoricoJornadaMensalServidor.objects.filter(
                servidor=sem_jornada
            ).exists()
        )

        servidor = criar_servidor(
            dados=self.dados_mensalista(221, Decimal("160.00")),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 1, 1),
            data_vigencia_jornada=date(2026, 1, 1),
        )
        atualizar_servidor(
            servidor,
            dados=self.dados_mensalista(221, Decimal("176.00")),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 1, 1),
            data_vigencia_jornada=date(2026, 7, 1),
        )
        vigencias = list(
            HistoricoJornadaMensalServidor.objects.filter(
                servidor=servidor
            ).order_by("data_inicio")
        )
        self.assertEqual(len(vigencias), 2)
        self.assertEqual(vigencias[0].horas_mensais, Decimal("160.00"))
        self.assertEqual(vigencias[0].data_fim, date(2026, 6, 30))
        self.assertEqual(vigencias[1].horas_mensais, Decimal("176.00"))
        self.assertIsNone(vigencias[1].data_fim)

    def test_jornada_valida_limites_vinculo_e_sobreposicao(self):
        for indice, jornada in ((222, Decimal("0.00")), (223, Decimal("744.01"))):
            with self.subTest(jornada=jornada), self.assertRaises(ValidationError):
                criar_servidor(
                    dados=self.dados_mensalista(indice, jornada),
                    servicos_ids=[self.servico.id],
                    usuario=self.usuario,
                )
        with self.assertRaises(ValidationError):
            criar_servidor(
                dados=self.dados_servidor(
                    224,
                    carga_horaria_mensal=Decimal("160.00"),
                ),
                servicos_ids=[self.servico.id],
                usuario=self.usuario,
            )

        servidor = criar_servidor(
            dados=self.dados_mensalista(225, Decimal("160.00")),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_jornada=date(2026, 1, 1),
        )
        sobreposta = HistoricoJornadaMensalServidor(
            servidor=servidor,
            servidor_id_snapshot=servidor.pk,
            servidor_nome_snapshot=servidor.nome,
            horas_mensais=Decimal("180.00"),
            data_inicio=date(2026, 6, 1),
        )
        with self.assertRaises(ValidationError):
            sobreposta.full_clean()

    def test_exclusao_preserva_snapshot_da_jornada(self):
        servidor = criar_servidor(
            dados=self.dados_mensalista(226, Decimal("160.00")),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_jornada=date(2026, 1, 1),
        )
        referencia = servidor.pk
        nome = servidor.nome
        excluir_servidor(servidor, usuario=self.usuario)

        historico = HistoricoJornadaMensalServidor.objects.get(
            servidor_id_snapshot=referencia
        )
        self.assertIsNone(historico.servidor_id)
        self.assertEqual(historico.servidor_nome_snapshot, nome)
        self.assertEqual(historico.horas_mensais, Decimal("160.00"))


class EscalaDiariaServidoresTests(ServidoresFixtureMixin, TenantAppTestCase):
    def ampliar_evento(self, data_fim=date(2026, 7, 22)):
        self.evento.data_fim = data_fim
        self.evento.save(update_fields=["data_fim"])

    def test_eventos_de_um_e_varios_dias_derivam_totais(self):
        participacao_um_dia = self.participar(
            self.criar_diarista(101),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        self.assertEqual(participacao_um_dia.quantidade_dias, 1)
        self.assertEqual(participacao_um_dia.quantidade_horas, Decimal("8.00"))

        self.ampliar_evento()
        participacao_varios_dias = self.participar(
            self.criar_diarista(102),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")},
                {"data": date(2026, 7, 22), "quantidade_horas": Decimal("6.00")},
            ],
        )
        self.assertEqual(participacao_varios_dias.quantidade_dias, 2)
        self.assertEqual(participacao_varios_dias.quantidade_horas, Decimal("14.00"))
        self.assertEqual(
            list(
                participacao_varios_dias.dias_trabalhados.values_list(
                    "data",
                    "quantidade_horas",
                )
            ),
            [
                (date(2026, 7, 20), Decimal("8.00")),
                (date(2026, 7, 22), Decimal("6.00")),
            ],
        )

    def test_evento_que_atravessa_mes_aceita_data_interna(self):
        self.evento.data_inicio = date(2026, 7, 31)
        self.evento.data_fim = date(2026, 8, 2)
        self.evento.save(update_fields=["data_inicio", "data_fim"])
        participacao = self.participar(
            self.criar_diarista(103),
            datas_trabalhadas=[
                {"data": date(2026, 8, 1), "quantidade_horas": None}
            ],
        )
        self.assertEqual(participacao.quantidade_dias, 1)
        self.assertEqual(participacao.quantidade_horas, Decimal("0.00"))

    def test_periodo_do_evento_nao_pode_excluir_data_ja_trabalhada(self):
        self.ampliar_evento()
        self.participar(
            self.criar_diarista(113),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        self.evento.data_inicio = date(2026, 7, 21)
        with self.assertRaises(ValidationError):
            self.evento.full_clean()

    def test_rejeita_data_fora_duplicada_e_horas_nao_positivas(self):
        self.ampliar_evento()
        servidor = self.criar_diarista(104)
        casos = (
            [
                {"data": date(2026, 7, 19), "quantidade_horas": Decimal("8.00")}
            ],
            [
                {"data": date(2026, 7, 23), "quantidade_horas": Decimal("8.00")}
            ],
            [
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")},
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("6.00")},
            ],
            [
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("0.00")}
            ],
            [
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("-1.00")}
            ],
        )
        for escala in casos:
            with self.subTest(escala=escala):
                with self.assertRaises(ValidationError):
                    self.participar(servidor, datas_trabalhadas=escala)
                self.assertFalse(
                    ParticipacaoServidorEvento.objects.filter(
                        servidor=servidor
                    ).exists()
                )

    def test_mesma_data_e_permitida_para_pessoas_diferentes_e_unica_na_participacao(self):
        escala = [{"data": date(2026, 7, 20), "quantidade_horas": None}]
        primeira = self.participar(
            self.criar_diarista(105),
            datas_trabalhadas=escala,
        )
        segunda = self.participar(
            self.criar_diarista(106),
            datas_trabalhadas=escala,
        )
        self.assertEqual(primeira.dias_trabalhados.count(), 1)
        self.assertEqual(segunda.dias_trabalhados.count(), 1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServidorEventoDiaTrabalhado.objects.create(
                    participacao=primeira,
                    data=date(2026, 7, 20),
                )

    def test_dois_servidores_podem_dividir_dias_do_mesmo_evento(self):
        self.ampliar_evento(date(2026, 7, 21))
        primeira = self.participar(
            self.criar_diarista(114),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        segunda = self.participar(
            self.criar_diarista(115),
            datas_trabalhadas=[
                {"data": date(2026, 7, 21), "quantidade_horas": Decimal("8.00")}
            ],
        )
        self.assertEqual(
            list(primeira.dias_trabalhados.values_list("data", flat=True)),
            [date(2026, 7, 20)],
        )
        self.assertEqual(
            list(segunda.dias_trabalhados.values_list("data", flat=True)),
            [date(2026, 7, 21)],
        )

    def test_edicao_substitui_datas_remove_desmarcadas_e_recalcula_totais(self):
        self.ampliar_evento()
        participacao = self.participar(
            self.criar_diarista(107),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")},
                {"data": date(2026, 7, 21), "quantidade_horas": Decimal("8.00")},
            ],
        )
        participacao = atualizar_participacao(
            participacao,
            servico=self.servico,
            quantidade_dias=999,
            quantidade_horas=Decimal("999.00"),
            datas_trabalhadas=[
                {"data": date(2026, 7, 21), "quantidade_horas": Decimal("6.00")},
                {"data": date(2026, 7, 22), "quantidade_horas": None},
            ],
            usuario=self.usuario,
        )
        self.assertEqual(participacao.quantidade_dias, 2)
        self.assertEqual(participacao.quantidade_horas, Decimal("6.00"))
        self.assertEqual(
            list(participacao.dias_trabalhados.values_list("data", flat=True)),
            [date(2026, 7, 21), date(2026, 7, 22)],
        )

    def test_totais_derivados_mantem_resultado_do_rateio(self):
        self.ampliar_evento(date(2026, 7, 21))
        primeira = self.participar(self.criar_diarista(108), dias=2)
        segunda = self.participar(
            self.criar_diarista(109),
            dias=1,
            horas=Decimal("4.00"),
        )
        primeira.refresh_from_db()
        segunda.refresh_from_db()
        valores_legados = (primeira.valor_final, segunda.valor_final)

        primeira = atualizar_participacao(
            primeira,
            servico=self.servico,
            quantidade_dias=2,
            quantidade_horas=Decimal("0.00"),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": None},
                {"data": date(2026, 7, 21), "quantidade_horas": None},
            ],
            usuario=self.usuario,
        )
        segunda = atualizar_participacao(
            segunda,
            servico=self.servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("4.00"),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("4.00")}
            ],
            usuario=self.usuario,
        )
        primeira.refresh_from_db()
        segunda.refresh_from_db()
        self.assertEqual(
            (primeira.valor_final, segunda.valor_final),
            valores_legados,
        )
        self.assertEqual(
            primeira.valor_final + segunda.valor_final,
            Decimal("100.00"),
        )

    def test_mensalista_e_historico_preservam_regras_financeiras_e_serializacao(self):
        historica = self.participar(self.criar_diarista(110), dias=3)
        payload_historico = serializar_participacao(historica)
        self.assertFalse(payload_historico["workDatesProvided"])
        self.assertEqual(payload_historico["workedDays"], [])
        self.assertEqual(payload_historico["days"], 3)

        mensalista = criar_servidor(
            dados=self.dados_servidor(
                111,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2500.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        participacao_mensalista = self.participar(
            mensalista,
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        self.assertEqual(participacao_mensalista.valor_calculado, Decimal("0.00"))
        self.assertEqual(participacao_mensalista.valor_final, Decimal("0.00"))

        custos = custos_por_servidor(
            data_inicial=date(2026, 7, 1),
            data_final=date(2026, 7, 31),
            usuario=self.usuario,
        )
        item_historico = next(
            item
            for grupo in custos["servers"]
            for item in grupo["participations"]
            if item["id"] == historica.id
        )
        item_mensalista = next(
            item
            for grupo in custos["servers"]
            for item in grupo["participations"]
            if item["id"] == participacao_mensalista.id
        )
        self.assertFalse(item_historico["workDatesProvided"])
        self.assertTrue(item_mensalista["workDatesProvided"])
        self.assertEqual(item_mensalista["financialRealCost"], "0.00")

        distribuicao = _distribuicoes_servidores_por_evento([self.evento.id])[
            self.evento.id
        ]
        participantes = [
            item
            for servico in distribuicao["services"]
            for item in servico["participants"]
        ]
        mensalista_serializado = next(
            item
            for item in participantes
            if item["participationId"] == participacao_mensalista.id
        )
        self.assertTrue(mensalista_serializado["workDatesProvided"])
        self.assertEqual(mensalista_serializado["financialRealCost"], 0.0)


class EscalaDiariaConcorrenciaPostgreSQLTests(
    ServidoresFixtureMixin,
    TenantTransactionTestCase,
):
    def setUp(self):
        super().setUp()
        if connection.vendor != "postgresql":
            self.skipTest("Concorrência da escala diária exige PostgreSQL.")
        self.evento.data_fim = date(2026, 7, 22)
        self.evento.save(update_fields=["data_fim"])

    def test_atualizacoes_simultaneas_nao_criam_datas_duplicadas(self):
        participacao = self.participar(
            self.criar_diarista(112),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        outra_participacao = self.participar(
            self.criar_diarista(116),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        barreira = Barrier(2)
        lock = Lock()
        erros = []
        escalas = (
            [
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")},
                {"data": date(2026, 7, 21), "quantidade_horas": Decimal("6.00")},
            ],
            [
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")},
                {"data": date(2026, 7, 22), "quantidade_horas": Decimal("4.00")},
            ],
        )

        def executar(escala):
            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                barreira.wait(timeout=10)
                atualizar_participacao(
                    ParticipacaoServidorEvento.objects.get(pk=participacao.pk),
                    servico=Servico.objects.get(pk=self.servico.pk),
                    quantidade_dias=1,
                    quantidade_horas=Decimal("8.00"),
                    datas_trabalhadas=escala,
                    usuario=get_user_model().objects.get(pk=self.usuario.pk),
                )
            except Exception as error:
                with lock:
                    erros.append(error)
            finally:
                close_old_connections()

        threads = [Thread(target=executar, args=(escala,)) for escala in escalas]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(erros, [])
        datas_finais = set(
            ServidorEventoDiaTrabalhado.objects.filter(
                participacao=participacao
            ).values_list("data", flat=True)
        )
        self.assertIn(
            datas_finais,
            (
                {date(2026, 7, 20), date(2026, 7, 21)},
                {date(2026, 7, 20), date(2026, 7, 22)},
            ),
        )
        self.assertEqual(len(datas_finais), 2)
        participacao.refresh_from_db()
        outra_participacao.refresh_from_db()
        self.custo.refresh_from_db()
        self.assertEqual(participacao.quantidade_dias, 2)
        self.assertIn(
            participacao.quantidade_horas,
            (Decimal("12.00"), Decimal("14.00")),
        )
        self.assertEqual(
            participacao.valor_final + outra_participacao.valor_final,
            self.custo.valor_diarias,
        )
        self.assertEqual(self.custo.valor_diarias, Decimal("100.00"))


    def test_periodo_e_escala_concorrentes_nao_persistem_dia_fora_do_intervalo(self):
        participacao = self.participar(
            self.criar_diarista(117),
            datas_trabalhadas=[
                {"data": date(2026, 7, 20), "quantidade_horas": Decimal("8.00")}
            ],
        )
        barreira = Barrier(2)
        lock = Lock()
        erros = []

        def atualizar_periodo():
            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                barreira.wait(timeout=10)
                atualizar_evento_com_periodo(
                    Evento.objects.get(pk=self.evento.pk),
                    valores={"data_inicio": date(2026, 7, 21)},
                    usuario=get_user_model().objects.get(pk=self.usuario.pk),
                )
            except Exception as error:
                with lock:
                    erros.append(error)
            finally:
                close_old_connections()

        def substituir_escala():
            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                barreira.wait(timeout=10)
                atualizar_participacao(
                    ParticipacaoServidorEvento.objects.get(pk=participacao.pk),
                    servico=Servico.objects.get(pk=self.servico.pk),
                    quantidade_dias=1,
                    quantidade_horas=Decimal("8.00"),
                    datas_trabalhadas=[
                        {"data": date(2026, 7, 21), "quantidade_horas": Decimal("8.00")}
                    ],
                    usuario=get_user_model().objects.get(pk=self.usuario.pk),
                )
            except Exception as error:
                with lock:
                    erros.append(error)
            finally:
                close_old_connections()

        threads = [Thread(target=atualizar_periodo), Thread(target=substituir_escala)]
        for thread in threads:
            thread.start()
        for thread in threads:
            # Uma operação que não libera o lock canônico rapidamente é falha
            # de concorrência; encerrar o teste antes do timeout externo também
            # preserva evidência diagnóstica para a F7.
            thread.join(timeout=15)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertTrue(all(isinstance(error, ValidationError) for error in erros))
        self.assertLessEqual(len(erros), 1)
        self.evento.refresh_from_db()
        dias = ServidorEventoDiaTrabalhado.objects.filter(
            participacao=participacao,
        ).values_list("data", flat=True)
        self.assertTrue(
            all(self.evento.data_inicio <= dia <= self.evento.data_fim for dia in dias)
        )


class ServidoresApiTests(ServidoresFixtureMixin, TenantAppTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.usuario)
        csrf_response = self.client.get(reverse("caixa:api_auth_csrf"))
        self.csrf = csrf_response.json()["csrfToken"]

    def payload(self, indice=30):
        return {
            "name": f"Servidor API {indice}",
            "documentType": "CPF",
            "document": f"999999999{indice:02d}",
            "phone": "85999999999",
            "email": f"servidor{indice}@example.com",
            "birthDate": "1990-01-01",
            "address": "Rua Teste",
            "notes": "Teste API",
            "active": True,
            "linkType": "DIARISTA",
            "monthlySalary": None,
            "serviceIds": [self.servico.id],
        }

    def test_crud_servidor_exige_csrf_e_preserva_contrato(self):
        url = reverse("caixa:api_servidores")
        sem_csrf = self.client.post(url, self.payload(), content_type="application/json")
        self.assertEqual(sem_csrf.status_code, 403)
        resposta = self.client.post(
            url,
            self.payload(),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 201)
        servidor_id = resposta.json()["data"]["server"]["id"]
        self.assertFalse(
            resposta.json()["data"]["server"]["displayAsPartner"]
        )
        self.assertFalse(
            Servidor.objects.get(pk=servidor_id).exibir_como_socio
        )
        detalhe = reverse("caixa:api_servidor_detalhe", args=[servidor_id])
        self.assertEqual(self.client.get(detalhe).status_code, 200)
        payload = self.payload()
        payload["active"] = False
        atualizado = self.client.put(
            detalhe,
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(atualizado.status_code, 200)
        excluido = self.client.delete(detalhe, HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(excluido.status_code, 204)

    def test_api_cadastra_e_altera_jornada_mensal_com_vigencia(self):
        payload = {
            **self.payload(219),
            "linkType": "MENSALISTA",
            "monthlySalary": "3200.00",
            "monthlyWorkloadHours": "160.00",
            "salaryEffectiveDate": "2026-01-01",
            "workloadEffectiveDate": "2026-01-01",
        }
        resposta = self.client.post(
            reverse("caixa:api_servidores"),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        item = resposta.json()["data"]["server"]
        self.assertEqual(item["monthlyWorkloadHours"], "160.00")
        servidor = Servidor.objects.get(pk=item["id"])
        self.assertEqual(
            HistoricoJornadaMensalServidor.objects.get(
                servidor=servidor
            ).data_inicio,
            date(2026, 1, 1),
        )

        payload["monthlyWorkloadHours"] = "176.00"
        payload["workloadEffectiveDate"] = "2026-07-01"
        atualizada = self.client.put(
            reverse("caixa:api_servidor_detalhe", args=[servidor.pk]),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(atualizada.status_code, 200, atualizada.content)
        self.assertEqual(
            atualizada.json()["data"]["server"]["monthlyWorkloadHours"],
            "176.00",
        )
        vigencias = list(
            HistoricoJornadaMensalServidor.objects.filter(
                servidor=servidor
            ).order_by("data_inicio")
        )
        self.assertEqual(
            [(item.horas_mensais, item.data_inicio, item.data_fim) for item in vigencias],
            [
                (Decimal("160.00"), date(2026, 1, 1), date(2026, 6, 30)),
                (Decimal("176.00"), date(2026, 7, 1), None),
            ],
        )

    def test_cliente_legado_pode_mudar_mensalista_para_diarista_sem_novo_campo(self):
        payload = {
            **self.payload(218),
            "linkType": "MENSALISTA",
            "monthlySalary": "3200.00",
            "monthlyWorkloadHours": "160.00",
            "salaryEffectiveDate": "2026-01-01",
            "workloadEffectiveDate": "2026-01-01",
        }
        criada = self.client.post(
            reverse("caixa:api_servidores"),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(criada.status_code, 201, criada.content)
        servidor_id = criada.json()["data"]["server"]["id"]

        payload["linkType"] = "DIARISTA"
        payload["monthlySalary"] = None
        payload["salaryEffectiveDate"] = "2026-08-01"
        payload.pop("monthlyWorkloadHours")
        payload.pop("workloadEffectiveDate")
        atualizada = self.client.put(
            reverse("caixa:api_servidor_detalhe", args=[servidor_id]),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )

        self.assertEqual(atualizada.status_code, 200, atualizada.content)
        servidor = Servidor.objects.get(pk=servidor_id)
        self.assertEqual(servidor.tipo_vinculo, Servidor.VINCULO_DIARISTA)
        self.assertIsNone(servidor.carga_horaria_mensal)
        historico = HistoricoJornadaMensalServidor.objects.get(
            servidor=servidor
        )
        self.assertEqual(historico.data_fim, date(2026, 7, 31))

    def test_socio_diarista_altera_somente_apresentacao(self):
        payload = {
            **self.payload(89),
            "displayAsPartner": True,
        }
        resposta = self.client.post(
            reverse("caixa:api_servidores"),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        item = resposta.json()["data"]["server"]
        servidor = Servidor.objects.get(pk=item["id"])

        self.assertTrue(item["displayAsPartner"])
        self.assertEqual(item["linkType"], "DIARISTA")
        self.assertEqual(item["linkTypeLabel"], "Diarista")
        self.assertTrue(servidor.exibir_como_socio)
        self.assertEqual(servidor.tipo_vinculo, Servidor.VINCULO_DIARISTA)
        self.assertFalse(
            HistoricoSalarialServidor.objects.filter(servidor=servidor).exists()
        )
        self.assertFalse(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).exists()
        )

        participacao = criar_participacao(
            evento=self.evento,
            servidor=servidor,
            servico=self.servico,
            quantidade_dias=1,
            quantidade_horas=Decimal("0.00"),
            usuario=self.usuario,
        )
        self.assertEqual(participacao.tipo_vinculo, Servidor.VINCULO_DIARISTA)
        self.assertEqual(participacao.valor_final, Decimal("100.00"))

        payload_sem_apresentacao = {
            chave: valor
            for chave, valor in payload.items()
            if chave != "displayAsPartner"
        }
        preservado = self.client.put(
            reverse("caixa:api_servidor_detalhe", args=[servidor.id]),
            payload_sem_apresentacao,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(preservado.status_code, 200, preservado.content)
        servidor.refresh_from_db()
        self.assertTrue(servidor.exibir_como_socio)

        atualizado = self.client.put(
            reverse("caixa:api_servidor_detalhe", args=[servidor.id]),
            {**payload, "displayAsPartner": False},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(atualizado.status_code, 200, atualizado.content)
        servidor.refresh_from_db()
        self.assertFalse(atualizado.json()["data"]["server"]["displayAsPartner"])
        self.assertFalse(servidor.exibir_como_socio)
        self.assertEqual(servidor.tipo_vinculo, Servidor.VINCULO_DIARISTA)
        participacao.refresh_from_db()
        self.assertEqual(participacao.valor_final, Decimal("100.00"))

    def test_socio_mensalista_preserva_plano_historico_e_filtros(self):
        competencia = timezone.localdate().replace(day=1)
        payload = {
            **self.payload(90),
            "linkType": "MENSALISTA",
            "displayAsPartner": True,
            "monthlySalary": "3200.00",
            "salaryEffectiveDate": competencia.isoformat(),
            "contractStartDate": competencia.isoformat(),
            "salaryPaymentDay": 5,
            "salaryAutomationFromDate": competencia.isoformat(),
            "confirmSalaryAutomationActivation": True,
        }
        resposta = self.client.post(
            reverse("caixa:api_servidores"),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        item = resposta.json()["data"]["server"]
        servidor = Servidor.objects.get(pk=item["id"])
        plano = PlanoCustoRecorrente.objects.get(servidor=servidor)
        historico = HistoricoSalarialServidor.objects.get(servidor=servidor)
        custo = CustoFixo.objects.get(
            servidor_salario=servidor,
            competencia=competencia,
        )

        self.assertTrue(item["displayAsPartner"])
        self.assertEqual(item["linkType"], "MENSALISTA")
        self.assertEqual(item["linkTypeLabel"], "Mensalista")
        self.assertEqual(servidor.tipo_vinculo, Servidor.VINCULO_MENSALISTA)
        self.assertEqual(historico.valor, Decimal("3200.00"))
        self.assertEqual(custo.valor_previsto, Decimal("3200.00"))
        self.assertEqual(plano.origem, PlanoCustoRecorrente.ORIGEM_SALARIO)

        estado_financeiro = {
            "planos": list(
                PlanoCustoRecorrente.objects.filter(
                    servidor=servidor
                ).values_list("id", flat=True)
            ),
            "historicos": list(
                HistoricoSalarialServidor.objects.filter(
                    servidor=servidor
                ).values_list("id", "valor", "data_inicio", "data_fim")
            ),
            "custos": list(
                CustoFixo.objects.filter(
                    servidor_salario=servidor
                ).values_list("id", "valor_previsto", "competencia")
            ),
        }
        atualizado = self.client.put(
            reverse("caixa:api_servidor_detalhe", args=[servidor.id]),
            {**payload, "displayAsPartner": False},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(atualizado.status_code, 200, atualizado.content)
        servidor.refresh_from_db()
        self.assertFalse(servidor.exibir_como_socio)
        self.assertEqual(servidor.tipo_vinculo, Servidor.VINCULO_MENSALISTA)
        self.assertEqual(
            estado_financeiro["planos"],
            list(
                PlanoCustoRecorrente.objects.filter(
                    servidor=servidor
                ).values_list("id", flat=True)
            ),
        )
        self.assertEqual(
            estado_financeiro["historicos"],
            list(
                HistoricoSalarialServidor.objects.filter(
                    servidor=servidor
                ).values_list("id", "valor", "data_inicio", "data_fim")
            ),
        )
        self.assertEqual(
            estado_financeiro["custos"],
            list(
                CustoFixo.objects.filter(
                    servidor_salario=servidor
                ).values_list("id", "valor_previsto", "competencia")
            ),
        )

        mensalistas = self.client.get(
            reverse("caixa:api_servidores"),
            {"linkType": "MENSALISTA"},
        ).json()["data"]
        self.assertIn(
            servidor.id,
            [registro["id"] for registro in mensalistas["servers"]],
        )
        self.assertEqual(mensalistas["summary"]["monthly"], 1)
        self.assertEqual(mensalistas["summary"]["daily"], 0)

    def test_openapi_documenta_socio_sem_novo_tipo_de_vinculo(self):
        schema = SchemaGenerator().get_schema(public=True)
        componentes = schema["components"]["schemas"]
        payload = componentes["ServidorPayload"]
        resposta = componentes["ServidorResponse"]

        self.assertEqual(
            payload["properties"]["displayAsPartner"]["type"],
            "boolean",
        )
        self.assertEqual(
            resposta["properties"]["displayAsPartner"]["type"],
            "boolean",
        )
        self.assertNotIn("SOCIO", componentes["LinkTypeEnum"]["enum"])

    def test_novo_mensalista_nao_ativa_automacao_silenciosamente(self):
        payload = self.payload(91)
        payload.update(
            {
                "linkType": "MENSALISTA",
                "monthlySalary": "3100.00",
                "salaryEffectiveDate": "2026-07-01",
            }
        )
        resposta = self.client.post(
            reverse("caixa:api_servidores"),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        servidor = Servidor.objects.get(
            pk=resposta.json()["data"]["server"]["id"]
        )
        self.assertIsNone(servidor.data_inicio_contrato)
        self.assertIsNone(servidor.dia_pagamento_salario)
        self.assertIsNone(servidor.data_autorizacao_custo_salarial)
        self.assertFalse(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).exists()
        )

    def test_primeira_ativacao_salarial_exige_confirmacao_explicita(self):
        payload = self.payload(92)
        payload.update(
            {
                "linkType": "MENSALISTA",
                "monthlySalary": "3200.00",
                "salaryEffectiveDate": "2026-07-01",
                "contractStartDate": "2026-07-01",
                "salaryPaymentDay": 5,
                "salaryAutomationFromDate": "2026-07-01",
            }
        )
        url = reverse("caixa:api_servidores")
        recusada = self.client.post(
            url,
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(recusada.status_code, 400)
        self.assertIn(
            "confirmSalaryAutomationActivation",
            recusada.json()["errors"],
        )
        self.assertFalse(
            Servidor.objects.filter(documento=payload["document"]).exists()
        )

        aceita = self.client.post(
            url,
            {**payload, "confirmSalaryAutomationActivation": True},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(aceita.status_code, 201, aceita.content)
        servidor = Servidor.objects.get(
            pk=aceita.json()["data"]["server"]["id"]
        )
        self.assertEqual(
            servidor.data_autorizacao_custo_salarial,
            date(2026, 7, 1),
        )
        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).count(),
            1,
        )

    def test_content_type_auth_e_metodo(self):
        url = reverse("caixa:api_servidores")
        resposta = self.client.post(
            url,
            "payload",
            content_type="text/plain",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 415)
        anonimo = Client().get(url)
        self.assertEqual(anonimo.status_code, 401)
        self.assertEqual(
            self.client.patch(url, HTTP_X_CSRFTOKEN=self.csrf).status_code,
            405,
        )

    def test_detalhes_inexistentes_e_periodo_invalido(self):
        self.assertEqual(
            self.client.get(reverse("caixa:api_servidor_detalhe", args=[999999])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("caixa:api_participacao_detalhe", args=[999999])).status_code,
            404,
        )
        resposta = self.client.get(
            reverse("caixa:api_custos_por_servidor"),
            {"startDate": "2026-08-01", "endDate": "2026-07-01"},
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("period", resposta.json()["errors"])

    def test_api_participacao_e_custos_por_servidor(self):
        servidor = self.criar_diarista(31)
        url = reverse("caixa:api_participacoes_evento", args=[self.evento.id])
        resposta = self.client.post(
            url,
            {
                "serverId": servidor.id,
                "serviceId": self.servico.id,
                "workedDays": [
                    {"date": "2026-07-20", "hours": "8.00"},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(resposta.status_code, 201)
        participacao = resposta.json()["data"]["participation"]
        self.assertEqual(participacao["finalAmount"], "100.00")
        self.assertEqual(participacao["days"], 1)
        self.assertEqual(participacao["hours"], "8.00")
        self.assertTrue(participacao["workDatesProvided"])
        self.assertEqual(
            participacao["workedDays"],
            [{"date": "2026-07-20", "hours": "8.00"}],
        )
        relatorio = self.client.get(
            reverse("caixa:api_custos_por_servidor"),
            {"startDate": "2026-07-01", "endDate": "2026-07-31"},
        )
        self.assertEqual(relatorio.status_code, 200)
        dados_custos = relatorio.json()["data"]
        self.assertEqual(dados_custos["summary"]["diaristCostTotal"], "100.00")
        self.assertEqual(dados_custos["summary"]["diaristCostState"], "calculated")
        self.assertEqual(dados_custos["summary"]["monthlySalaryTotal"], "0.00")
        self.assertEqual(dados_custos["summary"]["teamCostTotal"], "100.00")
        self.assertEqual(dados_custos["summary"]["totalPeriod"], "100.00")
        self.assertEqual(dados_custos["meta"]["diaristPeriodBasis"], "eventStartDate")
        self.assertEqual(dados_custos["meta"]["salaryPeriodBasis"], "dueDate")
        self.assertEqual(
            dados_custos["meta"]["activeFilterBasis"],
            "currentRegistrationState",
        )
        self.assertEqual(
            dados_custos["meta"]["manualEditFilterBasis"],
            "historicalParticipation",
        )

    def test_api_custos_rejeita_filtros_invalidos_desconhecidos_e_repetidos(self):
        url = reverse("caixa:api_custos_por_servidor")
        casos = [
            {"startDate": "invalida"},
            {"endDate": "31-07-2026"},
            {"serverId": "abc"},
            {"serverId": "0"},
            {"existence": "archived"},
            {"active": "yes"},
            {"linkType": "SOCIO"},
            {"serviceId": "-1"},
            {"eventId": "evento"},
            {"manuallyEdited": "maybe"},
            {"desconhecido": "1"},
        ]
        for parametros in casos:
            with self.subTest(parametros=parametros):
                resposta = self.client.get(url, parametros)
                self.assertEqual(resposta.status_code, 400)
                self.assertIn("errors", resposta.json())

        repetido = self.client.get(f"{url}?serverId=1&serverId=2")
        self.assertEqual(repetido.status_code, 400)
        self.assertIn("duplicates", repetido.json()["errors"])

    def test_api_valida_e_substitui_escala_diaria_sem_confiar_nos_totais(self):
        self.evento.data_fim = date(2026, 7, 22)
        self.evento.save(update_fields=["data_fim"])
        servidor = self.criar_diarista(33)
        url = reverse("caixa:api_participacoes_evento", args=[self.evento.id])

        sem_datas = self.client.post(
            url,
            {"serverId": servidor.id, "serviceId": self.servico.id},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(sem_datas.status_code, 400)
        self.assertIn("workedDays", sem_datas.json()["errors"])

        duplicada = self.client.post(
            url,
            {
                "serverId": servidor.id,
                "serviceId": self.servico.id,
                "workedDays": [
                    {"date": "2026-07-20", "hours": "8.00"},
                    {"date": "2026-07-20", "hours": "6.00"},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(duplicada.status_code, 400)
        self.assertIn("workedDays", duplicada.json()["errors"])

        fora_periodo = self.client.post(
            url,
            {
                "serverId": servidor.id,
                "serviceId": self.servico.id,
                "workedDays": [
                    {"date": "2026-07-23", "hours": "8.00"},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(fora_periodo.status_code, 400)
        self.assertIn("workedDays", fora_periodo.json()["errors"])

        criada = self.client.post(
            url,
            {
                "serverId": servidor.id,
                "serviceId": self.servico.id,
                "days": 99,
                "hours": "99.00",
                "workedDays": [
                    {"date": "2026-07-20", "hours": "8.00"},
                    {"date": "2026-07-22", "hours": "6.00"},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(criada.status_code, 201)
        participacao = criada.json()["data"]["participation"]
        self.assertEqual(participacao["days"], 2)
        self.assertEqual(participacao["hours"], "14.00")

        atualizada = self.client.put(
            reverse(
                "caixa:api_participacao_detalhe",
                args=[participacao["id"]],
            ),
            {
                "serviceId": self.servico.id,
                "days": 88,
                "hours": "88.00",
                "workedDays": [
                    {"date": "2026-07-21", "hours": None},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(atualizada.status_code, 200)
        payload = atualizada.json()["data"]["participation"]
        self.assertEqual(payload["days"], 1)
        self.assertEqual(payload["hours"], "0.00")
        self.assertEqual(
            payload["workedDays"],
            [{"date": "2026-07-21", "hours": None}],
        )

        listagem = self.client.get(url)
        self.assertEqual(listagem.status_code, 200)
        self.assertEqual(listagem.json()["data"]["event"]["startDate"], "2026-07-20")
        self.assertEqual(listagem.json()["data"]["event"]["endDate"], "2026-07-22")

    def test_custos_sem_permissao_salarial_nao_revelam_ocorrencia_ou_total(self):
        restrito = get_user_model().objects.create_user(
            "operacional-custos-sem-salario",
            password="senha",
        )
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_custos_servidor"),
        )
        client = Client()
        client.force_login(restrito)
        url = reverse("caixa:api_custos_por_servidor")

        antes = client.get(
            url,
            {"startDate": "2026-07-01", "endDate": "2026-07-31"},
        )
        self.assertEqual(antes.status_code, 200)
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                160,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("9876.54"),
                data_inicio_contrato=date(2026, 7, 1),
                dia_pagamento_salario=5,
                data_autorizacao_custo_salarial=date(2026, 7, 1),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        self.assertTrue(
            CustoFixo.objects.filter(
                servidor_salario=mensalista,
                origem_recorrencia="salario",
                competencia=date(2026, 7, 1),
            ).exists()
        )

        depois = client.get(
            url,
            {"startDate": "2026-07-01", "endDate": "2026-07-31"},
        )
        self.assertEqual(depois.status_code, 200)
        dados = depois.json()["data"]
        self.assertFalse(dados["permissions"]["canViewSalary"])
        self.assertEqual(dados["meta"]["salarySource"], "redacted")
        self.assertEqual(dados["summary"]["monthlySalaryState"], "restricted")
        self.assertIsNone(dados["summary"]["monthlySalaryTotal"])
        self.assertEqual(dados["summary"]["teamCostState"], "restricted")
        self.assertIsNone(dados["summary"]["teamCostTotal"])
        self.assertEqual(
            dados["summary"]["totalPeriod"],
            antes.json()["data"]["summary"]["totalPeriod"],
        )
        self.assertNotIn(mensalista.id, [item["serverId"] for item in dados["servers"]])

        individual = client.get(
            url,
            {
                "startDate": "2026-07-01",
                "endDate": "2026-07-31",
                "serverId": str(mensalista.id),
            },
        )
        self.assertEqual(individual.status_code, 200)
        self.assertEqual(individual.json()["data"]["servers"], [])
        self.assertEqual(individual.json()["data"]["summary"]["totalPeriod"], "0.00")

        mensalistas = client.get(
            url,
            {
                "startDate": "2026-07-01",
                "endDate": "2026-07-31",
                "linkType": "MENSALISTA",
            },
        ).json()["data"]["summary"]
        self.assertEqual(mensalistas["diaristCostState"], "outOfFilter")
        self.assertEqual(mensalistas["monthlySalaryState"], "restricted")
        self.assertEqual(mensalistas["teamCostState"], "restricted")
        self.assertIsNone(mensalistas["teamCostTotal"])

    def test_api_restringe_documento_salario_e_custos_por_permissao(self):
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                61,
                telefone="85999999999",
                email="restrito@example.com",
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2200.00"),
                carga_horaria_mensal=Decimal("160.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        restrito = get_user_model().objects.create_user("servidor-restrito", password="senha")
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_servidor"),
        )
        client = Client()
        client.force_login(restrito)
        lista = client.get(reverse("caixa:api_servidores"))
        self.assertEqual(lista.status_code, 200)
        item = next(item for item in lista.json()["data"]["servers"] if item["id"] == mensalista.id)
        self.assertEqual(item["document"], mensalista.documento_mascarado)
        self.assertEqual(item["phone"], "")
        self.assertEqual(item["notes"], "")
        self.assertIsNone(item["monthlySalary"])
        self.assertIsNone(item["monthlyWorkloadHours"])
        self.assertEqual(client.get(reverse("caixa:api_custos_por_servidor")).status_code, 403)

    def test_edicao_sem_permissao_salarial_preserva_salario(self):
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                62,
                observacoes="Anotação confidencial",
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2300.00"),
                carga_horaria_mensal=Decimal("160.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        restrito = get_user_model().objects.create_user("editor-sem-salario", password="senha")
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_servidor"),
            Permission.objects.get(codename="change_servidor"),
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(restrito)
        csrf = client.get(reverse("caixa:api_auth_csrf")).json()["csrfToken"]
        payload = self.payload(62)
        payload.update({
            "name": "Mensalista atualizado",
            "document": mensalista.documento_mascarado,
            "linkType": "MENSALISTA",
            "monthlySalary": None,
            "monthlyWorkloadHours": "300.00",
            "workloadEffectiveDate": "2026-08-01",
        })
        resposta = client.put(
            reverse("caixa:api_servidor_detalhe", args=[mensalista.id]),
            payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(resposta.status_code, 200, resposta.content)
        mensalista.refresh_from_db()
        self.assertEqual(mensalista.nome, "Mensalista atualizado")
        self.assertEqual(mensalista.salario_mensal, Decimal("2300.00"))
        self.assertEqual(mensalista.carga_horaria_mensal, Decimal("160.00"))
        self.assertEqual(
            HistoricoJornadaMensalServidor.objects.get(
                servidor=mensalista
            ).horas_mensais,
            Decimal("160.00"),
        )
        self.assertEqual(mensalista.observacoes, "Anotação confidencial")

    def test_salario_aparece_em_custo_fixo_sem_linha_editavel_duplicada(self):
        dados = self.dados_servidor(
            63,
            tipo_vinculo=Servidor.VINCULO_MENSALISTA,
            salario_mensal=Decimal("2400.00"),
        )
        dados.update(
            {
                "data_inicio_contrato": date(2026, 7, 1),
                "data_fim_contrato": None,
                "dia_pagamento_salario": 5,
                "data_autorizacao_custo_salarial": date(2026, 7, 1),
            }
        )
        mensalista = criar_servidor(
            dados=dados,
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        resposta = self.client.get(
            reverse("caixa:api_custos_fixos"),
            {"startDate": "2026-07-01", "endDate": "2026-07-31"},
        )
        self.assertEqual(resposta.status_code, 200)
        linhas = [
            item for item in resposta.json()["data"]["fixedCosts"]
            if item.get("serverId") == mensalista.id
        ]
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["plannedAmount"], "2400.00")
        self.assertEqual(linhas[0]["source"], "salaryHistory")
        self.assertTrue(linhas[0]["readOnly"])
        self.assertFalse(linhas[0]["canEdit"])
        self.assertEqual(linhas[0]["kind"], "occurrence")
        self.assertGreater(linhas[0]["id"], 0)

    def test_admin_nao_expoe_dados_protegidos_nem_contorna_exclusao(self):
        mensalista = criar_servidor(
            dados=self.dados_servidor(
                64,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2500.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        restrito = get_user_model().objects.create_user(
            "admin-servidor-restrito",
            password="senha",
            is_staff=True,
        )
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_servidor"),
            Permission.objects.get(codename="change_servidor"),
        )
        client = Client()
        client.force_login(restrito)
        detalhe = client.get(reverse("admin:caixa_servidor_change", args=[mensalista.id]))
        self.assertEqual(detalhe.status_code, 200)
        self.assertNotContains(detalhe, mensalista.documento)
        self.assertNotContains(detalhe, "2500.00")
        self.assertNotContains(detalhe, "2500,00")
        self.assertNotContains(detalhe, "Salario mensal")
        self.assertNotContains(detalhe, "deletelink")
        self.assertEqual(
            client.get(reverse("admin:caixa_servidor_history", args=[mensalista.id])).status_code,
            403,
        )

    def test_admin_nao_permite_excluir_participacao_fora_do_servico_de_dominio(self):
        participacao = self.participar(self.criar_diarista(65))
        restrito = get_user_model().objects.create_user(
            "admin-participacao-restrito",
            password="senha",
            is_staff=True,
        )
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_participacaoservidorevento"),
            Permission.objects.get(codename="delete_participacaoservidorevento"),
        )
        client = Client()
        client.force_login(restrito)

        listagem = client.get(reverse("admin:caixa_participacaoservidorevento_changelist"))
        self.assertEqual(listagem.status_code, 200)
        self.assertNotContains(listagem, "delete_selected")

        url_exclusao = reverse(
            "admin:caixa_participacaoservidorevento_delete",
            args=[participacao.id],
        )
        self.assertEqual(client.get(url_exclusao).status_code, 403)
        self.assertEqual(client.post(url_exclusao, {"post": "yes"}).status_code, 403)
        self.assertTrue(ParticipacaoServidorEvento.objects.filter(pk=participacao.id).exists())

    def test_servico_nao_vinculado_e_duplicidade_retornam_400(self):
        servidor = self.criar_diarista(32)
        url = reverse("caixa:api_participacoes_evento", args=[self.evento.id])
        base = {
            "serverId": servidor.id,
            "workedDays": [{"date": "2026-07-20", "hours": None}],
        }
        invalido = self.client.post(
            url,
            {**base, "serviceId": self.outro_servico.id},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(invalido.status_code, 400)
        for esperado in (201, 400):
            resposta = self.client.post(
                url,
                {**base, "serviceId": self.servico.id},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=self.csrf,
            )
            self.assertEqual(resposta.status_code, esperado)

    def test_busca_sensivel_depende_da_permissao_especifica(self):
        servidor = criar_servidor(
            dados=self.dados_servidor(
                80,
                telefone="85987654321",
                email="busca.sensivel@example.com",
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
        )
        restrito = get_user_model().objects.create_user(
            "busca-sem-dados-sensiveis",
            password="senha",
        )
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_servidor"),
        )
        client = Client()
        client.force_login(restrito)
        url = reverse("caixa:api_servidores")

        for busca in (servidor.documento, servidor.email, servidor.telefone):
            with self.subTest(busca=busca):
                resposta = client.get(url, {"search": busca})
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.json()["data"]["servers"], [])

        por_nome = client.get(url, {"search": "Servidor 80"})
        self.assertEqual(len(por_nome.json()["data"]["servers"]), 1)
        autorizado = self.client.get(url, {"search": servidor.email})
        self.assertEqual(autorizado.json()["data"]["servers"][0]["id"], servidor.id)

    def test_leitura_de_participacao_exige_permissoes_de_evento_e_participacao(self):
        participacao = self.participar(self.criar_diarista(81))
        usuario = get_user_model().objects.create_user(
            "leitor-participacao-restrito",
            password="senha",
        )
        usuario.user_permissions.add(
            Permission.objects.get(codename="view_evento"),
        )
        client = Client()
        client.force_login(usuario)
        lista = reverse("caixa:api_participacoes_evento", args=[self.evento.id])
        detalhe = reverse("caixa:api_participacao_detalhe", args=[participacao.id])

        self.assertEqual(client.get(lista).status_code, 403)
        self.assertEqual(client.get(detalhe).status_code, 403)
        self.assertEqual(
            client.get(reverse("caixa:api_participacao_detalhe", args=[999999])).status_code,
            403,
        )

        usuario.user_permissions.add(
            Permission.objects.get(codename="view_participacaoservidorevento"),
        )
        resposta_lista = client.get(lista)
        self.assertEqual(resposta_lista.status_code, 200)
        self.assertEqual(resposta_lista.json()["data"]["serverOptions"], [])
        self.assertEqual(client.get(detalhe).status_code, 200)
        self.assertEqual(
            client.post(lista, {}, content_type="application/json").status_code,
            403,
        )
        self.assertEqual(
            client.put(detalhe, {}, content_type="application/json").status_code,
            403,
        )
        self.assertEqual(client.delete(detalhe).status_code, 403)

    def test_restaurar_e_recalcular_exigem_permissao_de_gestao(self):
        participacao = self.participar(self.criar_diarista(82))
        usuario = get_user_model().objects.create_user(
            "especialista-sem-gestao",
            password="senha",
        )
        usuario.user_permissions.add(
            Permission.objects.get(codename="change_valor_distribuido_servidor"),
            Permission.objects.get(codename="recalculate_custos_servidor"),
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(usuario)
        csrf = client.get(reverse("caixa:api_auth_csrf")).json()["csrfToken"]

        restaurar = client.post(
            reverse(
                "caixa:api_restaurar_calculo_participacao",
                args=[participacao.id],
            ),
            HTTP_X_CSRFTOKEN=csrf,
        )
        recalcular = client.post(
            reverse(
                "caixa:api_recalcular_participacoes_evento",
                args=[self.evento.id],
            ),
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(restaurar.status_code, 403)
        self.assertEqual(recalcular.status_code, 403)

    def test_api_rejeita_servico_inativo_horas_negativas_e_manual_mensalista(self):
        diarista = self.criar_diarista(83)
        url = reverse("caixa:api_participacoes_evento", args=[self.evento.id])
        negativo = self.client.post(
            url,
            {
                "serverId": diarista.id,
                "serviceId": self.servico.id,
                "workedDays": [
                    {"date": "2026-07-20", "hours": "-1.00"},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(negativo.status_code, 400)
        self.assertIn("workedDays", negativo.json()["errors"])

        self.servico.ativo = False
        self.servico.save(update_fields=["ativo"])
        inativo = self.client.post(
            url,
            {
                "serverId": diarista.id,
                "serviceId": self.servico.id,
                "workedDays": [
                    {"date": "2026-07-20", "hours": None},
                ],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(inativo.status_code, 400)
        self.servico.ativo = True
        self.servico.save(update_fields=["ativo"])

        mensalista = criar_servidor(
            dados=self.dados_servidor(
                84,
                tipo_vinculo=Servidor.VINCULO_MENSALISTA,
                salario_mensal=Decimal("2800.00"),
            ),
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )
        participacao = self.participar(mensalista)
        manual = self.client.put(
            reverse("caixa:api_participacao_detalhe", args=[participacao.id]),
            {
                "serviceId": self.servico.id,
                "days": 1,
                "hours": "0.00",
                "finalAmount": "10.00",
                "editReason": "Não permitido",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        self.assertEqual(manual.status_code, 400)
        self.assertIn("finalAmount", manual.json()["errors"])

    def test_rotas_de_participacao_exigem_autenticacao(self):
        participacao = self.participar(self.criar_diarista(85))
        anonimo = Client()
        rotas_get = (
            reverse("caixa:api_participacoes_evento", args=[self.evento.id]),
            reverse("caixa:api_participacao_detalhe", args=[participacao.id]),
        )
        rotas_post = (
            reverse(
                "caixa:api_restaurar_calculo_participacao",
                args=[participacao.id],
            ),
            reverse(
                "caixa:api_recalcular_participacoes_evento",
                args=[self.evento.id],
            ),
        )

        for rota in rotas_get:
            self.assertEqual(anonimo.get(rota).status_code, 401)
        for rota in rotas_post:
            self.assertEqual(anonimo.post(rota).status_code, 401)

    def test_sessao_expoe_permissao_especifica_de_participacao(self):
        resposta = self.client.get(reverse("caixa:api_auth_session"))
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["user"]["canViewServerParticipations"])


class AtivacaoMensalistasCommandTests(ServidoresFixtureMixin, TenantAppTestCase):
    def criar_mensalista_pendente(self, indice=93, **overrides):
        dados = self.dados_servidor(
            indice,
            tipo_vinculo=Servidor.VINCULO_MENSALISTA,
            salario_mensal=Decimal("7654321.09"),
            data_inicio_contrato=date(2026, 7, 1),
            data_fim_contrato=None,
            dia_pagamento_salario=5,
            data_autorizacao_custo_salarial=None,
        )
        dados.update(overrides)
        return criar_servidor(
            dados=dados,
            servicos_ids=[self.servico.id],
            usuario=self.usuario,
            data_vigencia_salario=date(2026, 7, 1),
        )

    def test_dry_run_eh_read_only_e_nao_expoe_salario(self):
        servidor = self.criar_mensalista_pendente()
        saida = StringIO()
        call_command(
            "ativar_mensalistas_existentes",
            "--data-corte",
            "2026-07-01",
            "--servidor-id",
            str(servidor.pk),
            "--dry-run",
            stdout=saida,
        )
        servidor.refresh_from_db()
        self.assertIn("eligible=1", saida.getvalue())
        self.assertNotIn("7654321", saida.getvalue())
        self.assertIsNone(servidor.data_autorizacao_custo_salarial)
        self.assertFalse(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).exists()
        )
        self.assertFalse(AuditoriaCustoRecorrente.objects.exists())

    def test_escrita_exige_confirmacao_forte(self):
        servidor = self.criar_mensalista_pendente()
        with self.assertRaises(CommandError):
            call_command(
                "ativar_mensalistas_existentes",
                "--data-corte",
                "2026-07-01",
                "--servidor-id",
                str(servidor.pk),
                stdout=StringIO(),
            )
        servidor.refresh_from_db()
        self.assertIsNone(servidor.data_autorizacao_custo_salarial)
        self.assertFalse(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).exists()
        )

    def test_execucao_e_repeticao_sao_idempotentes_e_auditadas(self):
        servidor = self.criar_mensalista_pendente()
        argumentos = [
            "--data-corte",
            "2026-07-01",
            "--servidor-id",
            str(servidor.pk),
            "--confirmar",
            "ATIVAR_MENSALISTAS",
        ]
        primeira = StringIO()
        call_command(
            "ativar_mensalistas_existentes",
            *argumentos,
            stdout=primeira,
        )
        segunda = StringIO()
        call_command(
            "ativar_mensalistas_existentes",
            *argumentos,
            stdout=segunda,
        )

        servidor.refresh_from_db()
        self.assertEqual(
            servidor.data_autorizacao_custo_salarial,
            date(2026, 7, 1),
        )
        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(servidor=servidor).count(),
            1,
        )
        self.assertEqual(
            CustoFixo.objects.filter(
                plano_recorrente__servidor=servidor,
                competencia=date(2026, 7, 1),
            ).count(),
            1,
        )
        self.assertIn("activated=1", primeira.getvalue())
        self.assertIn("alreadyConfigured=1", segunda.getvalue())
        self.assertNotIn("7654321", primeira.getvalue() + segunda.getvalue())
        self.assertEqual(
            AuditoriaCustoRecorrente.objects.filter(
                tipo_evento=AuditoriaCustoRecorrente.TIPO_ATIVACAO,
            ).count(),
            2,
        )

    def test_candidato_sem_contrato_eh_invalido(self):
        servidor = self.criar_mensalista_pendente(
            indice=94,
            data_inicio_contrato=None,
            dia_pagamento_salario=None,
        )
        saida = StringIO()
        call_command(
            "ativar_mensalistas_existentes",
            "--data-corte",
            "2026-07-01",
            "--servidor-id",
            str(servidor.pk),
            "--dry-run",
            stdout=saida,
        )
        self.assertIn("invalid=1", saida.getvalue())
        self.assertIn("CONTRACT_START_NOT_CONFIGURED", saida.getvalue())


class ServidoresIsolamentoMultiTenantTests(MultiTenantTestCase):
    def test_novos_totais_de_custos_permanecem_isolados_por_schema(self):
        tenant_b, _ = self.create_tenant(
            "tenant_custos_servidores_b",
            "Tenant Custos Servidores B",
            "tenant-custos-servidores-b.localhost",
        )

        def criar_cenario(sufixo, salario, jornada):
            usuario = get_user_model().objects.create_superuser(
                username=f"custos-servidores-{sufixo}",
                email=f"{sufixo}@example.com",
                password="senha-segura",
            )
            servico = Servico.objects.create(
                nome=f"Serviço {sufixo}",
                codigo=f"servico-{sufixo}",
                diaria_padrao=Decimal("100.00"),
                valor_unitario=Decimal("100.00"),
                horas_base_diaria=8,
            )
            criar_servidor(
                dados={
                    "nome": f"Mensalista {sufixo}",
                    "tipo_documento": Servidor.TIPO_DOCUMENTO_CPF,
                    "documento": "12345678901",
                    "tipo_vinculo": Servidor.VINCULO_MENSALISTA,
                    "salario_mensal": Decimal(salario),
                    "carga_horaria_mensal": Decimal(jornada),
                    "data_inicio_contrato": date(2026, 7, 1),
                    "dia_pagamento_salario": 5,
                    "data_autorizacao_custo_salarial": date(2026, 7, 1),
                },
                servicos_ids=[servico.pk],
                usuario=usuario,
                data_vigencia_salario=date(2026, 7, 1),
                data_vigencia_jornada=date(2026, 7, 1),
            )
            return usuario

        with self.in_schema(self.primary_tenant.schema_name):
            usuario_a = criar_cenario("tenant-a", "1234.00", "160.00")
            resumo_a = custos_por_servidor(
                data_inicial=date(2026, 7, 1),
                data_final=date(2026, 7, 31),
                usuario=usuario_a,
            )["summary"]
            jornadas_a = list(
                HistoricoJornadaMensalServidor.objects.values_list(
                    "horas_mensais", flat=True
                )
            )

        with self.in_schema(tenant_b.schema_name):
            usuario_b = criar_cenario("tenant-b", "9876.00", "176.00")
            resumo_b = custos_por_servidor(
                data_inicial=date(2026, 7, 1),
                data_final=date(2026, 7, 31),
                usuario=usuario_b,
            )["summary"]
            jornadas_b = list(
                HistoricoJornadaMensalServidor.objects.values_list(
                    "horas_mensais", flat=True
                )
            )

        self.assertEqual(resumo_a["monthlySalaryTotal"], "1234.00")
        self.assertEqual(resumo_a["teamCostTotal"], "1234.00")
        self.assertEqual(resumo_b["monthlySalaryTotal"], "9876.00")
        self.assertEqual(resumo_b["teamCostTotal"], "9876.00")
        self.assertEqual(jornadas_a, [Decimal("160.00")])
        self.assertEqual(jornadas_b, [Decimal("176.00")])

    def test_documento_repetido_por_tenant_e_api_sem_vazamento(self):
        tenant_b, _ = self.create_tenant(
            "tenant_servidores_b",
            "Tenant Servidores B",
            "tenant-servidores-b.localhost",
        )
        dados_base = {
            "tipo_documento": Servidor.TIPO_DOCUMENTO_CPF,
            "documento": "12345678901",
            "tipo_vinculo": Servidor.VINCULO_DIARISTA,
            "salario_mensal": None,
        }

        with self.in_schema(self.primary_tenant.schema_name):
            usuario_a = get_user_model().objects.create_user(
                username="servidores-tenant-a",
                password="senha-segura",
            )
            usuario_a.user_permissions.add(
                Permission.objects.get(codename="view_servidor")
            )
            servico_a = Servico.objects.create(
                nome="Serviço Tenant A",
                codigo="servico-tenant-a",
                diaria_padrao=Decimal("100.00"),
                valor_unitario=Decimal("100.00"),
                horas_base_diaria=8,
            )
            servidor_a = criar_servidor(
                dados={**dados_base, "nome": "Servidor Exclusivo A"},
                servicos_ids=[servico_a.pk],
                usuario=usuario_a,
            )

        with self.in_schema(tenant_b.schema_name):
            usuario_b = get_user_model().objects.create_user(
                username="servidores-tenant-b",
                password="senha-segura",
            )
            servico_b = Servico.objects.create(
                nome="Serviço Tenant B",
                codigo="servico-tenant-b",
                diaria_padrao=Decimal("100.00"),
                valor_unitario=Decimal("100.00"),
                horas_base_diaria=8,
            )
            criar_servidor(
                dados={**dados_base, "nome": "Servidor Exclusivo B"},
                servicos_ids=[servico_b.pk],
                usuario=usuario_b,
            )
            servidor_apenas_b = criar_servidor(
                dados={
                    **dados_base,
                    "nome": "Outro Servidor Exclusivo B",
                    "documento": "10987654321",
                },
                servicos_ids=[servico_b.pk],
                usuario=usuario_b,
            )

        with self.in_schema(self.primary_tenant.schema_name):
            self.assertEqual(
                list(Servidor.objects.values_list("nome", flat=True)),
                ["Servidor Exclusivo A"],
            )
        client = self.client_for_tenant(self.primary_tenant)
        with self.in_schema(self.primary_tenant.schema_name):
            client.force_login(usuario_a)

        lista = client.get(reverse("caixa:api_servidores"))
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(
            [item["name"] for item in lista.json()["data"]["servers"]],
            ["Servidor Exclusivo A"],
        )
        detalhe_cruzado = client.get(
            reverse(
                "caixa:api_servidor_detalhe",
                kwargs={"pk": servidor_apenas_b.pk},
            )
        )
        self.assertEqual(detalhe_cruzado.status_code, 404)

        with self.in_schema(tenant_b.schema_name):
            self.assertEqual(
                Servidor.objects.filter(documento="12345678901").count(),
                1,
            )
        with self.in_schema(self.primary_tenant.schema_name):
            self.assertEqual(
                Servidor.objects.filter(documento="12345678901").count(),
                1,
            )
            self.assertEqual(Servidor.objects.get().pk, servidor_a.pk)
