from datetime import date
import calendar
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from simple_history.models import HistoricalRecords

from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PAGO,
    STATUS_PAGAMENTO_CHOICES,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
)
from .services_validacao_pagamentos import erro_caixa_insuficiente_para_aumento
from .utils_financeiros import ZERO_DECIMAL, quantizar_moeda


def adicionar_meses(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia)
    return date(ano, mes, dia)


class PlanoCustoRecorrente(models.Model):
    ORIGEM_COMUM = "comum"
    ORIGEM_SALARIO = "salario"
    ORIGEM_CHOICES = [
        (ORIGEM_COMUM, "Custo recorrente"),
        (ORIGEM_SALARIO, "Salário mensal"),
    ]

    PERIODICIDADE_MENSAL = "mensal"
    PERIODICIDADE_CHOICES = [
        (PERIODICIDADE_MENSAL, "Mensal"),
    ]

    descricao = models.CharField(max_length=150)
    categoria = models.CharField(
        max_length=30,
        choices=[
            ("aluguel", "Aluguel"),
            ("energia", "Energia"),
            ("agua", "Água"),
            ("internet", "Internet"),
            ("telefone", "Telefone"),
            ("salario", "Salário"),
            ("contador", "Contador"),
            ("sistema", "Sistema"),
            ("imposto", "Imposto"),
            ("outro", "Outro"),
        ],
        default="outro",
        db_index=True,
    )
    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default=ORIGEM_COMUM,
        db_index=True,
    )
    periodicidade = models.CharField(
        max_length=12,
        choices=PERIODICIDADE_CHOICES,
        default=PERIODICIDADE_MENSAL,
    )
    valor_previsto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(null=True, blank=True, db_index=True)
    dia_vencimento = models.PositiveSmallIntegerField(default=1)
    data_autorizacao_materializacao = models.DateField(db_index=True)
    ativo = models.BooleanField(default=True, db_index=True)
    observacao = models.TextField(blank=True)

    servidor = models.ForeignKey(
        "caixa.Servidor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planos_custos_recorrentes",
    )
    custo_legado_referencia = models.ForeignKey(
        "CustoFixo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planos_renovacao",
    )
    plano_renovado = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="renovacoes",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_custos_recorrentes_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_custos_recorrentes_atualizados",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Plano de custo recorrente"
        verbose_name_plural = "Planos de custos recorrentes"
        ordering = ["data_inicio", "descricao", "id"]
        indexes = [
            models.Index(fields=["ativo", "data_inicio", "data_fim"]),
            models.Index(fields=["origem", "ativo"]),
            models.Index(fields=["servidor", "ativo"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(dia_vencimento__gte=1, dia_vencimento__lte=31),
                name="ck_plano_custo_dia_venc",
            ),
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=models.F("data_inicio")),
                name="ck_plano_custo_periodo",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        origem="comum",
                        valor_previsto__gt=0,
                        servidor__isnull=True,
                    )
                    | Q(
                        origem="salario",
                        categoria="salario",
                        valor_previsto__isnull=True,
                        servidor__isnull=False,
                    )
                ),
                name="ck_plano_custo_origem",
            ),
            models.UniqueConstraint(
                fields=["servidor"],
                condition=Q(origem="salario", servidor__isnull=False),
                name="uq_plano_salario_servidor",
            ),
            models.UniqueConstraint(
                fields=["custo_legado_referencia"],
                condition=Q(custo_legado_referencia__isnull=False),
                name="uq_plano_renovacao_legado",
            ),
            models.UniqueConstraint(
                fields=["plano_renovado"],
                condition=Q(plano_renovado__isnull=False),
                name="uq_plano_renovacao_plano",
            ),
        ]
        permissions = [
            ("materialize_planocustorecorrente", "Pode materializar plano de custo recorrente"),
        ]

    def __str__(self):
        return f"{self.descricao} — desde {self.data_inicio:%m/%Y}"

    def clean(self):
        super().clean()
        self.descricao = (self.descricao or "").strip()
        self.observacao = (self.observacao or "").strip()
        erros = {}

        if not self.descricao:
            erros["descricao"] = "Informe a descrição do plano."
        if self.periodicidade != self.PERIODICIDADE_MENSAL:
            erros["periodicidade"] = "Apenas a periodicidade mensal é suportada."
        if not 1 <= self.dia_vencimento <= 31:
            erros["dia_vencimento"] = "O dia de vencimento deve estar entre 1 e 31."
        if self.data_fim and self.data_fim < self.data_inicio:
            erros["data_fim"] = "A data final não pode ser anterior à data inicial."

        if self.origem == self.ORIGEM_SALARIO:
            if self.categoria != "salario":
                erros["categoria"] = "Plano salarial deve usar a categoria salário."
            if not self.servidor_id:
                erros["servidor"] = "Informe o servidor do plano salarial."
            if self.valor_previsto is not None:
                erros["valor_previsto"] = "O valor salarial deve vir do histórico salarial."
        else:
            if self.categoria == "salario":
                erros["categoria"] = "A categoria salário é exclusiva de planos salariais."
            if self.servidor_id:
                erros["servidor"] = "Plano comum não deve possuir servidor."
            if self.valor_previsto is None or self.valor_previsto <= ZERO_DECIMAL:
                erros["valor_previsto"] = "Informe um valor previsto maior que zero."

        if self.plano_renovado_id == self.pk and self.pk:
            erros["plano_renovado"] = "Um plano não pode renovar a si próprio."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.descricao = (self.descricao or "").strip()
        self.observacao = (self.observacao or "").strip()
        super().save(*args, **kwargs)


