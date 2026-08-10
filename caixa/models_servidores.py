from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from simple_history.models import HistoricalRecords


ZERO = Decimal("0.00")


class Servidor(models.Model):
    TIPO_DOCUMENTO_CPF = "CPF"
    TIPO_DOCUMENTO_CNPJ = "CNPJ"
    TIPO_DOCUMENTO_RG = "RG"
    TIPO_DOCUMENTO_OUTRO = "OUTRO"
    TIPO_DOCUMENTO_CHOICES = [
        (TIPO_DOCUMENTO_CPF, "CPF"),
        (TIPO_DOCUMENTO_CNPJ, "CNPJ"),
        (TIPO_DOCUMENTO_RG, "RG"),
        (TIPO_DOCUMENTO_OUTRO, "Outro"),
    ]

    VINCULO_DIARISTA = "DIARISTA"
    VINCULO_MENSALISTA = "MENSALISTA"
    TIPO_VINCULO_CHOICES = [
        (VINCULO_DIARISTA, "Diarista"),
        (VINCULO_MENSALISTA, "Mensalista"),
    ]

    nome = models.CharField(max_length=150, db_index=True)
    tipo_documento = models.CharField(
        max_length=10,
        choices=TIPO_DOCUMENTO_CHOICES,
        default=TIPO_DOCUMENTO_CPF,
    )
    documento = models.CharField(max_length=32, unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True, db_index=True)
    tipo_vinculo = models.CharField(
        max_length=12,
        choices=TIPO_VINCULO_CHOICES,
        default=VINCULO_DIARISTA,
        db_index=True,
    )
    exibir_como_socio = models.BooleanField(
        default=False,
        verbose_name="Exibir como Sócio",
    )
    salario_mensal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    carga_horaria_mensal = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("744.00")),
        ],
    )
    data_inicio_contrato = models.DateField(null=True, blank=True, db_index=True)
    data_fim_contrato = models.DateField(null=True, blank=True, db_index=True)
    dia_pagamento_salario = models.PositiveSmallIntegerField(null=True, blank=True)
    data_autorizacao_custo_salarial = models.DateField(null=True, blank=True, db_index=True)
    servicos = models.ManyToManyField(
        "Servico",
        through="ServidorServico",
        related_name="servidores",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servidores_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servidores_atualizados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Servidor"
        verbose_name_plural = "Servidores"
        ordering = ["nome", "id"]
        indexes = [
            models.Index(fields=["ativo", "tipo_vinculo", "nome"]),
            models.Index(fields=["tipo_documento", "documento"]),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("documento"),
                name="uq_servidor_documento_ci",
            ),
            models.CheckConstraint(
                condition=Q(
                    tipo_vinculo__in=["DIARISTA", "MENSALISTA"]
                ),
                name="ck_servidor_vinculo_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(tipo_vinculo="MENSALISTA", salario_mensal__gt=0)
                    | Q(
                        tipo_vinculo="DIARISTA",
                        salario_mensal__isnull=True,
                        data_inicio_contrato__isnull=True,
                        data_fim_contrato__isnull=True,
                        dia_pagamento_salario__isnull=True,
                        data_autorizacao_custo_salarial__isnull=True,
                    )
                ),
                name="ck_servidor_salario_vinculo",
            ),
            models.CheckConstraint(
                condition=Q(data_fim_contrato__isnull=True)
                | Q(data_inicio_contrato__isnull=True)
                | Q(data_fim_contrato__gte=models.F("data_inicio_contrato")),
                name="ck_servidor_periodo_contrato",
            ),
            models.CheckConstraint(
                condition=Q(dia_pagamento_salario__isnull=True)
                | Q(dia_pagamento_salario__gte=1, dia_pagamento_salario__lte=31),
                name="ck_servidor_dia_pagamento",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        tipo_vinculo="MENSALISTA",
                        carga_horaria_mensal__isnull=True,
                    )
                    | Q(
                        tipo_vinculo="MENSALISTA",
                        carga_horaria_mensal__gt=0,
                        carga_horaria_mensal__lte=Decimal("744.00"),
                    )
                    | Q(
                        tipo_vinculo="DIARISTA",
                        carga_horaria_mensal__isnull=True,
                    )
                ),
                name="ck_servidor_jornada_mensal",
            ),
        ]
        permissions = [
            ("view_salario_servidor", "Pode visualizar salário de servidor"),
            ("change_salario_servidor", "Pode alterar salário de servidor"),
            ("view_dados_sensiveis_servidor", "Pode visualizar dados sensíveis de servidor"),
        ]

    def __str__(self):
        return self.nome

    @staticmethod
    def normalizar_documento(valor):
        return "".join(
            caractere
            for caractere in str(valor or "").strip().upper()
            if caractere.isalnum()
        )

    @property
    def documento_mascarado(self):
        sufixo = self.documento[-4:] if self.documento else ""
        return f"••••{sufixo}" if sufixo else ""

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        self.documento = self.normalizar_documento(self.documento)
        self.telefone = (self.telefone or "").strip()
        self.email = (self.email or "").strip().lower()
        self.endereco = (self.endereco or "").strip()
        self.observacoes = (self.observacoes or "").strip()

        erros = {}
        if not self.nome:
            erros["nome"] = "Informe o nome do servidor."
        if not self.documento:
            erros["documento"] = "Informe o documento do servidor."
        if self.data_nascimento and self.data_nascimento > date.today():
            erros["data_nascimento"] = "A data de nascimento não pode estar no futuro."

        if self.tipo_vinculo == self.VINCULO_MENSALISTA:
            if self.salario_mensal is None or self.salario_mensal <= ZERO:
                erros["salario_mensal"] = "Informe um salário mensal maior que zero."
            if self.data_fim_contrato and not self.data_inicio_contrato:
                erros["data_inicio_contrato"] = "Informe o início do contrato."
            if (
                self.data_inicio_contrato
                and self.data_fim_contrato
                and self.data_fim_contrato < self.data_inicio_contrato
            ):
                erros["data_fim_contrato"] = "O fim do contrato não pode ser anterior ao início."
            if self.dia_pagamento_salario is not None and not (
                1 <= self.dia_pagamento_salario <= 31
            ):
                erros["dia_pagamento_salario"] = "O dia de pagamento deve estar entre 1 e 31."
            if self.carga_horaria_mensal is not None and not (
                Decimal("0.01")
                <= self.carga_horaria_mensal
                <= Decimal("744.00")
            ):
                erros["carga_horaria_mensal"] = (
                    "A jornada mensal deve estar entre 0,01 e 744 horas."
                )
        else:
            if self.salario_mensal is not None:
                erros["salario_mensal"] = "Diarista não deve possuir salário mensal."
            if any(
                [
                    self.data_inicio_contrato,
                    self.data_fim_contrato,
                    self.dia_pagamento_salario,
                    self.data_autorizacao_custo_salarial,
                ]
            ):
                erros["tipo_vinculo"] = "Dados de custo salarial são exclusivos de mensalistas."
            if self.carga_horaria_mensal is not None:
                erros["carga_horaria_mensal"] = (
                    "Jornada mensal contratada é exclusiva de mensalistas."
                )

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.nome = (self.nome or "").strip()
        self.documento = self.normalizar_documento(self.documento)
        self.email = (self.email or "").strip().lower()
        self.full_clean()
        super().save(*args, **kwargs)


