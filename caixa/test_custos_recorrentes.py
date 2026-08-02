from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO
import json
from pathlib import Path
from threading import Barrier, Lock, Thread
from tempfile import TemporaryDirectory
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
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
from django.test.utils import CaptureQueriesContext
from django.db.models.deletion import ProtectedError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from tenancy.test_helpers import (
    MultiTenantTestCase,
    TenantAppTestCase,
    TenantTransactionTestCase,
)

from .models import LancamentoFinanceiro, ObrigacaoFinanceira
from .models_custo_fixo import (
    AuditoriaCustoRecorrente,
    CustoFixo,
    PlanoCustoRecorrente,
    RequisicaoIdempotenteRecorrencia,
)
from .models_servidores import HistoricoSalarialServidor, Servidor
from .selectors_obrigacoes import listar_obrigacoes_financeiras
from .selectors_lancamentos import filtrar_lancamentos_financeiros
from .selectors_obrigacoes_canonicas import (
    contar_obrigacoes_financeiras_canonicas,
)
from .security_salarios import ids_custos_salariais
from .services_auditoria_recorrencias import (
    expurgar_auditoria_recorrencias,
    registrar_evento_auditoria_recorrente,
)
from .services_custos_recorrentes import (
    adicionar_meses_competencia,
    atualizar_plano_recorrente,
    criar_plano_recorrente,
    data_vencimento_da_competencia,
    executar_com_retry_transacional,
    fim_do_mes,
    iterar_competencias,
    materializar_competencia,
    materializar_plano_competencia,
    projetar_custos_recorrentes,
    recuperar_competencias_ausentes,
)
from .services_idempotencia import (
    executar_requisicao_idempotente,
    expurgar_requisicoes_idempotentes_recorrencia,
)


class CustosRecorrentesTestBase(TenantAppTestCase):
    def setUp(self):
        super().setUp()
        self.hoje = timezone.localdate()
        self.competencia = self.hoje.replace(day=1)
        self.usuario = get_user_model().objects.create_user(
            username="financeiro-recorrencias",
            password="senha-segura",
        )
        self.usuario.user_permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "view_custofixo",
                    "add_custofixo",
                    "change_custofixo",
                    "view_planocustorecorrente",
                    "add_planocustorecorrente",
                    "change_planocustorecorrente",
                    "materialize_planocustorecorrente",
                    "view_salario_servidor",
                    "change_salario_servidor",
                    "view_lancamentofinanceiro",
                    "view_evento",
                    "view_parceladivida",
                    "view_receitaoperacional",
                ]
            )
        )
        self.client = Client()
        self.client.force_login(self.usuario)

    def dados_plano_comum(self, **overrides):
        dados = {
            "descricao": "Internet recorrente",
            "categoria": "internet",
            "origem": PlanoCustoRecorrente.ORIGEM_COMUM,
            "periodicidade": PlanoCustoRecorrente.PERIODICIDADE_MENSAL,
            "valor_previsto": Decimal("199.90"),
            "data_inicio": self.competencia,
            "data_fim": None,
            "dia_vencimento": 31,
            "data_autorizacao_materializacao": self.hoje,
            "ativo": True,
            "observacao": "Plano de teste",
        }
        dados.update(overrides)
        return dados

    def criar_plano_comum(self, *, materializar_atual=False, **overrides):
        return criar_plano_recorrente(
            dados=self.dados_plano_comum(**overrides),
            usuario=self.usuario,
            materializar_atual=materializar_atual,
        )

    def criar_servidor_salarial(self, **overrides):
        numero = Servidor.objects.count() + 1
        dados = {
            "nome": f"Mensalista {numero}",
            "tipo_documento": Servidor.TIPO_DOCUMENTO_CPF,
            "documento": f"900000000{numero:02d}",
            "ativo": True,
            "tipo_vinculo": Servidor.VINCULO_MENSALISTA,
            "salario_mensal": Decimal("3200.00"),
            "data_inicio_contrato": self.competencia,
            "data_fim_contrato": None,
            "dia_pagamento_salario": 5,
            "data_autorizacao_custo_salarial": self.hoje,
        }
        dados.update(overrides)
        servidor = Servidor(**dados)
        servidor.full_clean()
        servidor.save()
        return servidor

    def criar_historico(self, servidor, **overrides):
        dados = {
            "servidor": servidor,
            "servidor_nome_snapshot": servidor.nome,
            "servidor_id_snapshot": servidor.pk,
            "valor": servidor.salario_mensal,
            "data_inicio": self.competencia,
            "data_fim": None,
        }
        dados.update(overrides)
        historico = HistoricoSalarialServidor(**dados)
        historico.full_clean()
        historico.save()
        return historico

    def criar_plano_salarial(self, servidor, **overrides):
        dados = {
            "descricao": f"Salário — {servidor.nome}",
            "categoria": "salario",
            "origem": PlanoCustoRecorrente.ORIGEM_SALARIO,
            "periodicidade": PlanoCustoRecorrente.PERIODICIDADE_MENSAL,
            "valor_previsto": None,
            "data_inicio": servidor.data_inicio_contrato,
            "data_fim": servidor.data_fim_contrato,
            "dia_vencimento": servidor.dia_pagamento_salario,
            "data_autorizacao_materializacao": (
                servidor.data_autorizacao_custo_salarial
            ),
            "ativo": True,
            "observacao": "Histórico salarial",
            "servidor": servidor,
        }
        dados.update(overrides)
        return criar_plano_recorrente(
            dados=dados,
            usuario=self.usuario,
            materializar_atual=False,
        )[0]