class RequisicaoIdempotenteRecorrencia(models.Model):
    STATUS_CONCLUIDA = "concluida"
    STATUS_CHOICES = [
        (STATUS_CONCLUIDA, "Concluída"),
    ]

    escopo = models.CharField(max_length=80)
    chave = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CONCLUIDA,
    )
    http_status = models.PositiveSmallIntegerField()
    resposta_segura = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Requisição idempotente de recorrência"
        verbose_name_plural = "Requisições idempotentes de recorrência"
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["escopo", "chave"],
                name="uq_idempotencia_rec_escopo_chave",
            ),
        ]
        indexes = [
            models.Index(fields=["criado_em"]),
        ]


class AuditoriaCustoRecorrente(models.Model):
    TIPO_MATERIALIZACAO = "materializacao"
    TIPO_RECUPERACAO = "recuperacao"
    TIPO_ATIVACAO = "ativacao"
    TIPO_EXPURGO = "expurgo"
    TIPO_CHOICES = [
        (TIPO_MATERIALIZACAO, "Materialização"),
        (TIPO_RECUPERACAO, "Recuperação"),
        (TIPO_ATIVACAO, "Ativação"),
        (TIPO_EXPURGO, "Expurgo"),
    ]

    ORIGEM_API = "api"
    ORIGEM_COMMAND = "command"
    ORIGEM_ADMIN = "admin"
    ORIGEM_ATIVACAO = "ativacao"
    ORIGEM_SISTEMA = "sistema"
    ORIGEM_CHOICES = [
        (ORIGEM_API, "API"),
        (ORIGEM_COMMAND, "Command"),
        (ORIGEM_ADMIN, "Admin"),
        (ORIGEM_ATIVACAO, "Ativação"),
        (ORIGEM_SISTEMA, "Sistema"),
    ]

    STATUS_SUCESSO = "sucesso"
    STATUS_BLOQUEADO = "bloqueado"
    STATUS_CONFLITO = "conflito"
    STATUS_FALHA = "falha"
    STATUS_CHOICES = [
        (STATUS_SUCESSO, "Sucesso"),
        (STATUS_BLOQUEADO, "Bloqueado"),
        (STATUS_CONFLITO, "Conflito"),
        (STATUS_FALHA, "Falha"),
    ]

    MOTIVO_MATERIALIZADO = "MATERIALIZED"
    MOTIVO_RECUPERADO = "RECOVERED"
    MOTIVO_JA_MATERIALIZADO = "ALREADY_MATERIALIZED"
    MOTIVO_BLOQUEIO_DOMINIO = "DOMAIN_BLOCKED"
    MOTIVO_CONCORRENCIA_ESGOTADA = "CONCURRENCY_RETRY_EXHAUSTED"
    MOTIVO_FALHA_INESPERADA = "UNEXPECTED_MATERIALIZATION_FAILURE"
    MOTIVO_SERVIDOR_ATIVADO = "SERVER_ACTIVATED"
    MOTIVO_SERVIDOR_JA_ATIVO = "SERVER_ALREADY_ACTIVE"
    MOTIVO_ATIVACAO_BLOQUEADA = "ACTIVATION_BLOCKED"
    MOTIVO_ATIVACAO_FALHA = "ACTIVATION_FAILED"
    MOTIVO_EXPURGO = "RETENTION_PURGE"
    MOTIVO_CHOICES = [
        (MOTIVO_MATERIALIZADO, "Materializado"),
        (MOTIVO_RECUPERADO, "Competência recuperada"),
        (MOTIVO_JA_MATERIALIZADO, "Já materializado"),
        (MOTIVO_BLOQUEIO_DOMINIO, "Bloqueio de domínio"),
        (MOTIVO_CONCORRENCIA_ESGOTADA, "Concorrência esgotada"),
        (MOTIVO_FALHA_INESPERADA, "Falha inesperada"),
        (MOTIVO_SERVIDOR_ATIVADO, "Servidor ativado"),
        (MOTIVO_SERVIDOR_JA_ATIVO, "Servidor já ativado"),
        (MOTIVO_ATIVACAO_BLOQUEADA, "Ativação bloqueada"),
        (MOTIVO_ATIVACAO_FALHA, "Falha na ativação"),
        (MOTIVO_EXPURGO, "Expurgo de retenção"),
    ]

    identificador_tecnico = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    tipo_evento = models.CharField(max_length=24, choices=TIPO_CHOICES)
    origem = models.CharField(max_length=16, choices=ORIGEM_CHOICES)
    plano = models.ForeignKey(
        PlanoCustoRecorrente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria",
    )
    competencia = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    codigo_motivo = models.CharField(max_length=48, choices=MOTIVO_CHOICES)
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    correlation_id = models.UUIDField(db_index=True)
    chave_agregacao = models.CharField(max_length=64, db_index=True)
    first_occurred_at = models.DateTimeField()
    last_occurred_at = models.DateTimeField(db_index=True)
    occurrences_count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Auditoria de custo recorrente"
        verbose_name_plural = "Auditoria de custos recorrentes"
        ordering = ["-last_occurred_at", "-id"]
        default_permissions = ()
        permissions = [
            (
                "view_auditoria_custos_recorrentes",
                "Pode consultar auditoria de custos recorrentes",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(occurrences_count__gte=1),
                name="ck_audit_rec_ocorrencias_pos",
            ),
        ]
        indexes = [
            models.Index(fields=["plano", "competencia"]),
            models.Index(fields=["tipo_evento", "origem", "status"]),
            models.Index(fields=["chave_agregacao", "last_occurred_at"]),
        ]