class ServidorServico(models.Model):
    servidor = models.ForeignKey(
        "Servidor",
        on_delete=models.CASCADE,
        related_name="vinculos_servicos",
    )
    servico = models.ForeignKey(
        "Servico",
        on_delete=models.PROTECT,
        related_name="vinculos_servidores",
    )
    ativo = models.BooleanField(default=True, db_index=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vinculos_servidor_servico_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vinculos_servidor_servico_atualizados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Serviço do servidor"
        verbose_name_plural = "Serviços dos servidores"
        ordering = ["servidor__nome", "servico__nome", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["servidor", "servico"],
                name="uq_servidor_servico",
            ),
        ]
        indexes = [
            models.Index(fields=["servidor", "ativo"]),
            models.Index(fields=["servico", "ativo"]),
        ]

    def __str__(self):
        return f"{self.servidor} — {self.servico}"

    def clean(self):
        super().clean()
        if not self.ativo or not self.servico_id or self.servico.ativo:
            return

        vinculo_anterior = (
            ServidorServico.objects.filter(pk=self.pk).only("servico_id").first()
            if self.pk
            else None
        )
        if not vinculo_anterior or vinculo_anterior.servico_id != self.servico_id:
            raise ValidationError(
                {"servico": "Serviço inativo não pode ser adicionado ao servidor."}
            )