class ConcorrenciaCustoRecorrentePostgreSQLTests(TenantTransactionTestCase):
    def setUp(self):
        super().setUp()
        if connection.vendor != "postgresql":
            self.skipTest("Concorrência transacional exige PostgreSQL.")
        self.hoje = timezone.localdate()
        self.competencia = self.hoje.replace(day=1)
        self.usuario = get_user_model().objects.create_user(
            username="concorrencia-recorrencias",
            password="senha-segura",
        )

    def _dados_plano(self, **overrides):
        dados = {
            "descricao": "Plano concorrente",
            "categoria": "internet",
            "origem": PlanoCustoRecorrente.ORIGEM_COMUM,
            "periodicidade": PlanoCustoRecorrente.PERIODICIDADE_MENSAL,
            "valor_previsto": Decimal("199.90"),
            "data_inicio": self.competencia,
            "data_fim": None,
            "dia_vencimento": 10,
            "data_autorizacao_materializacao": self.hoje,
            "ativo": True,
            "observacao": "",
        }
        dados.update(overrides)
        return dados

    def _executar_em_duas_conexoes(self, operacao):
        barreira = Barrier(2)
        mutex = Lock()
        resultados = []
        operacoes = (
            [operacao, operacao]
            if callable(operacao)
            else list(operacao)
        )

        def executar(operacao_thread):
            close_old_connections()
            connection.set_tenant(self.primary_tenant)
            try:
                barreira.wait(timeout=10)
                resultado = operacao_thread()
            except Exception as error:
                resultado = error
            finally:
                close_old_connections()
            with mutex:
                resultados.append(resultado)

        threads = [
            Thread(target=executar, args=(operacao_thread,))
            for operacao_thread in operacoes
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return resultados

    def test_duas_materializacoes_deixam_uma_ocorrencia_e_uma_obrigacao(self):
        plano, _ = criar_plano_recorrente(
            dados=self._dados_plano(),
            usuario=self.usuario,
            materializar_atual=False,
        )

        def materializar():
            plano_thread = PlanoCustoRecorrente.objects.get(pk=plano.pk)
            usuario_thread = get_user_model().objects.get(pk=self.usuario.pk)
            return materializar_plano_competencia(
                plano_thread,
                self.competencia,
                usuario=usuario_thread,
            )

        resultados = self._executar_em_duas_conexoes(materializar)

        self.assertCountEqual(
            [resultado["status"] for resultado in resultados],
            ["created", "alreadyMaterialized"],
        )
        self.assertEqual(
            CustoFixo.objects.filter(
                plano_recorrente=plano,
                competencia=self.competencia,
            ).count(),
            1,
        )
        self.assertEqual(
            ObrigacaoFinanceira.objects.filter(
                custo_fixo__plano_recorrente=plano,
                custo_fixo__competencia=self.competencia,
            ).count(),
            1,
        )

    def test_duas_renovacoes_da_mesma_serie_deixam_um_plano(self):
        pai = CustoFixo.objects.create(
            descricao="Série concorrente",
            categoria="internet",
            valor_previsto=Decimal("100.00"),
            data_vencimento=self.competencia,
            recorrente=True,
            quantidade_meses=2,
        )
        pai.gerar_recorrencias()
        inicio = adicionar_meses_competencia(self.competencia, 2)

        def renovar():
            pai_thread = CustoFixo.objects.get(pk=pai.pk)
            usuario_thread = get_user_model().objects.get(pk=self.usuario.pk)
            return criar_plano_recorrente(
                dados=self._dados_plano(
                    descricao="Renovação concorrente",
                    data_inicio=inicio,
                    custo_legado_referencia=pai_thread,
                ),
                usuario=usuario_thread,
                materializar_atual=False,
            )[0].pk

        resultados = self._executar_em_duas_conexoes(renovar)

        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(
                custo_legado_referencia=pai
            ).count(),
            1,
        )
        self.assertEqual(sum(isinstance(item, int) for item in resultados), 1)
        self.assertEqual(sum(isinstance(item, ValidationError) for item in resultados), 1)

    def test_deadlock_real_e_recuperado_por_retry_limitado(self):
        primeiro, _ = criar_plano_recorrente(
            dados=self._dados_plano(descricao="Lock A"),
            usuario=self.usuario,
            materializar_atual=False,
        )
        segundo, _ = criar_plano_recorrente(
            dados=self._dados_plano(descricao="Lock B"),
            usuario=self.usuario,
            materializar_atual=False,
        )
        barreira_deadlock = Barrier(2)
        tentativas = [0, 0]

        def operacao(indice, ordem):
            def executar():
                tentativas[indice] += 1
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL deadlock_timeout = '100ms'")
                    PlanoCustoRecorrente.objects.select_for_update().get(pk=ordem[0])
                    if tentativas[indice] == 1:
                        barreira_deadlock.wait(timeout=10)
                    PlanoCustoRecorrente.objects.select_for_update().get(pk=ordem[1])
                return "committed"

            return lambda: executar_com_retry_transacional(executar)

        resultados = self._executar_em_duas_conexoes(
            [
                operacao(0, (primeiro.pk, segundo.pk)),
                operacao(1, (segundo.pk, primeiro.pk)),
            ]
        )

        self.assertEqual(resultados, ["committed", "committed"])
        self.assertEqual(sorted(tentativas), [1, 2])

    def test_auditoria_concorrente_agrega_sem_duplicar(self):
        correlation_id = uuid.uuid4()

        def registrar():
            return registrar_evento_auditoria_recorrente(
                tipo_evento=AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
                origem=AuditoriaCustoRecorrente.ORIGEM_API,
                plano_id=None,
                competencia=self.competencia,
                status=AuditoriaCustoRecorrente.STATUS_BLOQUEADO,
                codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_BLOQUEIO_DOMINIO,
                correlation_id=correlation_id,
            ).pk

        resultados = self._executar_em_duas_conexoes(registrar)

        self.assertTrue(all(isinstance(item, int) for item in resultados))
        self.assertEqual(AuditoriaCustoRecorrente.objects.count(), 1)
        self.assertEqual(
            AuditoriaCustoRecorrente.objects.get().occurrences_count,
            2,
        )

    def test_mesma_chave_idempotente_concorrente_cria_um_plano(self):
        chave = uuid.uuid4()
        payload = {
            "description": "Plano por chave concorrente",
            "plannedAmount": "199.90",
        }

        def criar():
            usuario_thread = get_user_model().objects.get(pk=self.usuario.pk)

            def operacao():
                plano, _ = criar_plano_recorrente(
                    dados=self._dados_plano(
                        descricao="Plano por chave concorrente"
                    ),
                    usuario=usuario_thread,
                    materializar_atual=False,
                )
                return {"planId": plano.pk}, 201

            return executar_requisicao_idempotente(
                escopo="teste-plano-concorrente",
                chave=chave,
                payload=payload,
                ator=usuario_thread,
                operacao=operacao,
            )

        resultados = self._executar_em_duas_conexoes(criar)

        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(
                descricao="Plano por chave concorrente"
            ).count(),
            1,
        )
        self.assertEqual(
            RequisicaoIdempotenteRecorrencia.objects.filter(
                escopo="teste-plano-concorrente",
                chave=chave,
            ).count(),
            1,
        )
        self.assertCountEqual(
            [resultado[2] for resultado in resultados],
            [False, True],
        )