class EstadoAgregacaoAuditoriaRecorrente(models.Model):
    chave_agregacao = models.CharField(max_length=64, primary_key=True)
    ultimo_evento = models.ForeignKey(
        AuditoriaCustoRecorrente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de agregação de auditoria recorrente"
        verbose_name_plural = "Estados de agregação de auditoria recorrente"
        default_permissions = ()


class CustoFixo(models.Model):
    STATUS_CHOICES = STATUS_PAGAMENTO_CHOICES

    CATEGORIA_CHOICES = [
        ("aluguel", "Aluguel"),
        ("energia", "Energia"),
        ("agua", "Água"),
        ("internet", "Internet"),
        ("telefone", "Telefone"),
        ("salario", "Salário"),
        ("contador", "Contador"),
        ("sistema", "Sistema"),
        ("imposto", "Imposto"),
        ("outro", "Outro"),
    ]

    descricao = models.CharField(max_length=150)
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, default="outro", db_index=True)

    valor_previsto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    data_vencimento = models.DateField(db_index=True)
    data_pagamento = models.DateField(null=True, blank=True, db_index=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDENTE, db_index=True)
    baixado_manualmente = models.BooleanField(default=False, verbose_name="Baixa manual")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")
    observacao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True, db_index=True)

    recorrente = models.BooleanField(default=True)
    quantidade_meses = models.PositiveIntegerField(default=12)
    custo_pai = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_filhos",
    )
    gerado_automaticamente = models.BooleanField(default=False)
    plano_recorrente = models.ForeignKey(
        PlanoCustoRecorrente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ocorrencias",
    )
    competencia = models.DateField(null=True, blank=True, db_index=True)
    origem_recorrencia = models.CharField(
        max_length=20,
        choices=[
            ("legado", "Legado ou avulso"),
            ("plano", "Plano recorrente"),
            ("salario", "Salário mensal"),
        ],
        default="legado",
        db_index=True,
    )
    servidor_salario = models.ForeignKey(
        "caixa.Servidor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_salariais",
    )
    historico_salarial = models.ForeignKey(
        "caixa.HistoricoSalarialServidor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="custos_materializados",
    )
    servidor_nome_snapshot = models.CharField(max_length=150, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_fixos_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_fixos_atualizados",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Custo fixo"
        verbose_name_plural = "Custos fixos"
        ordering = ["data_vencimento", "descricao", "id"]
        indexes = [
            models.Index(fields=["status", "data_vencimento"]),
            models.Index(fields=["categoria", "data_vencimento"]),
            models.Index(fields=["ativo", "data_vencimento"]),
            models.Index(fields=["custo_pai", "data_vencimento"]),
            models.Index(fields=["origem_recorrencia", "data_vencimento"]),
            models.Index(fields=["plano_recorrente", "competencia"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_previsto__gte=0)
                    & models.Q(valor_pago__gte=0)
                    & models.Q(valor_pago__lte=models.F("valor_previsto"))
                ),
                name="ck_custo_fixo_valores",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade_meses__gte=1),
                name="ck_custo_fixo_meses_pos",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(plano_recorrente__isnull=True, competencia__isnull=True)
                    | models.Q(plano_recorrente__isnull=False, competencia__isnull=False)
                ),
                name="ck_custo_fixo_plano_comp",
            ),
            models.UniqueConstraint(
                fields=["plano_recorrente", "competencia"],
                condition=models.Q(plano_recorrente__isnull=False),
                name="uq_custo_fixo_plano_comp",
            ),
        ]

    def __str__(self):
        return f"{self.descricao} - {self.data_vencimento:%m/%Y}"

    @property
    def saldo_em_aberto(self):
        if self.status in [STATUS_PAGO, STATUS_CANCELADO] or self.baixado_manualmente:
            return Decimal("0.00")

        return quantizar_moeda(self.valor_previsto - self.valor_pago)

    @property
    def valor_pendente_pagamento(self):
        return self.saldo_em_aberto

    @property
    def contas_pendentes(self):
        return self.valor_pendente_pagamento

    @property
    def eh_recorrente(self):
        return bool(
            self.recorrente
            or self.custo_pai_id
            or self.plano_recorrente_id
            or self.origem_recorrencia in {"plano", "salario"}
        )

    def clean(self):
        erros = {}

        if self.valor_previsto < 0:
            erros["valor_previsto"] = "O valor previsto não pode ser negativo."

        if self.valor_pago < 0:
            erros["valor_pago"] = "O valor pago não pode ser negativo."

        if self.valor_pago > self.valor_previsto:
            erros["valor_pago"] = "O valor pago não pode ser maior que o valor previsto."

        if self.quantidade_meses < 1:
            erros["quantidade_meses"] = "A quantidade de meses deve ser no mínimo 1."

        if self.baixado_manualmente and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        if "valor_pago" not in erros and self.valor_pago > ZERO_DECIMAL:
            erro_caixa = erro_caixa_insuficiente_para_aumento(
                self.__class__,
                self.pk,
                "valor_pago",
                self.valor_pago,
                self.data_pagamento or self.data_vencimento,
            )
            if erro_caixa:
                erros["valor_pago"] = erro_caixa

        if erros:
            raise ValidationError(erros)

    def atualizar_status_automaticamente(self):
        if self.status == STATUS_CANCELADO:
            return

        if self.baixado_manualmente:
            self.status = STATUS_PAGO
            return

        if self.status == STATUS_PAGO and self.valor_pago > ZERO_DECIMAL:
            return

        saldo = self.valor_pendente_pagamento

        if saldo <= ZERO_DECIMAL:
            self.status = STATUS_PAGO
            return

        if self.valor_pago > ZERO_DECIMAL:
            self.status = STATUS_PARCIAL
            return

        self.status = STATUS_PENDENTE

    def save(self, *args, **kwargs):
        self.atualizar_status_automaticamente()
        super().save(*args, **kwargs)

    def gerar_recorrencias(self):
        if not self.recorrente:
            return

        if self.gerado_automaticamente:
            return

        if self.quantidade_meses <= 1:
            return

        if self.custos_filhos.exists():
            return

        for i in range(1, self.quantidade_meses):
            nova_data = adicionar_meses(self.data_vencimento, i)

            CustoFixo.objects.create(
                descricao=self.descricao,
                categoria=self.categoria,
                valor_previsto=self.valor_previsto,
                valor_pago=Decimal("0.00"),
                data_vencimento=nova_data,
                data_pagamento=None,
                status=STATUS_PENDENTE,
                observacao=self.observacao,
                ativo=self.ativo,
                recorrente=False,
                quantidade_meses=1,
                custo_pai=self,
                gerado_automaticamente=True,
                criado_por=self.criado_por,
                atualizado_por=self.atualizado_por,
            )