class HistoricoSalarialServidor(models.Model):
    servidor = models.ForeignKey(
        "Servidor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_salariais",
    )
    servidor_nome_snapshot = models.CharField(max_length=150)
    servidor_id_snapshot = models.PositiveBigIntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(null=True, blank=True, db_index=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_salariais_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_salariais_atualizados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Histórico salarial do servidor"
        verbose_name_plural = "Históricos salariais dos servidores"
        ordering = ["-data_inicio", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="ck_hist_salario_valor_pos",
            ),
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=models.F("data_inicio")),
                name="ck_hist_salario_periodo",
            ),
            models.UniqueConstraint(
                fields=["servidor", "data_inicio"],
                condition=Q(servidor__isnull=False),
                name="uq_hist_salario_inicio",
            ),
        ]
        indexes = [models.Index(fields=["servidor", "data_inicio", "data_fim"])]

    def __str__(self):
        nome = self.servidor.nome if self.servidor_id else self.servidor_nome_snapshot
        return f"{nome} — {self.valor} desde {self.data_inicio:%d/%m/%Y}"

    def clean(self):
        super().clean()
        self.servidor_nome_snapshot = (self.servidor_nome_snapshot or "").strip()
        erros = {}
        if self.valor <= ZERO:
            erros["valor"] = "O salário deve ser maior que zero."
        if self.data_fim and self.data_fim < self.data_inicio:
            erros["data_fim"] = "A data final não pode ser anterior à data inicial."
        if self.servidor_id:
            sobrepostos = HistoricoSalarialServidor.objects.filter(
                servidor_id=self.servidor_id,
            ).exclude(pk=self.pk)
            if self.data_fim:
                sobrepostos = sobrepostos.filter(data_inicio__lte=self.data_fim)
            sobrepostos = sobrepostos.filter(
                Q(data_fim__isnull=True) | Q(data_fim__gte=self.data_inicio)
            )
            if sobrepostos.exists():
                erros["data_inicio"] = "Já existe uma vigência salarial sobreposta."
        if erros:
            raise ValidationError(erros)


class HistoricoJornadaMensalServidor(models.Model):
    servidor = models.ForeignKey(
        "Servidor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_jornada_mensal",
    )
    servidor_nome_snapshot = models.CharField(max_length=150)
    servidor_id_snapshot = models.PositiveBigIntegerField()
    horas_mensais = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("744.00")),
        ],
    )
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(null=True, blank=True, db_index=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_jornada_mensal_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_jornada_mensal_atualizados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Histórico de jornada mensal do servidor"
        verbose_name_plural = "Históricos de jornada mensal dos servidores"
        ordering = ["-data_inicio", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(horas_mensais__gt=0, horas_mensais__lte=Decimal("744.00")),
                name="ck_hist_jornada_horas",
            ),
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True)
                | Q(data_fim__gte=models.F("data_inicio")),
                name="ck_hist_jornada_periodo",
            ),
            models.UniqueConstraint(
                fields=["servidor_id_snapshot", "data_inicio"],
                name="uq_hist_jornada_snapshot_inicio",
            ),
        ]
        indexes = [
            models.Index(fields=["servidor", "data_inicio", "data_fim"]),
            models.Index(
                fields=["servidor_id_snapshot", "data_inicio", "data_fim"]
            ),
        ]

    def __str__(self):
        nome = self.servidor.nome if self.servidor_id else self.servidor_nome_snapshot
        return f"{nome} — {self.horas_mensais}h desde {self.data_inicio:%d/%m/%Y}"

    def clean(self):
        super().clean()
        self.servidor_nome_snapshot = (self.servidor_nome_snapshot or "").strip()
        erros = {}
        if not Decimal("0.01") <= self.horas_mensais <= Decimal("744.00"):
            erros["horas_mensais"] = (
                "A jornada mensal deve estar entre 0,01 e 744 horas."
            )
        if self.data_fim and self.data_fim < self.data_inicio:
            erros["data_fim"] = "A data final não pode ser anterior à data inicial."
        if self.servidor_id_snapshot:
            sobrepostos = HistoricoJornadaMensalServidor.objects.filter(
                servidor_id_snapshot=self.servidor_id_snapshot,
            ).exclude(pk=self.pk)
            if self.data_fim:
                sobrepostos = sobrepostos.filter(data_inicio__lte=self.data_fim)
            sobrepostos = sobrepostos.filter(
                Q(data_fim__isnull=True) | Q(data_fim__gte=self.data_inicio)
            )
            if sobrepostos.exists():
                erros["data_inicio"] = "Já existe uma vigência de jornada sobreposta."
        if erros:
            raise ValidationError(erros)