class PlanoCustoRecorrenteModelTests(CustosRecorrentesTestBase):
    def test_plano_comum_exige_valor_positivo(self):
        plano = PlanoCustoRecorrente(
            **self.dados_plano_comum(valor_previsto=Decimal("0.00"))
        )
        with self.assertRaises(ValidationError):
            plano.full_clean()

    def test_plano_comum_nao_aceita_categoria_salario(self):
        plano = PlanoCustoRecorrente(
            **self.dados_plano_comum(categoria="salario")
        )
        with self.assertRaises(ValidationError):
            plano.full_clean()

    def test_plano_salarial_nao_aceita_valor_copiado(self):
        servidor = self.criar_servidor_salarial()
        plano = PlanoCustoRecorrente(
            **self.dados_plano_comum(
                origem=PlanoCustoRecorrente.ORIGEM_SALARIO,
                categoria="salario",
                valor_previsto=Decimal("3200.00"),
                servidor=servidor,
            )
        )
        with self.assertRaises(ValidationError):
            plano.full_clean()

    def test_dia_de_vencimento_deve_estar_entre_um_e_trinta_e_um(self):
        for dia in (0, 32):
            with self.subTest(dia=dia):
                plano = PlanoCustoRecorrente(
                    **self.dados_plano_comum(dia_vencimento=dia)
                )
                with self.assertRaises(ValidationError):
                    plano.full_clean()

    def test_data_final_nao_pode_anteceder_inicio(self):
        plano = PlanoCustoRecorrente(
            **self.dados_plano_comum(
                data_fim=self.competencia - timedelta(days=1)
            )
        )
        with self.assertRaises(ValidationError):
            plano.full_clean()

    def test_campos_novos_do_custo_legado_ficam_neutros(self):
        custo = CustoFixo.objects.create(
            descricao="Legado",
            categoria="outro",
            valor_previsto=Decimal("10.00"),
            data_vencimento=self.hoje,
            recorrente=False,
            quantidade_meses=1,
        )
        self.assertIsNone(custo.plano_recorrente_id)
        self.assertIsNone(custo.competencia)
        self.assertEqual(custo.origem_recorrencia, "legado")

    def test_unicidade_plano_competencia_eh_protegida_no_banco(self):
        plano, _ = self.criar_plano_comum()
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        with self.assertRaises(IntegrityError):
            CustoFixo.objects.create(
                descricao="Duplicado",
                categoria="internet",
                valor_previsto=Decimal("199.90"),
                data_vencimento=self.hoje,
                recorrente=False,
                quantidade_meses=1,
                plano_recorrente=plano,
                competencia=self.competencia,
                origem_recorrencia="plano",
            )

    def test_renovacao_exige_encerramento_do_plano_anterior(self):
        anterior, _ = self.criar_plano_comum()
        with self.assertRaises(ValidationError):
            self.criar_plano_comum(
                data_inicio=adicionar_meses_competencia(self.competencia, 1),
                plano_renovado=anterior,
            )

    def test_renovacao_nao_pode_sobrepor_vigencia(self):
        anterior, _ = self.criar_plano_comum(data_fim=fim_do_mes(self.competencia))
        with self.assertRaises(ValidationError):
            self.criar_plano_comum(
                data_inicio=self.competencia,
                plano_renovado=anterior,
            )

    def test_renovacao_posterior_eh_valida(self):
        anterior, _ = self.criar_plano_comum(data_fim=fim_do_mes(self.competencia))
        renovacao, _ = self.criar_plano_comum(
            data_inicio=adicionar_meses_competencia(self.competencia, 1),
            plano_renovado=anterior,
        )
        self.assertEqual(renovacao.plano_renovado_id, anterior.pk)

    def test_servidor_possui_um_unico_plano_salarial(self):
        servidor = self.criar_servidor_salarial()
        self.criar_plano_salarial(servidor)
        with self.assertRaises(ValidationError):
            self.criar_plano_salarial(servidor)

    def test_banco_rejeita_plano_salarial_sem_servidor(self):
        dados = self.dados_plano_comum(
            origem=PlanoCustoRecorrente.ORIGEM_SALARIO,
            categoria="salario",
            valor_previsto=None,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            PlanoCustoRecorrente.objects.bulk_create(
                [PlanoCustoRecorrente(**dados)]
            )

    def test_servidor_com_plano_salarial_nao_pode_ser_excluido(self):
        servidor = self.criar_servidor_salarial()
        plano = self.criar_plano_salarial(servidor)

        with self.assertRaises(ProtectedError):
            servidor.delete()

        plano.refresh_from_db()
        self.assertEqual(plano.servidor_id, servidor.pk)

    def test_plano_comum_nao_renova_custo_salarial(self):
        custo_salarial = CustoFixo.objects.create(
            descricao="Salário legado",
            categoria="salario",
            valor_previsto=Decimal("1000.00"),
            data_vencimento=fim_do_mes(self.competencia),
            recorrente=False,
            quantidade_meses=1,
            origem_recorrencia="salario",
        )
        with self.assertRaises(ValidationError):
            self.criar_plano_comum(
                data_inicio=adicionar_meses_competencia(self.competencia, 1),
                custo_legado_referencia=custo_salarial,
            )

    def test_renovacao_legada_considera_todos_os_filhos(self):
        pai = CustoFixo.objects.create(
            descricao="Série legada",
            categoria="internet",
            valor_previsto=Decimal("120.00"),
            data_vencimento=self.competencia,
            recorrente=True,
            quantidade_meses=12,
        )
        pai.gerar_recorrencias()

        with self.assertRaises(ValidationError):
            self.criar_plano_comum(
                data_inicio=adicionar_meses_competencia(self.competencia, 6),
                custo_legado_referencia=pai,
            )

    def test_referencia_por_filho_e_normalizada_para_raiz(self):
        pai = CustoFixo.objects.create(
            descricao="Série legada por filho",
            categoria="internet",
            valor_previsto=Decimal("120.00"),
            data_vencimento=self.competencia,
            recorrente=True,
            quantidade_meses=3,
        )
        pai.gerar_recorrencias()
        filho = pai.custos_filhos.order_by("data_vencimento").first()

        plano, _ = self.criar_plano_comum(
            data_inicio=adicionar_meses_competencia(self.competencia, 3),
            custo_legado_referencia=filho,
        )

        self.assertEqual(plano.custo_legado_referencia_id, pai.pk)

    def test_serie_legada_so_pode_originar_um_plano(self):
        pai = CustoFixo.objects.create(
            descricao="Série legada única",
            categoria="internet",
            valor_previsto=Decimal("120.00"),
            data_vencimento=self.competencia,
            recorrente=True,
            quantidade_meses=2,
        )
        pai.gerar_recorrencias()
        inicio = adicionar_meses_competencia(self.competencia, 2)
        self.criar_plano_comum(
            data_inicio=inicio,
            custo_legado_referencia=pai,
        )

        with self.assertRaises(ValidationError):
            self.criar_plano_comum(
                descricao="Segunda renovação incompatível",
                data_inicio=inicio,
                custo_legado_referencia=pai.custos_filhos.first(),
            )

    def test_exclusao_de_plano_materializado_preserva_ocorrencia(self):
        plano, _ = self.criar_plano_comum()
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        with self.assertRaises(ProtectedError):
            plano.delete()
        self.assertTrue(CustoFixo.objects.filter(plano_recorrente=plano).exists())


class ProjecaoCustoRecorrenteTests(CustosRecorrentesTestBase):
    def test_vencimento_trinta_e_um_usa_ultimo_dia_do_mes(self):
        fevereiro = date(2028, 2, 1)
        self.assertEqual(
            data_vencimento_da_competencia(fevereiro, 31),
            date(2028, 2, 29),
        )

    def test_projecao_nao_cria_custo_obrigacao_ou_lancamento(self):
        plano, _ = self.criar_plano_comum()
        resultado = projetar_custos_recorrentes(
            inicio=self.competencia,
            fim=fim_do_mes(adicionar_meses_competencia(self.competencia, 2)),
        )
        self.assertTrue(resultado["items"])
        self.assertEqual(CustoFixo.objects.count(), 0)
        self.assertEqual(ObrigacaoFinanceira.objects.count(), 0)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 0)

    def test_projecao_salarial_tem_quantidade_constante_de_consultas(self):
        for indice in range(100):
            servidor = self.criar_servidor_salarial(
                nome=f"Mensalista escala {indice:03d}",
                documento=f"8{indice:010d}",
            )
            self.criar_historico(servidor)
            self.criar_plano_salarial(servidor)

        fim = fim_do_mes(adicionar_meses_competencia(self.competencia, 23))
        with CaptureQueriesContext(connection) as consultas:
            resultado = projetar_custos_recorrentes(
                inicio=self.competencia,
                fim=fim,
            )

        self.assertEqual(len(resultado["items"]), 2400)
        selects = [
            consulta
            for consulta in consultas.captured_queries
            if consulta["sql"].lstrip().upper().startswith("SELECT")
        ]
        self.assertLessEqual(len(selects), 3)

    @override_settings(CUSTOS_RECORRENTES_HORIZONTE_MAXIMO_MESES=2)
    def test_plano_aberto_respeita_horizonte_maximo(self):
        self.criar_plano_comum()
        resultado = projetar_custos_recorrentes(
            inicio=self.competencia,
            fim=fim_do_mes(adicionar_meses_competencia(self.competencia, 8)),
        )
        self.assertTrue(resultado["period"]["truncatedByHorizon"])
        self.assertEqual(len(resultado["items"]), 2)

    def test_projecao_respeita_data_final(self):
        self.criar_plano_comum(data_fim=fim_do_mes(self.competencia))
        resultado = projetar_custos_recorrentes(
            inicio=self.competencia,
            fim=fim_do_mes(adicionar_meses_competencia(self.competencia, 2)),
        )
        self.assertEqual(len(resultado["items"]), 1)

    def test_projecao_exclui_competencia_materializada(self):
        plano, _ = self.criar_plano_comum()
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        resultado = projetar_custos_recorrentes(
            inicio=self.competencia,
            fim=fim_do_mes(self.competencia),
        )
        self.assertEqual(resultado["items"], [])

    def test_projecao_nao_entra_em_pendente(self):
        self.criar_plano_comum()
        item = projetar_custos_recorrentes(
            inicio=self.competencia,
            fim=fim_do_mes(self.competencia),
        )["items"][0]
        self.assertEqual(item["pendingPaymentAmount"], "0.00")
        self.assertEqual(item["plannedAmount"], "0.00")
        self.assertFalse(item["canPay"])

    def test_competencia_anterior_a_criacao_fica_bloqueada(self):
        self.criar_plano_comum(
            data_inicio=adicionar_meses_competencia(self.competencia, -2),
            data_autorizacao_materializacao=adicionar_meses_competencia(
                self.competencia,
                -2,
            ),
        )
        item = projetar_custos_recorrentes(
            inicio=adicionar_meses_competencia(self.competencia, -1),
            fim=fim_do_mes(adicionar_meses_competencia(self.competencia, -1)),
        )["items"][0]
        self.assertEqual(item["status"], "blocked")
        self.assertEqual(item["blockedReason"], "beforePlanCreation")

    def test_edicao_do_plano_altera_so_projecao_futura(self):
        plano, _ = self.criar_plano_comum()
        criado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        atualizar_plano_recorrente(
            plano,
            dados={"valor_previsto": Decimal("299.90")},
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=criado["fixedCostId"])
        futuro = adicionar_meses_competencia(self.competencia, 1)
        item = projetar_custos_recorrentes(
            inicio=futuro,
            fim=fim_do_mes(futuro),
        )["items"][0]
        self.assertEqual(custo.valor_previsto, Decimal("199.90"))
        self.assertEqual(item["projectedAmount"], "299.90")