class ParticipacaoServidorEvento(models.Model):
    REGRA_RATEIO_HORAS_EQUIVALENTES = "HORAS_EQUIVALENTES"

    servidor = models.ForeignKey(
        "Servidor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participacoes_eventos",
    )
    evento = models.ForeignKey(
        "Evento",
        on_delete=models.CASCADE,
        related_name="participacoes_servidores",
    )
    servico = models.ForeignKey(
        "Servico",
        on_delete=models.PROTECT,
        related_name="participacoes_servidores",
    )
    tipo_vinculo = models.CharField(
        max_length=12,
        choices=Servidor.TIPO_VINCULO_CHOICES,
        db_index=True,
    )
    quantidade_dias = models.PositiveIntegerField(default=1)
    quantidade_horas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=ZERO,
        validators=[MinValueValidator(ZERO)],
    )
    valor_calculado = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    valor_final = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    valor_editado_manualmente = models.BooleanField(default=False, db_index=True)
    motivo_edicao = models.TextField(blank=True)
    valor_anterior_edicao = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    valor_novo_edicao = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    editado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="valores_participacao_editados",
    )
    editado_em = models.DateTimeField(null=True, blank=True)

    servidor_nome_snapshot = models.CharField(max_length=150)
    servidor_id_snapshot = models.PositiveBigIntegerField()
    servidor_identificador_snapshot = models.CharField(max_length=8, blank=True)
    servico_nome_snapshot = models.CharField(max_length=100)
    servico_codigo_snapshot = models.CharField(max_length=50)
    salario_mensal_referencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    unidade_cobranca_snapshot = models.CharField(max_length=10)
    horas_base_diaria_snapshot = models.PositiveIntegerField(default=8)
    regra_calculo_snapshot = models.CharField(
        max_length=40,
        default=REGRA_RATEIO_HORAS_EQUIVALENTES,
    )
    valor_total_servico_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=ZERO,
    )
    quantidade_servidores_rateio_snapshot = models.PositiveIntegerField(default=1)

    servidor_excluido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participacoes_de_servidores_excluidos",
    )
    servidor_excluido_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participacoes_servidores_criadas",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participacoes_servidores_atualizadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Participação de servidor no evento"
        verbose_name_plural = "Participações de servidores nos eventos"
        ordering = ["evento", "servico__nome", "servidor_nome_snapshot", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["servidor", "evento", "servico"],
                condition=Q(servidor__isnull=False),
                name="uq_part_servidor_evento_serv",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_dias__gt=0) | Q(quantidade_horas__gt=0),
                name="ck_part_trabalho_pos",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_horas__gte=0),
                name="ck_part_horas_nn",
            ),
            models.CheckConstraint(
                condition=(
                    Q(valor_calculado__gte=0)
                    & Q(valor_final__gte=0)
                    & Q(valor_total_servico_snapshot__gte=0)
                ),
                name="ck_part_valores_nn",
            ),
            models.CheckConstraint(
                condition=(
                    Q(valor_editado_manualmente=False)
                    | ~Q(motivo_edicao="")
                ),
                name="ck_part_manual_motivo",
            ),
            models.CheckConstraint(
                condition=Q(tipo_vinculo__in=[Servidor.VINCULO_DIARISTA, Servidor.VINCULO_MENSALISTA]),
                name="ck_part_vinculo_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["evento", "servico", "tipo_vinculo"]),
            models.Index(fields=["servidor", "evento"]),
            models.Index(fields=["servidor_excluido_em", "evento"]),
        ]
        permissions = [
            ("view_custos_servidor", "Pode visualizar custos por servidor"),
            ("manage_participacao_servidor", "Pode gerenciar participação de servidor"),
            ("change_valor_distribuido_servidor", "Pode editar valor distribuído"),
            ("recalculate_custos_servidor", "Pode recalcular custos por servidor"),
            ("view_apropriacao_servidor", "Pode visualizar apropriação gerencial"),
        ]

    def __str__(self):
        sufixo = " — servidor excluído" if self.servidor_id is None else ""
        return f"{self.servidor_nome_snapshot}{sufixo} — {self.evento} — {self.servico_nome_snapshot}"

    @property
    def servidor_nome_exibicao(self):
        sufixo = " — servidor excluído" if self.servidor_id is None else ""
        return f"{self.servidor_nome_snapshot}{sufixo}"

    @property
    def unidades_rateio(self):
        if self.quantidade_horas > ZERO:
            return self.quantidade_horas
        return Decimal(self.quantidade_dias * self.horas_base_diaria_snapshot)

    def clean(self):
        super().clean()
        self.motivo_edicao = (self.motivo_edicao or "").strip()
        erros = {}
        if self.quantidade_horas < ZERO:
            erros["quantidade_horas"] = "A quantidade de horas não pode ser negativa."
        if self.quantidade_dias <= 0 and self.quantidade_horas <= ZERO:
            erros["quantidade_dias"] = "Informe ao menos dias ou horas trabalhadas."
        if self.valor_calculado < ZERO or self.valor_final < ZERO:
            erros["valor_final"] = "Os valores não podem ser negativos."
        if self.valor_editado_manualmente and not self.motivo_edicao:
            erros["motivo_edicao"] = "Informe o motivo da edição manual."
        if erros:
            raise ValidationError(erros)