class MaterializacaoCustoRecorrenteTests(CustosRecorrentesTestBase):
    def test_competencia_atual_autorizada_cria_ocorrencia_fisica(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        self.assertEqual(resultado["status"], "created")
        self.assertEqual(custo.plano_recorrente_id, plano.pk)
        self.assertEqual(custo.competencia, self.competencia)

    def test_materializacao_cria_obrigacao_canonica(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertTrue(
            ObrigacaoFinanceira.objects.filter(
                custo_fixo_id=resultado["fixedCostId"]
            ).exists()
        )

    def test_materializacao_nao_cria_fco_sem_pagamento(self):
        plano, _ = self.criar_plano_comum()
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_execucao_repetida_eh_idempotente(self):
        plano, _ = self.criar_plano_comum()
        primeiro = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        segundo = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(primeiro["status"], "created")
        self.assertEqual(segundo["status"], "alreadyMaterialized")
        self.assertEqual(CustoFixo.objects.count(), 1)

    def test_dry_run_nao_grava_nada(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
            dry_run=True,
        )
        self.assertEqual(resultado["status"], "wouldCreate")
        self.assertEqual(CustoFixo.objects.count(), 0)

    def test_plano_inativo_fica_bloqueado(self):
        plano, _ = self.criar_plano_comum(ativo=False)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "inactive")

    def test_competencia_futura_nao_materializa_antecipadamente(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            adicionar_meses_competencia(self.competencia, 1),
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "futureCompetence")

    def test_autorizacao_futura_no_mes_bloqueia_antes_do_dia(self):
        plano, _ = self.criar_plano_comum(
            data_autorizacao_materializacao=self.hoje + timedelta(days=1)
        )
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "beforeAuthorization")

    def test_materializacao_em_lote_resume_resultados(self):
        self.criar_plano_comum()
        resultado = materializar_competencia(
            competencia=self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["counts"]["created"], 1)
        self.assertEqual(resultado["counts"]["blocked"], 0)

    def test_comando_dry_run_exibe_resumo_sem_gravar(self):
        self.criar_plano_comum()
        saida = StringIO()
        call_command(
            "materializar_custos_recorrentes",
            "--dry-run",
            stdout=saida,
        )
        self.assertIn("criaria=1", saida.getvalue())
        self.assertEqual(CustoFixo.objects.count(), 0)

    def test_comando_dry_run_nao_expoe_valor_salarial(self):
        sentinela = Decimal("9876543.21")
        servidor = self.criar_servidor_salarial(salario_mensal=sentinela)
        self.criar_historico(servidor, valor=sentinela)
        self.criar_plano_salarial(servidor)
        saida = StringIO()

        call_command(
            "materializar_custos_recorrentes",
            "--competencia",
            self.competencia.strftime("%Y-%m"),
            "--dry-run",
            stdout=saida,
        )

        self.assertNotIn("9876543", saida.getvalue())
        self.assertNotIn("9876543.21", saida.getvalue())

    def test_comando_rejeita_competencia_invalida(self):
        with self.assertRaises(Exception):
            call_command(
                "materializar_custos_recorrentes",
                "--competencia",
                "2026-13",
            )

    def test_competencia_perdida_pode_ser_recuperada_depois(self):
        anterior = adicionar_meses_competencia(self.competencia, -1)
        plano, _ = self.criar_plano_comum(
            data_inicio=anterior,
            data_autorizacao_materializacao=anterior,
        )
        PlanoCustoRecorrente.objects.filter(pk=plano.pk).update(
            criado_em=timezone.now() - timedelta(days=70)
        )
        plano.refresh_from_db()
        resultado = materializar_plano_competencia(
            plano,
            anterior,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["status"], "created")
        self.assertEqual(
            CustoFixo.objects.get(pk=resultado["fixedCostId"]).competencia,
            anterior,
        )

    def test_recuperacao_padrao_materializa_todos_os_meses_ausentes(self):
        inicio = adicionar_meses_competencia(self.competencia, -6)
        plano, _ = self.criar_plano_comum(
            data_inicio=inicio,
            data_autorizacao_materializacao=inicio,
        )
        PlanoCustoRecorrente.objects.filter(pk=plano.pk).update(
            criado_em=timezone.make_aware(datetime.combine(inicio, time.min))
        )
        plano.refresh_from_db()

        resultado = recuperar_competencias_ausentes(
            competencia_limite=self.competencia,
            usuario=self.usuario,
            planos=PlanoCustoRecorrente.objects.filter(pk=plano.pk),
        )

        self.assertEqual(resultado["counts"]["created"], 7)
        self.assertEqual(
            list(
                CustoFixo.objects.filter(plano_recorrente=plano)
                .order_by("competencia")
                .values_list("competencia", flat=True)
            ),
            list(iterar_competencias(inicio, self.competencia)),
        )

    def test_recuperacao_preserva_existentes_e_cria_somente_ausentes(self):
        inicio = adicionar_meses_competencia(self.competencia, -3)
        plano, _ = self.criar_plano_comum(
            data_inicio=inicio,
            data_autorizacao_materializacao=inicio,
        )
        PlanoCustoRecorrente.objects.filter(pk=plano.pk).update(
            criado_em=timezone.make_aware(datetime.combine(inicio, time.min))
        )
        plano.refresh_from_db()
        existente = adicionar_meses_competencia(inicio, 1)
        materializar_plano_competencia(
            plano,
            existente,
            usuario=self.usuario,
        )

        resultado = recuperar_competencias_ausentes(
            competencia_limite=self.competencia,
            usuario=self.usuario,
            planos=PlanoCustoRecorrente.objects.filter(pk=plano.pk),
        )

        self.assertEqual(resultado["counts"]["created"], 3)
        self.assertEqual(resultado["counts"]["alreadyMaterialized"], 1)
        self.assertEqual(CustoFixo.objects.filter(plano_recorrente=plano).count(), 4)

    def test_recuperacao_repetida_dez_vezes_nao_duplica(self):
        inicio = adicionar_meses_competencia(self.competencia, -2)
        plano, _ = self.criar_plano_comum(
            data_inicio=inicio,
            data_autorizacao_materializacao=inicio,
        )
        PlanoCustoRecorrente.objects.filter(pk=plano.pk).update(
            criado_em=timezone.make_aware(datetime.combine(inicio, time.min))
        )

        for _ in range(10):
            recuperar_competencias_ausentes(
                competencia_limite=self.competencia,
                usuario=self.usuario,
                planos=PlanoCustoRecorrente.objects.filter(pk=plano.pk),
            )

        self.assertEqual(CustoFixo.objects.filter(plano_recorrente=plano).count(), 3)
        self.assertEqual(
            ObrigacaoFinanceira.objects.filter(custo_fixo__plano_recorrente=plano).count(),
            3,
        )

    def test_api_recuperacao_exige_modo_e_limite_explicitos(self):
        url = reverse("caixa:api_materializar_custos_recorrentes")
        sem_competencia = self.client.post(
            url,
            {"dryRun": True},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(sem_competencia.status_code, 400)

        sem_limite = self.client.post(
            url,
            {"recoverMissing": True, "dryRun": True},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(sem_limite.status_code, 400)

    def test_edicao_do_plano_preserva_ocorrencia_paga(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        CustoFixo.objects.filter(pk=resultado["fixedCostId"]).update(
            valor_pago=Decimal("199.90"),
            status="pago",
        )
        atualizar_plano_recorrente(
            plano,
            dados={"valor_previsto": Decimal("500.00")},
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        self.assertEqual(custo.valor_previsto, Decimal("199.90"))
        self.assertEqual(custo.valor_pago, Decimal("199.90"))
        self.assertEqual(custo.status, "pago")

    def test_edicao_do_plano_preserva_ocorrencia_parcial(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        CustoFixo.objects.filter(pk=resultado["fixedCostId"]).update(
            valor_pago=Decimal("50.00"),
            status="parcial",
        )
        atualizar_plano_recorrente(
            plano,
            dados={"valor_previsto": Decimal("500.00")},
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        self.assertEqual(custo.valor_previsto, Decimal("199.90"))
        self.assertEqual(custo.valor_pago, Decimal("50.00"))
        self.assertEqual(custo.status, "parcial")

    def test_desativacao_do_plano_preserva_ocorrencia_e_obrigacao(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        atualizar_plano_recorrente(
            plano,
            dados={"ativo": False},
            usuario=self.usuario,
        )
        self.assertTrue(
            CustoFixo.objects.filter(pk=resultado["fixedCostId"]).exists()
        )
        self.assertTrue(
            ObrigacaoFinanceira.objects.filter(
                custo_fixo_id=resultado["fixedCostId"]
            ).exists()
        )

    def test_resumo_em_lote_distingue_ignorados_bloqueados_e_erros(self):
        plano, _ = self.criar_plano_comum(ativo=False)
        resultado = materializar_competencia(
            competencia=self.competencia,
            usuario=self.usuario,
            planos=PlanoCustoRecorrente.objects.filter(pk=plano.pk),
        )
        self.assertEqual(resultado["counts"]["ignored"], 1)
        self.assertEqual(resultado["counts"]["blocked"], 0)
        self.assertEqual(resultado["counts"]["error"], 0)


class MaterializacaoSalarialTests(CustosRecorrentesTestBase):
    def test_salario_integral_materializa_valor_do_historico(self):
        servidor = self.criar_servidor_salarial()
        historico = self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        self.assertEqual(custo.valor_previsto, historico.valor)
        self.assertEqual(custo.historico_salarial_id, historico.pk)
        self.assertEqual(custo.origem_recorrencia, "salario")

    def test_vigencia_salarial_no_meio_do_mes_bloqueia_sem_rateio(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(
            servidor,
            data_inicio=self.competencia + timedelta(days=10),
        )
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "partialSalaryPeriod")
        self.assertEqual(CustoFixo.objects.count(), 0)

    def test_inicio_de_contrato_no_meio_do_mes_bloqueia_sem_rateio(self):
        servidor = self.criar_servidor_salarial(
            data_inicio_contrato=self.competencia + timedelta(days=10)
        )
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "partialContractMonth")

    def test_fim_de_contrato_no_meio_do_mes_bloqueia_sem_rateio(self):
        servidor = self.criar_servidor_salarial(
            data_fim_contrato=self.competencia + timedelta(days=15)
        )
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "partialContractMonth")

    def test_diarista_nao_materializa_plano_salarial(self):
        servidor = self.criar_servidor_salarial()
        servidor.tipo_vinculo = Servidor.VINCULO_DIARISTA
        servidor.salario_mensal = None
        servidor.data_inicio_contrato = None
        servidor.dia_pagamento_salario = None
        servidor.data_autorizacao_custo_salarial = None
        servidor.save()
        plano = self.criar_plano_salarial(
            servidor,
            data_inicio=self.competencia,
            dia_vencimento=5,
            data_autorizacao_materializacao=self.hoje,
        )
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "notMonthlyServer")

    def test_salario_materializado_preserva_nome_snapshot(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        servidor.nome = "Nome alterado"
        servidor.save()
        self.assertNotEqual(custo.servidor_nome_snapshot, servidor.nome)

    def test_projecao_salarial_futura_usa_historico_sem_criar_pendente(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        self.criar_plano_salarial(servidor)
        futuro = adicionar_meses_competencia(self.competencia, 1)
        item = projetar_custos_recorrentes(
            inicio=futuro,
            fim=fim_do_mes(futuro),
        )["items"][0]
        self.assertEqual(item["projectedAmount"], "3200.00")
        self.assertEqual(item["pendingPaymentAmount"], "0.00")
        self.assertEqual(item["source"], "salaryHistory")

    def test_corte_salarial_impede_competencia_anterior(self):
        anterior = adicionar_meses_competencia(self.competencia, -1)
        servidor = self.criar_servidor_salarial(
            data_inicio_contrato=anterior,
            data_autorizacao_custo_salarial=self.competencia,
        )
        self.criar_historico(servidor, data_inicio=anterior)
        plano = self.criar_plano_salarial(servidor)
        PlanoCustoRecorrente.objects.filter(pk=plano.pk).update(
            criado_em=timezone.now() - timedelta(days=100)
        )
        plano.refresh_from_db()
        resultado = materializar_plano_competencia(
            plano,
            anterior,
            usuario=self.usuario,
        )
        self.assertEqual(resultado["reason"], "beforeAuthorization")
        self.assertFalse(CustoFixo.objects.exists())

    def test_reajuste_salarial_afeta_projecao_futura(self):
        servidor = self.criar_servidor_salarial()
        atual = self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        futuro = adicionar_meses_competencia(self.competencia, 1)
        atual.data_fim = futuro - timedelta(days=1)
        atual.save(update_fields=["data_fim"])
        self.criar_historico(
            servidor,
            data_inicio=futuro,
            valor=Decimal("4100.00"),
        )
        item = projetar_custos_recorrentes(
            inicio=futuro,
            fim=fim_do_mes(futuro),
            planos=PlanoCustoRecorrente.objects.filter(pk=plano.pk),
        )["items"][0]
        self.assertEqual(item["projectedAmount"], "4100.00")

    def test_descricao_salarial_materializada_identifica_competencia(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        self.assertTrue(custo.descricao.endswith(f"{self.competencia:%m/%Y}"))


class CustosRecorrentesApiESegurancaTests(CustosRecorrentesTestBase):
    def post_custo_recorrente(self, **overrides):
        payload = {
            "description": "Licença mensal",
            "category": "sistema",
            "plannedAmount": "150.00",
            "paidAmount": "0.00",
            "dueDate": self.hoje.isoformat(),
            "status": "pendente",
            "manuallySettled": False,
            "isActive": True,
            "isRecurring": True,
            "monthsCount": 12,
            "openEnded": True,
            "authorizedMaterializationDate": self.hoje.isoformat(),
        }
        payload.update(overrides)
        return self.client.post(
            reverse("caixa:api_custos_fixos"),
            payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

    def test_api_novo_recorrente_cria_plano_e_uma_ocorrencia_atual(self):
        resposta = self.post_custo_recorrente()
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(PlanoCustoRecorrente.objects.count(), 1)
        self.assertEqual(CustoFixo.objects.count(), 1)
        self.assertIsNotNone(resposta.json()["data"]["recurringPlan"])

    def test_api_novo_recorrente_nao_expande_meses_futuros(self):
        self.post_custo_recorrente(monthsCount=24)
        self.assertEqual(CustoFixo.objects.count(), 1)

    def test_api_plano_futuro_nao_cria_ocorrencia(self):
        futuro = adicionar_meses_competencia(self.competencia, 1)
        resposta = self.post_custo_recorrente(
            dueDate=futuro.isoformat(),
            authorizedMaterializationDate=futuro.isoformat(),
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(CustoFixo.objects.count(), 0)
        self.assertIsNone(resposta.json()["data"]["fixedCost"])

    def test_api_lista_separa_totais_materializados_e_projetados(self):
        self.post_custo_recorrente()
        CustoFixo.objects.update(
            valor_pago=Decimal("50.00"),
            status="parcial",
        )
        futuro = adicionar_meses_competencia(self.competencia, 1)
        resposta = self.client.get(
            reverse("caixa:api_custos_fixos"),
            {
                "startDate": self.competencia.isoformat(),
                "endDate": fim_do_mes(futuro).isoformat(),
            },
        )
        resumo = resposta.json()["data"]["summary"]
        self.assertEqual(resumo["materializedPlannedAmount"], "150.00")
        self.assertEqual(resumo["realizedAmount"], "50.00")
        self.assertEqual(resumo["pendingPaymentAmount"], "100.00")
        self.assertEqual(resumo["projectedAmount"], "150.00")
        self.assertEqual(resumo["forecastAmount"], "250.00")

    def test_api_projecao_exige_periodo_explicito(self):
        resposta = self.client.get(
            reverse("caixa:api_projecoes_custos_recorrentes")
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_plano_comum_exige_corte_explicito(self):
        resposta = self.client.post(
            reverse("caixa:api_planos_custos_recorrentes"),
            {
                "description": "Plano sem corte",
                "category": "outro",
                "plannedAmount": "10.00",
                "startDate": self.competencia.isoformat(),
                "dueDay": 5,
            },
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(resposta.status_code, 400)

    def test_mutacoes_recorrentes_rejeitam_corpo_nao_json_e_expoem_header(self):
        plano_url = reverse("caixa:api_planos_custos_recorrentes")
        chave = str(uuid.uuid4())
        for content_type in (
            "text/plain",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ):
            with self.subTest(content_type=content_type):
                resposta = self.client.post(
                    plano_url,
                    {"description": "ignorar"},
                    content_type=content_type,
                    HTTP_IDEMPOTENCY_KEY=chave,
                )
                self.assertEqual(resposta.status_code, 415)
                self.assertEqual(resposta.headers["Idempotency-Replayed"], "false")
                self.assertIn(
                    "Idempotency-Replayed",
                    resposta.headers["Access-Control-Expose-Headers"],
                )

        # O client de teste omite Content-Type para bytes com comprimento zero;
        # espaÃ§os exercitam a mesma ramificaÃ§Ã£o de corpo JSON vazio com o
        # header application/json efetivamente presente.
        for body in (b" ", b"{"):
            with self.subTest(body=body):
                resposta = self.client.post(
                    plano_url,
                    body,
                    content_type="application/json",
                    HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
                )
                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(resposta.headers["Idempotency-Replayed"], "false")

        plano, _ = self.criar_plano_comum()
        atualizacao = self.client.put(
            reverse("caixa:api_plano_custo_recorrente_detalhe", args=[plano.pk]),
            {"plannedAmount": "250.00"},
            content_type="text/plain",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(atualizacao.status_code, 415)
        self.assertEqual(atualizacao.headers["Idempotency-Replayed"], "false")

        materializacao = self.client.post(
            reverse("caixa:api_materializar_custos_recorrentes"),
            {"dryRun": True},
            content_type="text/plain",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(materializacao.status_code, 415)
        self.assertEqual(materializacao.headers["Idempotency-Replayed"], "false")

    def test_api_projecao_nao_oferece_pagamento_ou_edicao(self):
        self.criar_plano_comum()
        resposta = self.client.get(
            reverse("caixa:api_projecoes_custos_recorrentes"),
            {
                "startDate": self.competencia.isoformat(),
                "endDate": fim_do_mes(self.competencia).isoformat(),
            },
        )
        item = resposta.json()["data"]["items"][0]
        self.assertFalse(item["canPay"])
        self.assertFalse(item["canEdit"])
        self.assertTrue(item["readOnly"])

    def test_dashboard_sinaliza_custo_recorrente_ausente_ate_materializacao(self):
        plano, _ = self.criar_plano_comum()
        url = reverse("caixa:api_dashboard_financial_overview")
        filtros = {
            "startDate": self.competencia.isoformat(),
            "endDate": fim_do_mes(self.competencia).isoformat(),
        }
        antes = self.client.get(url, filtros)
        self.assertEqual(antes.status_code, 200)
        completude_antes = antes.json()["data"]["meta"][
            "financialCompleteness"
        ]
        self.assertTrue(completude_antes["assessed"])
        self.assertFalse(completude_antes["complete"])
        self.assertEqual(completude_antes["missingCount"], 1)
        self.assertEqual(
            completude_antes["reason"],
            "RECURRING_COSTS_NOT_MATERIALIZED",
        )

        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        depois = self.client.get(url, filtros)
        completude_depois = depois.json()["data"]["meta"][
            "financialCompleteness"
        ]
        self.assertTrue(completude_depois["complete"])
        self.assertEqual(completude_depois["missingCount"], 0)
        self.assertEqual(completude_depois["materializedCount"], 1)

    def test_completude_do_dashboard_nao_revela_plano_salarial_sem_permissao(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        self.criar_plano_salarial(servidor)
        restrito = get_user_model().objects.create_user(
            "dashboard-sem-salario"
        )
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_evento")
        )
        client = Client()
        client.force_login(restrito)
        resposta = client.get(
            reverse("caixa:api_dashboard_financial_overview"),
            {
                "startDate": self.competencia.isoformat(),
                "endDate": fim_do_mes(self.competencia).isoformat(),
            },
        )
        self.assertEqual(resposta.status_code, 200)
        completude = resposta.json()["data"]["meta"][
            "financialCompleteness"
        ]
        self.assertTrue(completude["excludedSalaryData"])
        self.assertTrue(completude["complete"])
        self.assertEqual(completude["expectedCount"], 0)
        self.assertEqual(completude["missingCount"], 0)

    def test_usuario_sem_permissao_salarial_nao_ve_custo_ou_total(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        restrito = get_user_model().objects.create_user("restrito-salario")
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_custofixo")
        )
        client = Client()
        client.force_login(restrito)
        resposta = client.get(
            reverse("caixa:api_custos_fixos"),
            {
                "startDate": self.competencia.isoformat(),
                "endDate": fim_do_mes(self.competencia).isoformat(),
            },
        )
        self.assertEqual(resposta.json()["data"]["fixedCosts"], [])
        self.assertEqual(
            resposta.json()["data"]["summary"]["materializedPlannedAmount"],
            "0.00",
        )

    def test_usuario_sem_permissao_salarial_recebe_404_no_detalhe(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        restrito = get_user_model().objects.create_user("restrito-detalhe")
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_custofixo")
        )
        client = Client()
        client.force_login(restrito)
        resposta = client.get(
            reverse(
                "caixa:api_custo_fixo_detalhe",
                args=[resultado["fixedCostId"]],
            )
        )
        self.assertEqual(resposta.status_code, 404)

    def test_obrigacoes_excluem_salario_antes_dos_totais(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        itens = listar_obrigacoes_financeiras({"_exclude_salary": True})
        self.assertEqual(itens, [])

    def test_ledger_sem_permissao_nao_revela_pagamento_salarial(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        custo.valor_pago = custo.valor_previsto
        custo.data_pagamento = self.hoje
        custo.save()
        restrito = get_user_model().objects.create_user("restrito-ledger")
        restrito.user_permissions.add(
            Permission.objects.get(codename="view_lancamentofinanceiro")
        )
        client = Client()
        client.force_login(restrito)
        resposta = client.get(reverse("caixa:api_lancamentos_financeiros"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["data"]["items"], [])
        self.assertEqual(resposta.json()["data"]["summary"]["outflowAmount"], 0.0)

    def test_categoria_salario_direta_exige_permissao_salarial(self):
        restrito = get_user_model().objects.create_user("restrito-criacao")
        restrito.user_permissions.add(
            Permission.objects.get(codename="add_custofixo")
        )
        client = Client()
        client.force_login(restrito)
        resposta = client.post(
            reverse("caixa:api_custos_fixos"),
            {
                "description": "Salário manual",
                "category": "salario",
                "plannedAmount": "1000.00",
                "paidAmount": "0.00",
                "dueDate": self.hoje.isoformat(),
                "status": "pendente",
                "isRecurring": False,
                "monthsCount": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_materializacao_manual_exige_permissao_explicita(self):
        permissao = Permission.objects.get(
            codename="materialize_planocustorecorrente"
        )
        self.usuario.user_permissions.remove(permissao)
        url = reverse("caixa:api_materializar_custos_recorrentes")
        negada = self.client.post(
            url,
            {"competence": self.competencia.isoformat(), "dryRun": True},
            content_type="application/json",
        )
        self.assertEqual(negada.status_code, 403)
        self.usuario.user_permissions.add(permissao)
        autorizada = self.client.post(
            url,
            {"competence": self.competencia.isoformat(), "dryRun": True},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(autorizada.status_code, 200)

    def test_ocorrencia_salarial_rejeita_edicao_direta(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        resposta = self.client.put(
            reverse(
                "caixa:api_custo_fixo_detalhe",
                args=[resultado["fixedCostId"]],
            ),
            {},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("derivada", resposta.json()["errors"]["detail"][0])

    def test_usuario_autorizado_ve_salario_como_ocorrencia_somente_leitura(self):
        servidor = self.criar_servidor_salarial()
        self.criar_historico(servidor)
        plano = self.criar_plano_salarial(servidor)
        materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        resposta = self.client.get(
            reverse("caixa:api_custos_fixos"),
            {
                "startDate": self.competencia.isoformat(),
                "endDate": fim_do_mes(self.competencia).isoformat(),
            },
        )
        item = resposta.json()["data"]["fixedCosts"][0]
        self.assertEqual(item["origin"], "salario")
        self.assertTrue(item["readOnly"])
        self.assertFalse(item["canEdit"])

    def test_referencia_salarial_oculta_parece_inexistente(self):
        custo_salarial = CustoFixo.objects.create(
            descricao="Salário confidencial",
            categoria="salario",
            valor_previsto=Decimal("1000.00"),
            data_vencimento=self.hoje,
            recorrente=False,
            quantidade_meses=1,
            origem_recorrencia="salario",
        )
        restrito = get_user_model().objects.create_user("restrito-referencia")
        restrito.user_permissions.add(
            Permission.objects.get(codename="add_custofixo"),
            Permission.objects.get(codename="add_planocustorecorrente"),
        )
        client = Client()
        client.force_login(restrito)
        payload = {
            "description": "Renovação comum",
            "category": "outro",
            "plannedAmount": "50.00",
            "startDate": adicionar_meses_competencia(
                self.competencia,
                1,
            ).isoformat(),
            "dueDay": 5,
            "authorizedMaterializationDate": self.hoje.isoformat(),
        }
        url = reverse("caixa:api_planos_custos_recorrentes")
        oculto = client.post(
            url,
            {**payload, "legacyFixedCostId": custo_salarial.pk},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        inexistente = client.post(
            url,
            {**payload, "legacyFixedCostId": custo_salarial.pk + 9999},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(oculto.status_code, 400)
        self.assertEqual(
            oculto.json()["errors"]["legacyFixedCostId"],
            inexistente.json()["errors"]["legacyFixedCostId"],
        )

    def test_criacao_de_plano_e_idempotente_por_chave_e_payload(self):
        url = reverse("caixa:api_planos_custos_recorrentes")
        payload = {
            "description": "Plano idempotente",
            "category": "internet",
            "plannedAmount": "88.00",
            "startDate": self.competencia.isoformat(),
            "dueDay": 10,
            "authorizedMaterializationDate": self.hoje.isoformat(),
        }
        chave = str(uuid.uuid4())

        primeira = self.client.post(
            url,
            payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )
        segunda = self.client.post(
            url,
            payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(segunda.headers["Idempotency-Replayed"], "true")
        self.assertEqual(primeira.json(), segunda.json())
        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(
                descricao="Plano idempotente"
            ).count(),
            1,
        )
        self.assertEqual(RequisicaoIdempotenteRecorrencia.objects.count(), 1)

    def test_reutilizar_chave_com_payload_diferente_retorna_400(self):
        url = reverse("caixa:api_planos_custos_recorrentes")
        payload = {
            "description": "Plano idempotente conflitante",
            "category": "internet",
            "plannedAmount": "88.00",
            "startDate": self.competencia.isoformat(),
            "dueDay": 10,
            "authorizedMaterializationDate": self.hoje.isoformat(),
        }
        chave = str(uuid.uuid4())
        primeira = self.client.post(
            url,
            payload,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )
        conflito = self.client.post(
            url,
            {**payload, "plannedAmount": "99.00"},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(conflito.status_code, 400)
        self.assertEqual(
            PlanoCustoRecorrente.objects.filter(
                descricao="Plano idempotente conflitante"
            ).count(),
            1,
        )

    def test_atualizacao_de_plano_exige_chave_e_reproduz_resposta(self):
        plano, _ = self.criar_plano_comum()
        url = reverse(
            "caixa:api_plano_custo_recorrente_detalhe",
            args=[plano.pk],
        )
        sem_chave = self.client.put(
            url,
            {"plannedAmount": "250.00"},
            content_type="application/json",
        )
        self.assertEqual(sem_chave.status_code, 400)
        chave = str(uuid.uuid4())
        primeira = self.client.put(
            url,
            {"plannedAmount": "250.00"},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )
        repetida = self.client.put(
            url,
            {"plannedAmount": "250.00"},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )
        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(repetida.status_code, 200)
        self.assertEqual(repetida.headers["Idempotency-Replayed"], "true")
        self.assertEqual(primeira.json(), repetida.json())
        plano.refresh_from_db()
        self.assertEqual(plano.valor_previsto, Decimal("250.00"))

    def test_materializacao_exige_chave_idempotente(self):
        resposta = self.client.post(
            reverse("caixa:api_materializar_custos_recorrentes"),
            {"competence": self.competencia.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Idempotency-Key", resposta.json()["errors"])

    def test_permissao_de_custo_fixo_nao_concede_acesso_a_planos(self):
        usuario = get_user_model().objects.create_user("somente-custo-fixo")
        usuario.user_permissions.add(
            Permission.objects.get(codename="view_custofixo"),
            Permission.objects.get(codename="add_custofixo"),
        )
        client = Client()
        client.force_login(usuario)
        url = reverse("caixa:api_planos_custos_recorrentes")
        payload = {
            "description": "Plano sem permissão própria",
            "category": "internet",
            "plannedAmount": "10.00",
            "startDate": self.competencia.isoformat(),
            "dueDay": 5,
            "authorizedMaterializationDate": self.hoje.isoformat(),
        }

        self.assertEqual(client.get(url).status_code, 403)
        self.assertEqual(
            client.post(
                url,
                payload,
                content_type="application/json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            ).status_code,
            403,
        )
        self.assertFalse(
            PlanoCustoRecorrente.objects.filter(
                descricao="Plano sem permissão própria"
            ).exists()
        )

    def test_lista_de_planos_expoe_capacidades_especificas_do_usuario(self):
        usuario = get_user_model().objects.create_user("somente-consulta-planos")
        usuario.user_permissions.add(
            Permission.objects.get(codename="view_planocustorecorrente")
        )
        client = Client()
        client.force_login(usuario)

        resposta = client.get(
            reverse("caixa:api_planos_custos_recorrentes")
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.json()["data"]["permissions"],
            {
                "canCreate": False,
                "canUpdate": False,
                "canMaterialize": False,
            },
        )

    def test_falha_inesperada_retorna_500_sem_mensagem_interna(self):
        self.criar_plano_comum()
        sentinela = "SALARIO-SENTINELA-9876.54"
        with patch(
            "caixa.views_planos_custos_recorrentes_api.materializar_competencia",
            side_effect=RuntimeError(sentinela),
        ):
            resposta = self.client.post(
                reverse("caixa:api_materializar_custos_recorrentes"),
                {
                    "competence": self.competencia.isoformat(),
                    "dryRun": False,
                },
                content_type="application/json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )

        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(
            resposta.json()["data"]["failure"]["code"],
            "UNEXPECTED_MATERIALIZATION_FAILURE",
        )
        self.assertNotIn(sentinela, resposta.content.decode("utf-8"))
        self.assertEqual(RequisicaoIdempotenteRecorrencia.objects.count(), 0)


class AuditoriaCustoRecorrenteTests(CustosRecorrentesTestBase):
    def test_mil_eventos_equivalentes_sao_agregados(self):
        correlation_id = uuid.uuid4()
        for _ in range(1000):
            registrar_evento_auditoria_recorrente(
                tipo_evento=AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
                origem=AuditoriaCustoRecorrente.ORIGEM_COMMAND,
                plano_id=None,
                competencia=self.competencia,
                status=AuditoriaCustoRecorrente.STATUS_BLOQUEADO,
                codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_BLOQUEIO_DOMINIO,
                correlation_id=correlation_id,
            )

        evento = AuditoriaCustoRecorrente.objects.get()
        self.assertEqual(evento.occurrences_count, 1000)

    def test_evento_fora_da_janela_de_uma_hora_cria_novo_registro(self):
        inicio = timezone.now() - timedelta(hours=2)
        dados = {
            "tipo_evento": AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
            "origem": AuditoriaCustoRecorrente.ORIGEM_COMMAND,
            "plano_id": None,
            "competencia": self.competencia,
            "status": AuditoriaCustoRecorrente.STATUS_BLOQUEADO,
            "codigo_motivo": AuditoriaCustoRecorrente.MOTIVO_BLOQUEIO_DOMINIO,
            "correlation_id": uuid.uuid4(),
        }
        registrar_evento_auditoria_recorrente(
            **dados,
            ocorrido_em=inicio,
        )
        registrar_evento_auditoria_recorrente(
            **dados,
            ocorrido_em=inicio + timedelta(hours=1, seconds=1),
        )

        self.assertEqual(AuditoriaCustoRecorrente.objects.count(), 2)

    def test_agregacao_separa_atores_distintos_na_mesma_janela(self):
        segundo_ator = get_user_model().objects.create_user(
            "segundo-ator-auditoria",
            password="senha",
        )
        dados = {
            "tipo_evento": AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
            "origem": AuditoriaCustoRecorrente.ORIGEM_API,
            "plano_id": None,
            "competencia": self.competencia,
            "status": AuditoriaCustoRecorrente.STATUS_SUCESSO,
            "codigo_motivo": AuditoriaCustoRecorrente.MOTIVO_MATERIALIZADO,
            "ocorrido_em": timezone.now(),
        }
        primeiro = registrar_evento_auditoria_recorrente(
            **dados,
            ator=self.usuario,
            correlation_id=uuid.uuid4(),
        )
        segundo = registrar_evento_auditoria_recorrente(
            **dados,
            ator=segundo_ator,
            correlation_id=uuid.uuid4(),
        )

        self.assertNotEqual(primeiro.pk, segundo.pk)
        self.assertNotEqual(primeiro.chave_agregacao, segundo.chave_agregacao)
        self.assertCountEqual(
            AuditoriaCustoRecorrente.objects.values_list("ator_id", flat=True),
            [self.usuario.pk, segundo_ator.pk],
        )

    def test_expurgo_remove_somente_eventos_com_mais_de_400_dias(self):
        agora = timezone.now()
        for dias, motivo in [
            (399, AuditoriaCustoRecorrente.MOTIVO_MATERIALIZADO),
            (400, AuditoriaCustoRecorrente.MOTIVO_JA_MATERIALIZADO),
            (401, AuditoriaCustoRecorrente.MOTIVO_BLOQUEIO_DOMINIO),
        ]:
            registrar_evento_auditoria_recorrente(
                tipo_evento=AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
                origem=AuditoriaCustoRecorrente.ORIGEM_COMMAND,
                plano_id=None,
                competencia=self.competencia,
                status=AuditoriaCustoRecorrente.STATUS_SUCESSO,
                codigo_motivo=motivo,
                correlation_id=uuid.uuid4(),
                ocorrido_em=agora - timedelta(days=dias),
            )

        self.assertEqual(expurgar_auditoria_recorrencias(agora=agora), 1)
        self.assertEqual(expurgar_auditoria_recorrencias(agora=agora), 0)
        self.assertCountEqual(
            AuditoriaCustoRecorrente.objects.values_list(
                "codigo_motivo",
                flat=True,
            ),
            [
                AuditoriaCustoRecorrente.MOTIVO_MATERIALIZADO,
                AuditoriaCustoRecorrente.MOTIVO_JA_MATERIALIZADO,
            ],
        )

    def test_command_de_expurgo_respeita_dry_run_e_audita_execucao(self):
        agora = timezone.now()
        antigo = registrar_evento_auditoria_recorrente(
            tipo_evento=AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
            origem=AuditoriaCustoRecorrente.ORIGEM_COMMAND,
            status=AuditoriaCustoRecorrente.STATUS_SUCESSO,
            codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_MATERIALIZADO,
            correlation_id=uuid.uuid4(),
            ocorrido_em=agora - timedelta(days=401),
        )
        recente = registrar_evento_auditoria_recorrente(
            tipo_evento=AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
            origem=AuditoriaCustoRecorrente.ORIGEM_API,
            status=AuditoriaCustoRecorrente.STATUS_SUCESSO,
            codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_JA_MATERIALIZADO,
            correlation_id=uuid.uuid4(),
            ocorrido_em=agora - timedelta(days=399),
        )
        saida_dry_run = StringIO()
        call_command(
            "expurgar_auditoria_custos_recorrentes",
            "--dry-run",
            stdout=saida_dry_run,
        )
        self.assertIn("eligibleForDeletion=1 deleted=0", saida_dry_run.getvalue())
        self.assertTrue(
            AuditoriaCustoRecorrente.objects.filter(pk=antigo.pk).exists()
        )

        saida_real = StringIO()
        call_command(
            "expurgar_auditoria_custos_recorrentes",
            stdout=saida_real,
        )
        self.assertIn("eligibleForDeletion=1 deleted=1", saida_real.getvalue())
        self.assertFalse(
            AuditoriaCustoRecorrente.objects.filter(pk=antigo.pk).exists()
        )
        self.assertTrue(
            AuditoriaCustoRecorrente.objects.filter(pk=recente.pk).exists()
        )
        self.assertTrue(
            AuditoriaCustoRecorrente.objects.filter(
                tipo_evento=AuditoriaCustoRecorrente.TIPO_EXPURGO,
                codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_EXPURGO,
            ).exists()
        )

    def test_admin_de_auditoria_exige_permissao_e_eh_somente_leitura(self):
        evento = registrar_evento_auditoria_recorrente(
            tipo_evento=AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO,
            origem=AuditoriaCustoRecorrente.ORIGEM_API,
            status=AuditoriaCustoRecorrente.STATUS_SUCESSO,
            codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_MATERIALIZADO,
            correlation_id=uuid.uuid4(),
        )
        sem_permissao = get_user_model().objects.create_user(
            "auditoria-admin-sem-permissao",
            password="senha",
            is_staff=True,
        )
        client = Client()
        client.force_login(sem_permissao)
        lista_url = reverse("admin:caixa_auditoriacustorecorrente_changelist")
        detalhe_url = reverse(
            "admin:caixa_auditoriacustorecorrente_change",
            args=[evento.pk],
        )
        self.assertEqual(client.get(lista_url).status_code, 403)
        self.assertEqual(client.get(detalhe_url).status_code, 403)

        investigador = get_user_model().objects.create_user(
            "auditoria-admin-investigador",
            password="senha",
            is_staff=True,
        )
        investigador.user_permissions.add(
            Permission.objects.get(
                codename="view_auditoria_custos_recorrentes"
            )
        )
        client.force_login(investigador)
        lista = client.get(lista_url)
        detalhe = client.get(detalhe_url)
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, str(evento.identificador_tecnico))
        self.assertEqual(detalhe.status_code, 200)
        self.assertNotContains(detalhe, "Salvar")
        self.assertNotContains(detalhe, "deletelink")
        self.assertEqual(client.post(detalhe_url, {}).status_code, 403)


class RetencaoIdempotenciaRecorrenteTests(CustosRecorrentesTestBase):
    def _criar_registro(self, indice, atualizado_em):
        registro = RequisicaoIdempotenteRecorrencia.objects.create(
            escopo=f"retencao-{indice}",
            chave=uuid.uuid4(),
            payload_hash="a" * 64,
            http_status=201,
            resposta_segura={"data": {"indice": indice}},
            ator=self.usuario,
        )
        RequisicaoIdempotenteRecorrencia.objects.filter(pk=registro.pk).update(
            atualizado_em=atualizado_em,
        )
        return registro

    def test_expurgo_de_idempotencia_respeita_janela_e_dry_run(self):
        agora = timezone.now()
        antigo = self._criar_registro(1, agora - timedelta(days=8))
        limite = self._criar_registro(2, agora - timedelta(days=7))
        recente = self._criar_registro(3, agora - timedelta(days=6))

        self.assertEqual(
            expurgar_requisicoes_idempotentes_recorrencia(
                agora=agora,
                dry_run=True,
            ),
            1,
        )
        self.assertTrue(
            RequisicaoIdempotenteRecorrencia.objects.filter(pk=antigo.pk).exists()
        )
        self.assertEqual(
            expurgar_requisicoes_idempotentes_recorrencia(agora=agora),
            1,
        )
        self.assertFalse(
            RequisicaoIdempotenteRecorrencia.objects.filter(pk=antigo.pk).exists()
        )
        self.assertTrue(
            RequisicaoIdempotenteRecorrencia.objects.filter(pk=limite.pk).exists()
        )
        self.assertTrue(
            RequisicaoIdempotenteRecorrencia.objects.filter(pk=recente.pk).exists()
        )

    def test_command_de_idempotencia_e_tenant_only_e_valida_retencao(self):
        saida = StringIO()
        call_command(
            "expurgar_requisicoes_idempotentes_recorrencia",
            "--dry-run",
            stdout=saida,
        )
        self.assertIn("idempotencyRequestsWouldRemove=0", saida.getvalue())
        with self.assertRaises(CommandError):
            call_command(
                "expurgar_requisicoes_idempotentes_recorrencia",
                "--retencao-dias=0",
                stdout=StringIO(),
            )


class SigiloSalarialEAdminTests(CustosRecorrentesTestBase):
    def test_filtros_salariais_usam_subconsulta_sem_materializar_ids(self):
        with CaptureQueriesContext(connection) as construcao:
            ids_salariais = ids_custos_salariais()
            lancamentos = filtrar_lancamentos_financeiros(
                {"_exclude_salary": True}
            )
        self.assertEqual(len(construcao), 0)
        self.assertIsNone(ids_salariais._result_cache)
        sql = str(lancamentos.query).upper()
        self.assertIn("NOT", sql)
        self.assertGreaterEqual(sql.count("SELECT"), 2)

        with CaptureQueriesContext(connection) as execucao_lancamentos:
            list(lancamentos.values_list("id", flat=True)[:10])
        self.assertEqual(len(execucao_lancamentos), 1)

        with CaptureQueriesContext(connection) as execucao_obrigacoes:
            contar_obrigacoes_financeiras_canonicas(
                {"_exclude_salary": True}
            )
        self.assertEqual(len(execucao_obrigacoes), 1)

    def _criar_ocorrencia_salarial_sentinela(self):
        servidor = self.criar_servidor_salarial(
            nome="SERVIDOR-SIGILOSO-987654321",
            salario_mensal=Decimal("9876543.21"),
        )
        self.criar_historico(servidor, valor=Decimal("9876543.21"))
        plano = self.criar_plano_salarial(servidor)
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        custo.valor_pago = custo.valor_previsto
        custo.data_pagamento = self.hoje
        custo.save(update_fields=[
            "valor_pago",
            "data_pagamento",
            "status",
            "atualizado_em",
        ])
        obrigacao = ObrigacaoFinanceira.objects.get(custo_fixo=custo)
        lancamento = LancamentoFinanceiro.objects.get(custo_fixo=custo)
        return plano, custo, obrigacao, lancamento

    def test_exportacao_pm06_exclui_salario_e_derivados_canonicos(self):
        self._criar_ocorrencia_salarial_sentinela()
        with TemporaryDirectory() as diretorio:
            saida = StringIO()
            call_command(
                "exportar_recadastro_manual_pm06",
                f"--diretorio-saida={diretorio}",
                "--json",
                stdout=saida,
            )
            payload = json.loads(saida.getvalue())
            conteudo_arquivo = Path(
                diretorio,
                "pm06-recadastro-manual.json",
            ).read_text(encoding="utf-8")

        serializado = json.dumps(payload, ensure_ascii=False)
        for conteudo in (serializado, conteudo_arquivo):
            self.assertNotIn("SERVIDOR-SIGILOSO-987654321", conteudo)
            self.assertNotIn("9876543.21", conteudo)
            self.assertNotIn("9876543,21", conteudo)
        self.assertEqual(payload["summary"]["fixedCostsCount"], 0)
        self.assertEqual(
            payload["outOfManualScope"]["obrigacoesFinanceirasCount"],
            0,
        )
        self.assertEqual(
            payload["outOfManualScope"]["lancamentosFinanceirosCount"],
            0,
        )

    def test_admin_financeiro_sem_permissao_salarial_nao_lista_nem_abre_registros(self):
        plano, custo, obrigacao, lancamento = (
            self._criar_ocorrencia_salarial_sentinela()
        )
        restrito = get_user_model().objects.create_user(
            "admin-financeiro-sem-salario",
            password="senha",
            is_staff=True,
        )
        restrito.user_permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "view_custofixo",
                    "view_planocustorecorrente",
                    "view_obrigacaofinanceira",
                    "view_lancamentofinanceiro",
                ]
            )
        )
        client = Client()
        client.force_login(restrito)
        recursos = [
            ("custofixo", custo.pk),
            ("planocustorecorrente", plano.pk),
            ("obrigacaofinanceira", obrigacao.pk),
            ("lancamentofinanceiro", lancamento.pk),
        ]
        for modelo, pk in recursos:
            with self.subTest(modelo=modelo):
                lista = client.get(reverse(f"admin:caixa_{modelo}_changelist"))
                self.assertEqual(lista.status_code, 200)
                self.assertNotContains(lista, "SERVIDOR-SIGILOSO-987654321")
                self.assertNotContains(lista, "9876543.21")
                detalhe = client.get(
                    reverse(f"admin:caixa_{modelo}_change", args=[pk])
                )
                self.assertEqual(detalhe.status_code, 302)

    def test_admin_nao_altera_nem_exclui_ocorrencia_derivada(self):
        plano, _ = self.criar_plano_comum()
        resultado = materializar_plano_competencia(
            plano,
            self.competencia,
            usuario=self.usuario,
        )
        custo = CustoFixo.objects.get(pk=resultado["fixedCostId"])
        descricao_original = custo.descricao
        valor_original = custo.valor_previsto
        operador = get_user_model().objects.create_user(
            "admin-custo-derivado",
            password="senha",
            is_staff=True,
        )
        operador.user_permissions.add(
            Permission.objects.get(codename="view_custofixo"),
            Permission.objects.get(codename="change_custofixo"),
            Permission.objects.get(codename="delete_custofixo"),
        )
        client = Client()
        client.force_login(operador)
        detalhe_url = reverse("admin:caixa_custofixo_change", args=[custo.pk])
        resposta = client.post(
            detalhe_url,
            {
                "descricao": "ALTERACAO-INDEVIDA",
                "valor_previsto": "1.00",
                "status": "pago",
            },
        )
        self.assertIn(resposta.status_code, {200, 302})
        custo.refresh_from_db()
        self.assertEqual(custo.descricao, descricao_original)
        self.assertEqual(custo.valor_previsto, valor_original)
        self.assertNotEqual(custo.status, "pago")
        self.assertEqual(
            client.post(
                reverse("admin:caixa_custofixo_delete", args=[custo.pk]),
                {"post": "yes"},
            ).status_code,
            403,
        )
        self.assertTrue(CustoFixo.objects.filter(pk=custo.pk).exists())


class CommandsRecorrentesEscopoTenantTests(MultiTenantTestCase):
    def test_commands_recusam_schema_public(self):
        self.switch_to_public()
        comandos = (
            ("materializar_custos_recorrentes", ["--dry-run"]),
            (
                "ativar_mensalistas_existentes",
                ["--data-corte", "2026-07-01", "--dry-run"],
            ),
            ("expurgar_auditoria_custos_recorrentes", ["--dry-run"]),
            ("expurgar_requisicoes_idempotentes_recorrencia", ["--dry-run"]),
        )

        for comando, argumentos in comandos:
            with self.subTest(comando=comando):
                with self.assertRaises(CommandError):
                    call_command(comando, *argumentos, stdout=StringIO())