class ServidorEventoDiaTrabalhado(models.Model):
    participacao = models.ForeignKey(
        "ParticipacaoServidorEvento",
        on_delete=models.CASCADE,
        related_name="dias_trabalhados",
    )
    data = models.DateField(db_index=True)
    quantidade_horas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dia trabalhado por servidor no evento"
        verbose_name_plural = "Dias trabalhados por servidores nos eventos"
        ordering = ["participacao_id", "data", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["participacao", "data"],
                name="uq_part_servidor_dia_trab",
            ),
            models.CheckConstraint(
                condition=Q(quantidade_horas__isnull=True)
                | Q(quantidade_horas__gt=0),
                name="ck_part_dia_horas_pos",
            ),
        ]

    def __str__(self):
        return f"{self.participacao.servidor_nome_snapshot} — {self.data:%d/%m/%Y}"

    def clean(self):
        super().clean()
        erros = {}
        if self.quantidade_horas is not None and self.quantidade_horas <= ZERO:
            erros["quantidade_horas"] = (
                "A quantidade de horas deve ser maior que zero quando informada."
            )
        if self.participacao_id and self.data:
            participacao = self._state.fields_cache.get("participacao")
            if participacao is None:
                participacao = ParticipacaoServidorEvento.objects.select_related(
                    "evento"
                ).get(pk=self.participacao_id)
            evento = participacao._state.fields_cache.get("evento")
            if evento is None:
                evento = participacao.evento
            if self.data < evento.data_inicio or self.data > evento.data_fim:
                erros["data"] = (
                    "A data trabalhada deve pertencer ao período do evento."
                )
        if erros:
            raise ValidationError(erros)
