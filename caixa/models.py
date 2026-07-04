from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.functions import Lower
from django.conf import settings
from simple_history.models import HistoricalRecords
from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
    STATUS_PLANEJADO,
    STATUS_REALIZADO,
    TIPO_FLUXO_CHOICES,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from .services_validacao_pagamentos import erro_caixa_insuficiente_para_aumento
from .utils_financeiros import decimal_zero, quantizar_moeda


class Servico(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    codigo = models.SlugField(max_length=50, unique=True)
    diaria_padrao = models.DecimalField(max_digits=10, decimal_places=2)
    horas_base_diaria = models.PositiveIntegerField(default=8)
    percentual_hora_extra = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.50")
    )
    usa_regra_especial = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["ativo", "nome"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(diaria_padrao__gte=0),
                name="ck_servico_diaria_nn",
            ),
            models.CheckConstraint(
                condition=models.Q(horas_base_diaria__gt=0),
                name="ck_servico_horas_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(percentual_hora_extra__gte=0),
                name="ck_servico_extra_nn",
            ),
            models.UniqueConstraint(
                Lower("nome"),
                name="uq_servico_nome_ci",
            ),
            models.UniqueConstraint(
                Lower("codigo"),
                name="uq_servico_codigo_ci",
            ),
        ]

    def __str__(self):
        return self.nome

    def _normalizar_campos_texto(self):
        self.nome = (self.nome or "").strip()
        self.codigo = (self.codigo or "").strip().lower()

    def clean(self):
        super().clean()
        self._normalizar_campos_texto()

    def save(self, *args, **kwargs):
        self._normalizar_campos_texto()
        super().save(*args, **kwargs)

    @property
    def meia_diaria(self):
        return self.diaria_padrao / Decimal("2")

    @property
    def valor_hora_normal(self):
        if self.horas_base_diaria <= 0:
            return Decimal("0.00")
        return self.diaria_padrao / Decimal(self.horas_base_diaria)

    @property
    def valor_hora_extra(self):
        return self.valor_hora_normal * self.percentual_hora_extra


class ConfiguracaoFinanceira(models.Model):
    nome = models.CharField(max_length=100, default="Padrão")
    valor_alimentacao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("20.00")
    )
    valor_transporte = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("14.00")
    )
    margem_lucro = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.30"),
        help_text="Use 0.30 para 30%"
    )
    aliquota_imposto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.06"),
        help_text="Use 0.06 para 6%"
    )
    ativa = models.BooleanField(default=True, db_index=True)
    data_inicio_vigencia = models.DateField(db_index=True)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração financeira"
        verbose_name_plural = "Configurações financeiras"
        ordering = ["-data_inicio_vigencia", "-id"]
        indexes = [
            models.Index(fields=["ativa", "data_inicio_vigencia"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_alimentacao__gte=0)
                    & models.Q(valor_transporte__gte=0)
                    & models.Q(margem_lucro__gte=0)
                    & models.Q(aliquota_imposto__gte=0)
                ),
                name="ck_config_fin_valores_nn",
            ),
            models.UniqueConstraint(
                fields=["ativa"],
                condition=models.Q(ativa=True),
                name="uq_config_fin_ativa",
            ),
        ]

    def __str__(self):
        status = "Ativa" if self.ativa else "Inativa"
        return f"{self.nome} - {status}"

    def clean(self):
        if self.margem_lucro < 0:
            raise ValidationError("A margem de lucro não pode ser negativa.")

        if self.aliquota_imposto < 0:
            raise ValidationError("A alíquota de imposto não pode ser negativa.")

        if self.ativa:
            qs = ConfiguracaoFinanceira.objects.filter(ativa=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError("Já existe outra configuração financeira ativa.")


class Cliente(models.Model):
    TIPO_PESSOA_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]

    nome_razao_social = models.CharField(max_length=150, db_index=True)
    nome_fantasia = models.CharField(max_length=150, blank=True)
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_PESSOA_CHOICES, default="PJ")
    cpf_cnpj = models.CharField(max_length=18, unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    responsavel = models.CharField(max_length=120, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome_razao_social"]
        indexes = [
            models.Index(fields=["ativo", "nome_razao_social"]),
            models.Index(fields=["tipo_pessoa", "ativo"]),
        ]

    def __str__(self):
        if self.nome_fantasia:
            return f"{self.nome_razao_social} ({self.nome_fantasia})"
        return self.nome_razao_social


class Orcamento(models.Model):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("enviado", "Enviado"),
        ("aprovado", "Aprovado"),
        ("recusado", "Recusado"),
        ("cancelado", "Cancelado"),
    ]

    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.PROTECT,
        related_name="orcamentos"
    )
    configuracao_financeira = models.ForeignKey(
        "ConfiguracaoFinanceira",
        on_delete=models.PROTECT,
        related_name="orcamentos"
    )
    numero = models.CharField(max_length=30, unique=True)
    nome_evento = models.CharField(max_length=150)
    data_evento = models.DateField(db_index=True)
    local = models.CharField(max_length=255, blank=True)
    validade = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho", db_index=True)
    observacoes = models.TextField(blank=True)

    subtotal_custos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    total_impostos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    total_lucro = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    total_venda = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Orçamento"
        verbose_name_plural = "Orçamentos"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["status", "data_evento"]),
            models.Index(fields=["cliente", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(subtotal_custos__gte=0)
                    & models.Q(total_impostos__gte=0)
                    & models.Q(total_lucro__gte=0)
                    & models.Q(total_venda__gte=0)
                ),
                name="ck_orcamento_totais_nn",
            ),
        ]

    def __str__(self):
        return f"{self.numero} - {self.cliente}"

    @property
    def contrato_codigo(self):
        return self.numero

    @property
    def contrato(self):
        return self.contrato_codigo

    @contrato.setter
    def contrato(self, valor):
        self.numero = valor

    def clean(self):
        erros = {}

        if not str(self.numero).strip():
            erros["numero"] = "O contrato do orçamento é obrigatório."

        if not str(self.nome_evento).strip():
            erros["nome_evento"] = "O nome do evento é obrigatório."

        if erros:
            raise ValidationError(erros)

    def recalcular_totais(self):
        prefetched_cache = getattr(self, "_prefetched_objects_cache", None)
        if prefetched_cache is not None:
            prefetched_cache.pop("itens", None)

        itens = self.itens.all()

        subtotal_custos = Decimal("0.00")
        total_impostos = Decimal("0.00")
        total_lucro = Decimal("0.00")
        total_venda = Decimal("0.00")

        for item in itens:
            subtotal_custos += item.custo_total
            total_impostos += item.valor_imposto
            total_lucro += item.lucro
            total_venda += item.preco_venda

        self.subtotal_custos = quantizar_moeda(subtotal_custos)
        self.total_impostos = quantizar_moeda(total_impostos)
        self.total_lucro = quantizar_moeda(total_lucro)
        self.total_venda = quantizar_moeda(total_venda)

        super().save(update_fields=[
            "subtotal_custos",
            "total_impostos",
            "total_lucro",
            "total_venda",
            "atualizado_em",
        ])

    def sincronizar_custos_servicos_evento(self, evento):
        from .services_orcamentos import sincronizar_custos_servicos_orcamento

        sincronizar_custos_servicos_orcamento(self, evento)

    def sincronizar_custos_extras_evento(self, evento):
        from .services_orcamentos import sincronizar_custos_extras_orcamento

        sincronizar_custos_extras_orcamento(self, evento)

    def sincronizar_evento_aprovado(
        self,
        sincronizar_receita_operacional=True,
        sincronizar_custos_servico=True,
        sincronizar_custos_extras=True,
    ):
        from .services_orcamentos import sincronizar_evento_do_orcamento_aprovado

        return sincronizar_evento_do_orcamento_aprovado(
            self,
            sincronizar_receita_operacional=sincronizar_receita_operacional,
            sincronizar_custos_servico=sincronizar_custos_servico,
            sincronizar_custos_extras=sincronizar_custos_extras,
        )

    def aprovar_e_gerar_evento(self):
        if not self.pk:
            raise ValidationError("Salve o orçamento antes de aprovar.")

        if not self.itens.exists():
            raise ValidationError("Não é possível aprovar um orçamento sem itens.")

        self.full_clean()
        self.recalcular_totais()

        self.status = "aprovado"
        super().save(update_fields=["status", "atualizado_em"])

        from .services_orcamentos import criar_ou_atualizar_evento_do_orcamento

        evento = criar_ou_atualizar_evento_do_orcamento(self)

        evento.gerar_movimentacoes_previstas()
        self.sincronizar_custos_servicos_evento(evento)
        self.sincronizar_custos_extras_evento(evento)

        return evento


class OrcamentoItem(models.Model):
    orcamento = models.ForeignKey(
        "Orcamento",
        on_delete=models.CASCADE,
        related_name="itens"
    )
    servico = models.ForeignKey(
        "Servico",
        on_delete=models.PROTECT,
        related_name="itens_orcamento"
    )

    horas_por_dia = models.PositiveIntegerField()
    quantidade_dias = models.PositiveIntegerField(default=1)
    quantidade_pessoas = models.PositiveIntegerField(default=1)

    valor_diaria_usada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    valor_alimentacao_usado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    valor_transporte_usado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    margem_lucro_usada = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )
    aliquota_imposto_usada = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )
    usa_regra_especial = models.BooleanField(default=False)

    valor_dia_por_pessoa = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    quantidade_alimentacao_por_dia = models.PositiveIntegerField(default=0)
    quantidade_transporte_por_dia = models.PositiveIntegerField(default=0)

    custo_servico_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gasto_alimentacao_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gasto_transporte_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valor_horas_extras_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    custo_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valor_com_margem = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valor_imposto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    lucro = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    preco_venda = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Item do orçamento"
        verbose_name_plural = "Itens do orçamento"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["orcamento", "servico"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(horas_por_dia__gt=0)
                    & models.Q(quantidade_dias__gt=0)
                    & models.Q(quantidade_pessoas__gt=0)
                ),
                name="ck_orc_item_qtd_pos",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valor_diaria_usada__gte=0)
                    & models.Q(valor_alimentacao_usado__gte=0)
                    & models.Q(valor_transporte_usado__gte=0)
                    & models.Q(margem_lucro_usada__gte=0)
                    & models.Q(aliquota_imposto_usada__gte=0)
                    & models.Q(valor_dia_por_pessoa__gte=0)
                    & models.Q(custo_servico_total__gte=0)
                    & models.Q(gasto_alimentacao_total__gte=0)
                    & models.Q(gasto_transporte_total__gte=0)
                    & models.Q(valor_horas_extras_total__gte=0)
                    & models.Q(custo_total__gte=0)
                    & models.Q(valor_com_margem__gte=0)
                    & models.Q(valor_imposto__gte=0)
                    & models.Q(lucro__gte=0)
                    & models.Q(preco_venda__gte=0)
                ),
                name="ck_orc_item_valores_nn",
            ),
        ]

    def __str__(self):
        return f"{self.orcamento.numero} - {self.servico.nome}"

    def clean(self):
        erros = {}

        if self.horas_por_dia <= 0:
            erros["horas_por_dia"] = "Horas por dia deve ser maior que zero."

        if self.quantidade_dias <= 0:
            erros["quantidade_dias"] = "Quantidade de dias deve ser maior que zero."

        if self.quantidade_pessoas <= 0:
            erros["quantidade_pessoas"] = "Quantidade de pessoas deve ser maior que zero."

        if erros:
            raise ValidationError(erros)

    def arredondar2(self, valor):
        return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calcular_meia_diaria(self):
        return self.arredondar2(self.valor_diaria_usada / Decimal("2"))

    def calcular_hora_normal(self):
        horas_base = self.servico.horas_base_diaria or 8
        return self.arredondar2(self.valor_diaria_usada / Decimal(horas_base))

    def calcular_hora_extra(self):
        hora_normal = self.calcular_hora_normal()
        percentual = self.servico.percentual_hora_extra or Decimal("1.50")
        return self.arredondar2(hora_normal * percentual)

    def calcular_valor_turno_regra_especial(self, horas):
        if horas <= 4:
            return self.calcular_meia_diaria()

        if horas <= 8:
            return self.valor_diaria_usada

        extras = horas - 8
        return self.arredondar2(
            self.valor_diaria_usada + (Decimal(extras) * self.calcular_hora_extra())
        )

    def calcular_valor_turno_normal(self, horas):
        meia_diaria = self.calcular_meia_diaria()
        hora_normal = self.calcular_hora_normal()
        hora_extra = self.calcular_hora_extra()

        if horas <= 4:
            return meia_diaria

        if horas <= 8:
            horas_apos_4 = horas - 4
            return self.arredondar2(
                meia_diaria + (Decimal(horas_apos_4) * hora_normal)
            )

        horas_ate_8 = 4
        horas_extras = horas - 8

        return self.arredondar2(
            meia_diaria +
            (Decimal(horas_ate_8) * hora_normal) +
            (Decimal(horas_extras) * hora_extra)
        )

    def calcular_valor_dia(self):
        horas = self.horas_por_dia

        if self.usa_regra_especial:
            return self.calcular_valor_turno_regra_especial(horas)

        restante = horas
        total = Decimal("0.00")

        while restante > 0:
            turno = min(restante, 10)
            total += self.calcular_valor_turno_normal(turno)
            restante -= turno

        return self.arredondar2(total)

    def calcular_quantidade_alimentacao_regra_especial(self, horas):
        restante = horas
        total = 0

        while restante > 0:
            turno = min(restante, 12)

            if turno <= 4:
                total += 0
            elif turno <= 8:
                total += 1
            else:
                total += 2

            restante -= turno

        return total

    def calcular_quantidade_alimentacao(self):
        horas = self.horas_por_dia

        if self.usa_regra_especial:
            return self.calcular_quantidade_alimentacao_regra_especial(horas)

        restante = horas
        total = 0

        while restante > 0:
            turno = min(restante, 10)

            if turno <= 4:
                total += 0
            elif turno <= 8:
                total += 1
            else:
                total += 2

            restante -= turno

        return total

    def calcular_quantidade_transporte(self):
        horas = self.horas_por_dia

        if self.usa_regra_especial:
            return 1

        restante = horas
        total = 0

        while restante > 0:
            turno = min(restante, 10)
            total += 1
            restante -= turno

        return total

    def calcular_valor_horas_extras_por_pessoa_dia(self):
        valor_hora_extra = self.calcular_hora_extra()
        horas = self.horas_por_dia

        if self.usa_regra_especial:
            horas_extras = horas - 8 if horas > 8 else 0
            return self.arredondar2(Decimal(horas_extras) * valor_hora_extra)

        restante = horas
        total = Decimal("0.00")

        while restante > 0:
            turno = min(restante, 10)

            if turno > 8:
                horas_extras_turno = turno - 8
                total += Decimal(horas_extras_turno) * valor_hora_extra

            restante -= turno

        return self.arredondar2(total)

    def calcular_totais(self):
        valor_dia = self.calcular_valor_dia()
        qtd_alimentacao = self.calcular_quantidade_alimentacao()
        qtd_transporte = self.calcular_quantidade_transporte()

        alimentacao_dia = self.arredondar2(
            Decimal(qtd_alimentacao) * self.valor_alimentacao_usado
        )
        transporte_dia = self.arredondar2(
            Decimal(qtd_transporte) * self.valor_transporte_usado
        )

        custo_servico_total = self.arredondar2(
            valor_dia * self.quantidade_dias * self.quantidade_pessoas
        )
        gasto_alimentacao_total = self.arredondar2(
            alimentacao_dia * self.quantidade_dias * self.quantidade_pessoas
        )
        gasto_transporte_total = self.arredondar2(
            transporte_dia * self.quantidade_dias * self.quantidade_pessoas
        )

        custo_total = self.arredondar2(
            custo_servico_total + gasto_alimentacao_total + gasto_transporte_total
        )

        valor_com_margem = self.arredondar2(
            custo_total * (Decimal("1.00") + self.margem_lucro_usada)
        )
        valor_imposto = self.arredondar2(
            valor_com_margem * self.aliquota_imposto_usada
        )
        preco_venda = self.arredondar2(valor_com_margem + valor_imposto)
        lucro = self.arredondar2(valor_com_margem - custo_total)

        valor_horas_extras_total = self.arredondar2(
            self.calcular_valor_horas_extras_por_pessoa_dia() *
            self.quantidade_dias *
            self.quantidade_pessoas
        )

        self.valor_dia_por_pessoa = valor_dia
        self.quantidade_alimentacao_por_dia = qtd_alimentacao
        self.quantidade_transporte_por_dia = qtd_transporte
        self.custo_servico_total = custo_servico_total
        self.gasto_alimentacao_total = gasto_alimentacao_total
        self.gasto_transporte_total = gasto_transporte_total
        self.valor_horas_extras_total = valor_horas_extras_total
        self.custo_total = custo_total
        self.valor_com_margem = valor_com_margem
        self.valor_imposto = valor_imposto
        self.lucro = lucro
        self.preco_venda = preco_venda

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.valor_diaria_usada = self.servico.diaria_padrao
            self.usa_regra_especial = self.servico.usa_regra_especial

            config = self.orcamento.configuracao_financeira
            self.valor_alimentacao_usado = config.valor_alimentacao
            self.valor_transporte_usado = config.valor_transporte
            self.margem_lucro_usada = config.margem_lucro
            self.aliquota_imposto_usada = config.aliquota_imposto

        with transaction.atomic():
            self.full_clean()
            self.calcular_totais()
            super().save(*args, **kwargs)
            self.orcamento.recalcular_totais()
            self.orcamento.sincronizar_evento_aprovado()


class Evento(models.Model):
    STATUS_CHOICES = [
        ("planejado", "Planejado"),
        ("confirmado", "Confirmado"),
        ("em_andamento", "Em andamento"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
    ]

    orcamento = models.OneToOneField(
        "Orcamento",
        on_delete=models.PROTECT,
        related_name="evento",
        null=True,
        blank=True,
    )
    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.PROTECT,
        related_name="eventos"
    )
    numero = models.CharField(max_length=30, unique=True)
    nome_evento = models.CharField(max_length=150)
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(db_index=True)
    local = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planejado", db_index=True)
    observacoes = models.TextField(blank=True)

    valor_total_previsto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    custo_total_previsto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    lucro_previsto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    valor_total_realizado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    custo_total_realizado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    lucro_realizado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ["-data_inicio", "-id"]
        indexes = [
            models.Index(fields=["status", "data_inicio"]),
            models.Index(fields=["cliente", "data_inicio"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(data_fim__gte=models.F("data_inicio")),
                name="ck_evento_periodo_valido",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valor_total_previsto__gte=0)
                    & models.Q(custo_total_previsto__gte=0)
                    & models.Q(valor_total_realizado__gte=0)
                    & models.Q(custo_total_realizado__gte=0)
                ),
                name="ck_evento_valores_nn",
            ),
        ]

    def __str__(self):
        return f"{self.numero} - {self.nome_evento}"

    @property
    def contrato_codigo(self):
        if self.orcamento_id:
            orcamento_carregado = self._state.fields_cache.get("orcamento")
            if orcamento_carregado is not None:
                return orcamento_carregado.numero

        numero = str(self.numero or "").strip()
        if numero.upper().startswith("EVT-"):
            return numero[4:].strip() or numero
        return numero

    @property
    def contrato(self):
        return self.contrato_codigo

    @contrato.setter
    def contrato(self, valor):
        self.numero = valor

    def clean(self):
        erros = {}

        if self.data_fim < self.data_inicio:
            erros["data_fim"] = "A data final não pode ser menor que a data inicial."

        if erros:
            raise ValidationError(erros)

    @property
    def resultado_financeiro_previsto(self):
        return quantizar_moeda(self.valor_total_previsto - self.custo_total_previsto)

    @property
    def resultado_financeiro_realizado(self):
        return quantizar_moeda(self.valor_total_realizado - self.custo_total_realizado)

    @property
    def saldo_previsto(self):
        return self.resultado_financeiro_previsto

    @property
    def saldo_realizado(self):
        return self.resultado_financeiro_realizado

    def recalcular_realizado(self):
        from .services_evento import recalcular_totais_realizados_evento

        recalcular_totais_realizados_evento(self)

    def recalcular_receita_prevista(self):
        from .services_evento import recalcular_receita_prevista_evento

        recalcular_receita_prevista_evento(self)

    def recalcular_custo_previsto(self):
        from .services_evento import recalcular_custo_previsto_evento

        recalcular_custo_previsto_evento(self)

    def gerar_movimentacoes_previstas(self):
        from .services_evento import gerar_movimentacoes_previstas_evento

        gerar_movimentacoes_previstas_evento(self)

    @classmethod
    def criar_a_partir_do_orcamento(cls, orcamento):
        evento = cls.objects.create(
            orcamento=orcamento,
            cliente=orcamento.cliente,
            numero=f"EVT-{orcamento.numero}",
            nome_evento=orcamento.nome_evento,
            data_inicio=orcamento.data_evento,
            data_fim=orcamento.data_evento,
            local=orcamento.local,
            status="planejado",
            observacoes=orcamento.observacoes,
            valor_total_previsto=orcamento.total_venda,
            custo_total_previsto=quantizar_moeda(orcamento.subtotal_custos + orcamento.total_impostos),
            lucro_previsto=orcamento.total_lucro,
        )
        return evento


class ReceitaOperacional(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("parcial", "Parcial"),
        ("recebido", "Recebido"),
        ("vencido", "Vencido"),
        ("cancelado", "Cancelado"),
    ]

    FORMA_PAGAMENTO_CHOICES = [
        ("pix", "Pix"),
        ("dinheiro", "Dinheiro"),
        ("transferencia", "Transferência"),
        ("boleto", "Boleto"),
        ("cartao", "Cartão"),
        ("outro", "Outro"),
    ]

    evento = models.ForeignKey(
        "Evento",
        on_delete=models.CASCADE,
        related_name="receitas"
    )
    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.PROTECT,
        related_name="receitas_operacionais"
    )
    descricao = models.CharField(max_length=255)
    valor_previsto = models.DecimalField(max_digits=12, decimal_places=2)
    valor_recebido = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    data_vencimento = models.DateField(db_index=True)
    data_recebimento = models.DateField(null=True, blank=True, db_index=True)
    forma_pagamento = models.CharField(
        max_length=20,
        choices=FORMA_PAGAMENTO_CHOICES,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente", db_index=True)
    baixado_manualmente = models.BooleanField(default=False, verbose_name="Baixa manual")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")
    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Receita operacional"
        verbose_name_plural = "Receitas operacionais"
        ordering = ["data_vencimento", "id"]
        indexes = [
            models.Index(fields=["status", "data_vencimento"]),
            models.Index(fields=["cliente", "status"]),
            models.Index(fields=["evento", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_previsto__gte=0)
                    & models.Q(valor_recebido__gte=0)
                ),
                name="ck_receita_valores_nn",
            ),
        ]

    def __str__(self):
        return f"{self.evento.numero} - {self.descricao}"

    @property
    def saldo_a_receber(self):
        if self.status in ["recebido", "cancelado"] or self.baixado_manualmente:
            return Decimal("0.00")

        valor_previsto = decimal_zero(self.valor_previsto)
        valor_recebido = decimal_zero(self.valor_recebido)
        saldo = valor_previsto - valor_recebido
        return saldo if saldo > 0 else Decimal("0.00")

    @property
    def valor_pendente_recebimento(self):
        return self.saldo_a_receber

    @property
    def contas_pendentes(self):
        return self.valor_pendente_recebimento

    def clean(self):
        erros = {}

        if self.valor_previsto < 0:
            erros["valor_previsto"] = "O valor previsto não pode ser negativo."

        if self.valor_recebido < 0:
            erros["valor_recebido"] = "O valor recebido não pode ser negativo."

        if self.baixado_manualmente and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        if erros:
            raise ValidationError(erros)

    def atualizar_status(self):
        if self.status == "cancelado":
            return

        if self.baixado_manualmente:
            self.status = "recebido"
            return

        if self.status == "recebido" and self.valor_recebido > Decimal("0.00"):
            return

        if self.valor_recebido <= Decimal("0.00"):
            self.status = "pendente"
        elif self.valor_recebido < self.valor_previsto:
            self.status = "parcial"
        else:
            self.status = "recebido"

    def save(self, *args, **kwargs):
        self.full_clean()
        self.atualizar_status()
        super().save(*args, **kwargs)
        self.evento.recalcular_realizado()

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receitas_criadas"
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receitas_atualizadas"
    )


class DespesaOperacional(models.Model):
    ORIGEM_MANUAL = "manual"
    ORIGEM_CUSTO_SERVICO = "custo_servico"
    ORIGEM_CUSTO_EXTRA = "custo_extra"

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("parcial", "Parcial"),
        ("pago", "Pago"),
        ("vencido", "Vencido"),
        ("cancelado", "Cancelado"),
    ]

    FORMA_PAGAMENTO_CHOICES = [
        ("pix", "Pix"),
        ("dinheiro", "Dinheiro"),
        ("transferencia", "Transferência"),
        ("boleto", "Boleto"),
        ("cartao", "Cartão"),
        ("outro", "Outro"),
    ]

    ORIGEM_CHOICES = [
        (ORIGEM_MANUAL, "Manual"),
        (ORIGEM_CUSTO_SERVICO, "Custo de serviço"),
        (ORIGEM_CUSTO_EXTRA, "Custo extra"),
    ]

    ORIGEM_CUSTO_SERVICO_TIPO_CHOICES = [
        ("diarias", "Diárias"),
        ("alimentacao", "Alimentação"),
        ("transporte", "Transporte"),
    ]

    CATEGORIA_CHOICES = [
        ("mao_obra", "Mão de obra"),
        ("alimentacao", "Alimentação"),
        ("transporte", "Transporte"),
        ("imposto", "Imposto"),
        ("uniforme", "Uniforme"),
        ("material", "Material"),
        ("comissao", "Comissão"),
        ("outros", "Outros"),
    ]

    CUSTOS_SERVICO_DERIVADOS = {
        "mao_obra": ("Mão de obra prevista", "valor_diarias", "diarias"),
        "alimentacao": ("Alimentação prevista", "valor_alimentacao", "alimentacao"),
        "transporte": ("Transporte previsto", "valor_transporte", "transporte"),
    }

    evento = models.ForeignKey(
        "Evento",
        on_delete=models.CASCADE,
        related_name="despesas"
    )
    descricao = models.CharField(max_length=255)
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, db_index=True)
    valor_previsto = models.DecimalField(max_digits=12, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    data_vencimento = models.DateField(db_index=True)
    data_pagamento = models.DateField(null=True, blank=True, db_index=True)
    forma_pagamento = models.CharField(
        max_length=20,
        choices=FORMA_PAGAMENTO_CHOICES,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente", db_index=True)
    baixado_manualmente = models.BooleanField(default=False, verbose_name="Baixa manual")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")
    observacao = models.TextField(blank=True)
    origem = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default=ORIGEM_MANUAL,
        db_index=True,
    )
    origem_custo_servico_tipo = models.CharField(
        max_length=20,
        choices=ORIGEM_CUSTO_SERVICO_TIPO_CHOICES,
        blank=True,
    )
    origem_custo_extra = models.ForeignKey(
        "EventoCustoExtra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="despesas_operacionais",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Despesa operacional"
        verbose_name_plural = "Despesas operacionais"
        ordering = ["data_vencimento", "id"]
        indexes = [
            models.Index(fields=["status", "data_vencimento"]),
            models.Index(fields=["categoria", "data_vencimento"]),
            models.Index(fields=["evento", "status"]),
            models.Index(fields=["origem", "evento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_previsto__gte=0)
                    & models.Q(valor_pago__gte=0)
                ),
                name="ck_despesa_valores_nn",
            ),
        ]

    def __str__(self):
        return f"{self.evento.numero} - {self.descricao}"

    @property
    def saldo_a_pagar(self):
        if self.status in ["pago", "cancelado"] or self.baixado_manualmente:
            return Decimal("0.00")

        valor_previsto = decimal_zero(self.valor_previsto)
        valor_pago = decimal_zero(self.valor_pago)
        return quantizar_moeda(valor_previsto - valor_pago)

    @property
    def valor_pendente_pagamento(self):
        return self.saldo_a_pagar

    @property
    def contas_pendentes(self):
        return self.valor_pendente_pagamento

    @property
    def origem_pagamento(self):
        return self.origem

    def _foi_derivada_de_custo_servico(self):
        return self.origem == self.ORIGEM_CUSTO_SERVICO

    @property
    def origem_legada_inferida(self):
        if self.descricao.startswith("Custo extra: "):
            return self.ORIGEM_CUSTO_EXTRA

        regra = self.CUSTOS_SERVICO_DERIVADOS.get(self.categoria)
        if not regra or not self.evento_id:
            return self.ORIGEM_MANUAL

        descricao_esperada, campo_valor, _tipo_origem = regra
        if self.descricao != descricao_esperada:
            return self.ORIGEM_MANUAL

        custos_prefetchados = getattr(self.evento, "_prefetched_objects_cache", {}).get(
            "custos_servicos"
        )
        if custos_prefetchados is not None:
            if any(
                decimal_zero(getattr(custo, campo_valor)) > Decimal("0.00")
                for custo in custos_prefetchados
            ):
                return self.ORIGEM_CUSTO_SERVICO
            return self.ORIGEM_MANUAL

        if self.evento.custos_servicos.filter(
            **{f"{campo_valor}__gt": Decimal("0.00")}
        ).exists():
            return self.ORIGEM_CUSTO_SERVICO

        return self.ORIGEM_MANUAL

    @property
    def origem_pagamento_display(self):
        if self.origem_pagamento == self.ORIGEM_CUSTO_EXTRA:
            return "Custo extra"

        if self.origem_pagamento == self.ORIGEM_CUSTO_SERVICO:
            return "Custo de serviço"

        return "Manual"

    @property
    def pode_editar_na_lista(self):
        return self.origem_pagamento == self.ORIGEM_MANUAL

    def _manual_usa_linha_reservada_de_custo_servico(self):
        if self.origem != self.ORIGEM_MANUAL or not self.evento_id:
            return False

        regra = self.CUSTOS_SERVICO_DERIVADOS.get(self.categoria)
        if not regra:
            return False

        descricao_esperada, campo_valor, _tipo_origem = regra
        if self.descricao != descricao_esperada:
            return False

        return self.evento.custos_servicos.filter(
            **{f"{campo_valor}__gt": Decimal("0.00")}
        ).exists()

    def _edicao_de_origem_sincronizada_permitida(self):
        return bool(getattr(self, "_sincronizacao_origem", False))

    def clean(self):
        erros = {}

        if self.valor_previsto < 0:
            erros["valor_previsto"] = "O valor previsto não pode ser negativo."

        if self.valor_pago < 0:
            erros["valor_pago"] = "O valor pago não pode ser negativo."

        if self.baixado_manualmente and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        if self._manual_usa_linha_reservada_de_custo_servico():
            erros["descricao"] = (
                "Este custo estruturado de serviço deve ser pago em "
                "'Pagamentos de custos de serviço'. Use uma descrição diferente "
                "apenas quando for uma despesa operacional manual adicional."
            )

        if (
            self.origem != self.ORIGEM_MANUAL
            and not self._edicao_de_origem_sincronizada_permitida()
        ):
            erros["__all__"] = (
                "Despesas operacionais sincronizadas devem ser atualizadas pela "
                "origem correta: pagamentos de custos de serviço ou pagamentos "
                "de custos extras."
            )

        if (
            self.origem == self.ORIGEM_CUSTO_SERVICO
            and not self.origem_custo_servico_tipo
        ):
            erros["origem_custo_servico_tipo"] = (
                "Informe o tipo do custo de serviço que originou a despesa."
            )

        if (
            self.origem != self.ORIGEM_CUSTO_SERVICO
            and self.origem_custo_servico_tipo
        ):
            erros["origem_custo_servico_tipo"] = (
                "Tipo de custo de serviço só deve ser preenchido para despesas dessa origem."
            )

        if (
            self.origem != self.ORIGEM_CUSTO_EXTRA
            and self.origem_custo_extra_id
        ):
            erros["origem_custo_extra"] = (
                "Custo extra de origem só deve ser preenchido para despesas dessa origem."
            )

        if erros:
            raise ValidationError(erros)

        if (
            self.valor_pago > Decimal("0.00")
            and self.origem_pagamento == self.ORIGEM_MANUAL
        ):
            erro_caixa = erro_caixa_insuficiente_para_aumento(
                self.__class__,
                self.pk,
                "valor_pago",
                self.valor_pago,
                self.data_pagamento or self.data_vencimento,
            )
            if erro_caixa:
                raise ValidationError({"valor_pago": erro_caixa})

    def atualizar_status(self):
        if self.status == "cancelado":
            return

        if self.baixado_manualmente:
            self.status = "pago"
            return

        if self.status == "pago" and self.valor_pago > Decimal("0.00"):
            return

        if self.valor_previsto == Decimal("0.00") and self.valor_pago == Decimal("0.00"):
            self.status = "cancelado"
        elif self.valor_pago <= Decimal("0.00"):
            self.status = "pendente"
        elif self.valor_pago < self.valor_previsto:
            self.status = "parcial"
        else:
            self.status = "pago"

    def save(self, *args, **kwargs):
        sincronizacao_origem = kwargs.pop("sincronizacao_origem", False)
        self._sincronizacao_origem = sincronizacao_origem
        try:
            self.full_clean()
            self.atualizar_status()
            super().save(*args, **kwargs)
        finally:
            self._sincronizacao_origem = False

        self.evento.recalcular_realizado()

    criado_por = models.ForeignKey(
       settings.AUTH_USER_MODEL,
       on_delete=models.SET_NULL,
       null=True,
       blank=True,
       related_name="despesas_criadas"
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="despesas_atualizadas"
    )


ORIGENS_LANCAMENTO_FINANCEIRO = (
    "receita_operacional",
    "despesa_operacional",
    "custo_fixo",
    "pagamento_custo_servico",
    "pagamento_custo_extra",
    "pagamento_parcela_divida",
    "investimento",
    "financiamento_movimentacao",
)


def q_origem_exclusiva_lancamento(campo_origem):
    condicao = models.Q(**{f"{campo_origem}__isnull": False})

    for outro_campo in ORIGENS_LANCAMENTO_FINANCEIRO:
        if outro_campo == campo_origem:
            continue
        condicao &= models.Q(**{f"{outro_campo}__isnull": True})

    return condicao


def q_origem_unica_lancamento():
    condicao = models.Q()

    for campo_origem in ORIGENS_LANCAMENTO_FINANCEIRO:
        condicao |= q_origem_exclusiva_lancamento(campo_origem)

    return condicao


class LancamentoFinanceiro(models.Model):
    FLUXO_FCO = "fco"
    FLUXO_FCI = "fci"
    FLUXO_FCF = "fcf"

    FLUXO_CHOICES = (
        (FLUXO_FCO, "FCO - Fluxo de Caixa Operacional"),
        (FLUXO_FCI, "FCI - Fluxo de Investimento"),
        (FLUXO_FCF, "FCF - Fluxo de Financiamento"),
    )

    NATUREZA_RECEITA_OPERACIONAL = "receita_operacional"
    NATUREZA_DESPESA_OPERACIONAL = "despesa_operacional"
    NATUREZA_CUSTO_SERVICO = "custo_servico"
    NATUREZA_CUSTO_EXTRA = "custo_extra"
    NATUREZA_PARCELA_DIVIDA = "parcela_divida"
    NATUREZA_INVESTIMENTO = "investimento"
    NATUREZA_FINANCIAMENTO = "financiamento"

    NATUREZA_CHOICES = (
        (NATUREZA_RECEITA_OPERACIONAL, "Receita operacional"),
        (NATUREZA_DESPESA_OPERACIONAL, "Despesa operacional"),
        (NATUREZA_CUSTO_SERVICO, "Custo de serviço"),
        (NATUREZA_CUSTO_EXTRA, "Custo extra"),
        (NATUREZA_PARCELA_DIVIDA, "Parcela de dívida"),
        (NATUREZA_INVESTIMENTO, "Investimento"),
        (NATUREZA_FINANCIAMENTO, "Financiamento"),
    )

    STATUS_CHOICES = (
        (STATUS_PLANEJADO, "Planejado"),
        (STATUS_REALIZADO, "Realizado"),
        (STATUS_CANCELADO, "Cancelado"),
    )

    REGRAS_ORIGEM = {
        "receita_operacional": {
            "tipo": TIPO_FLUXO_ENTRADA,
            "fluxo": FLUXO_FCO,
            "natureza": NATUREZA_RECEITA_OPERACIONAL,
        },
        "despesa_operacional": {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": FLUXO_FCO,
            "natureza": NATUREZA_DESPESA_OPERACIONAL,
        },
        "custo_fixo": {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": FLUXO_FCO,
            "natureza": NATUREZA_DESPESA_OPERACIONAL,
        },
        "pagamento_custo_servico": {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": FLUXO_FCO,
            "natureza": NATUREZA_CUSTO_SERVICO,
        },
        "pagamento_custo_extra": {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": FLUXO_FCO,
            "natureza": NATUREZA_CUSTO_EXTRA,
        },
        "pagamento_parcela_divida": {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": FLUXO_FCF,
            "natureza": NATUREZA_PARCELA_DIVIDA,
        },
        "investimento": {
            "fluxo": FLUXO_FCI,
            "natureza": NATUREZA_INVESTIMENTO,
        },
        "financiamento_movimentacao": {
            "fluxo": FLUXO_FCF,
            "natureza": NATUREZA_FINANCIAMENTO,
        },
    }

    tipo = models.CharField(max_length=10, choices=TIPO_FLUXO_CHOICES, db_index=True)
    fluxo = models.CharField(max_length=10, choices=FLUXO_CHOICES, db_index=True)
    natureza = models.CharField(max_length=40, choices=NATUREZA_CHOICES, db_index=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_lancamento = models.DateField(db_index=True)
    forma = models.CharField(max_length=30, blank=True)
    descricao = models.CharField(max_length=255)
    observacao = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REALIZADO,
        db_index=True,
    )

    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    evento = models.ForeignKey(
        "Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )

    receita_operacional = models.ForeignKey(
        "ReceitaOperacional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    despesa_operacional = models.ForeignKey(
        "DespesaOperacional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    custo_fixo = models.ForeignKey(
        "CustoFixo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    pagamento_custo_servico = models.ForeignKey(
        "PagamentoEventoCustoServico",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    pagamento_custo_extra = models.ForeignKey(
        "PagamentoEventoCustoExtra",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    pagamento_parcela_divida = models.ForeignKey(
        "PagamentoParcelaDivida",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    investimento = models.ForeignKey(
        "Investimento",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )
    financiamento_movimentacao = models.ForeignKey(
        "FinanciamentoMovimentacao",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros",
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos_financeiros_atualizados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Lançamento financeiro"
        verbose_name_plural = "Lançamentos financeiros"
        ordering = ["-data_lancamento", "-id"]
        indexes = [
            models.Index(fields=["data_lancamento", "tipo"]),
            models.Index(fields=["fluxo", "data_lancamento"]),
            models.Index(fields=["natureza", "data_lancamento"]),
            models.Index(fields=["status", "data_lancamento"]),
            models.Index(fields=["evento", "data_lancamento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gt=0),
                name="ck_lanc_fin_valor_pos",
            ),
            models.CheckConstraint(
                condition=q_origem_unica_lancamento(),
                name="ck_lanc_fin_origem_unica",
            ),
            models.UniqueConstraint(
                fields=["receita_operacional"],
                condition=models.Q(receita_operacional__isnull=False),
                name="uq_lanc_fin_receita",
            ),
            models.UniqueConstraint(
                fields=["despesa_operacional"],
                condition=models.Q(despesa_operacional__isnull=False),
                name="uq_lanc_fin_despesa",
            ),
            models.UniqueConstraint(
                fields=["custo_fixo"],
                condition=models.Q(custo_fixo__isnull=False),
                name="uq_lanc_fin_custo_fixo",
            ),
            models.UniqueConstraint(
                fields=["pagamento_custo_servico"],
                condition=models.Q(pagamento_custo_servico__isnull=False),
                name="uq_lanc_fin_pag_serv",
            ),
            models.UniqueConstraint(
                fields=["pagamento_custo_extra"],
                condition=models.Q(pagamento_custo_extra__isnull=False),
                name="uq_lanc_fin_pag_extra",
            ),
            models.UniqueConstraint(
                fields=["pagamento_parcela_divida"],
                condition=models.Q(pagamento_parcela_divida__isnull=False),
                name="uq_lanc_fin_pag_parc",
            ),
            models.UniqueConstraint(
                fields=["investimento"],
                condition=models.Q(investimento__isnull=False),
                name="uq_lanc_fin_invest",
            ),
            models.UniqueConstraint(
                fields=["financiamento_movimentacao"],
                condition=models.Q(financiamento_movimentacao__isnull=False),
                name="uq_lanc_fin_financ",
            ),
        ]

    def __str__(self):
        return f"{self.data_lancamento} - {self.get_tipo_display()} - {self.valor}"

    @property
    def data(self):
        return self.data_lancamento

    def campos_origem_preenchidos(self):
        return [
            campo
            for campo in ORIGENS_LANCAMENTO_FINANCEIRO
            if getattr(self, f"{campo}_id")
        ]

    def clean(self):
        erros = {}

        if self.valor <= Decimal("0.00"):
            erros["valor"] = "O valor do lançamento deve ser maior que zero."

        origens = self.campos_origem_preenchidos()
        if len(origens) != 1:
            erros["__all__"] = (
                "Informe exatamente uma origem para o lançamento financeiro."
            )
        else:
            self.validar_coerencia_origem(origens[0], erros)

        if erros:
            raise ValidationError(erros)

    def validar_coerencia_origem(self, origem, erros):
        regra = self.REGRAS_ORIGEM[origem]
        tipo_esperado = regra.get("tipo")

        if tipo_esperado and self.tipo != tipo_esperado:
            erros["tipo"] = (
                "O tipo do lançamento não corresponde à origem financeira."
            )

        if self.fluxo != regra["fluxo"]:
            erros["fluxo"] = (
                "O fluxo do lançamento não corresponde à origem financeira."
            )

        if self.natureza != regra["natureza"]:
            erros["natureza"] = (
                "A natureza do lançamento não corresponde à origem financeira."
            )

        if origem == "investimento" and self.investimento_id:
            self.validar_tipo_por_objeto_origem(self.investimento, erros)
        elif origem == "financiamento_movimentacao" and self.financiamento_movimentacao_id:
            self.validar_tipo_por_objeto_origem(
                self.financiamento_movimentacao,
                erros,
            )

    def validar_tipo_por_objeto_origem(self, origem_objeto, erros):
        if origem_objeto.tipo_fluxo != self.tipo:
            erros["tipo"] = (
                "O tipo do lançamento deve acompanhar o tipo de fluxo da origem."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


STATUS_LIQUIDADO_CANONICO = "liquidado"
FONTE_ESCRITA_LEGACY_ADAPTER_SYNCED = "legacyAdapterSynced"
FONTE_ESCRITA_CANONICAL_FIRST = "canonicalFirst"
FONTE_ESCRITA_BAIXA_CHOICES = (
    (FONTE_ESCRITA_LEGACY_ADAPTER_SYNCED, "Adapter legado sincronizado"),
    (FONTE_ESCRITA_CANONICAL_FIRST, "Canonical-first"),
)

ORIGENS_OBRIGACAO_FINANCEIRA = (
    "receita_operacional",
    "despesa_operacional",
    "custo_fixo",
    "evento_custo_servico",
    "evento_custo_extra",
    "parcela_divida",
    "investimento",
    "financiamento_movimentacao",
)

ORIGEM_OBRIGACAO_CANONICA_POR_CAMPO = {
    "receita_operacional": "receita_operacional",
    "despesa_operacional": "despesa_operacional",
    "custo_fixo": "custo_fixo",
    "evento_custo_servico": "custo_servico",
    "evento_custo_extra": "custo_extra",
    "parcela_divida": "parcela_divida",
    "investimento": "investimento",
    "financiamento_movimentacao": "financiamento_movimentacao",
}

ORIGENS_BAIXA_FINANCEIRA = (
    "receita_operacional",
    "despesa_operacional",
    "custo_fixo",
    "pagamento_custo_servico",
    "pagamento_custo_extra",
    "pagamento_parcela_divida",
    "investimento",
    "financiamento_movimentacao",
)


def q_origem_exclusiva_obrigacao(campo_origem):
    condicao = models.Q(**{f"{campo_origem}__isnull": False})

    for outro_campo in ORIGENS_OBRIGACAO_FINANCEIRA:
        if outro_campo == campo_origem:
            continue
        condicao &= models.Q(**{f"{outro_campo}__isnull": True})

    return condicao


def q_origem_unica_obrigacao():
    condicao = models.Q()

    for campo_origem in ORIGENS_OBRIGACAO_FINANCEIRA:
        condicao |= q_origem_exclusiva_obrigacao(campo_origem)

    return condicao


def q_origem_consistente_obrigacao():
    condicao = models.Q()

    for campo_origem, origem_canonica in ORIGEM_OBRIGACAO_CANONICA_POR_CAMPO.items():
        condicao |= (
            q_origem_exclusiva_obrigacao(campo_origem)
            & models.Q(origem=origem_canonica)
        )

    return condicao


class ObrigacaoFinanceira(models.Model):
    TIPO_RECEBER = "receber"
    TIPO_PAGAR = "pagar"

    TIPO_CHOICES = (
        (TIPO_RECEBER, "A receber"),
        (TIPO_PAGAR, "A pagar"),
    )

    ORIGEM_CHOICES = (
        ("receita_operacional", "Receita operacional"),
        ("despesa_operacional", "Despesa operacional"),
        ("custo_fixo", "Custo fixo"),
        ("custo_servico", "Custo de serviço"),
        ("custo_extra", "Custo extra"),
        ("parcela_divida", "Parcela FCF"),
        ("investimento", "Investimento"),
        ("financiamento_movimentacao", "Movimentação de financiamento"),
    )

    STATUS_CHOICES = (
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PARCIAL, "Parcial"),
        (STATUS_LIQUIDADO_CANONICO, "Liquidado"),
        (STATUS_CANCELADO, "Cancelado"),
    )

    chave_origem = models.CharField(
        max_length=140,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Chave estável da origem legada ou canônica da obrigação.",
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, db_index=True)
    origem = models.CharField(max_length=40, choices=ORIGEM_CHOICES, db_index=True)
    detalhe_origem = models.CharField(max_length=40, blank=True, db_index=True)
    fluxo = models.CharField(
        max_length=10,
        choices=LancamentoFinanceiro.FLUXO_CHOICES,
        db_index=True,
    )
    natureza = models.CharField(
        max_length=40,
        choices=LancamentoFinanceiro.NATUREZA_CHOICES,
        db_index=True,
    )
    descricao = models.CharField(max_length=255)
    referencia = models.CharField(max_length=255, blank=True)
    data_vencimento = models.DateField(db_index=True)
    valor_previsto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    valor_realizado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    valor_pendente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    valor_excedente_realizado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
        db_index=True,
    )

    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    evento = models.ForeignKey(
        "Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )

    receita_operacional = models.ForeignKey(
        "ReceitaOperacional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    despesa_operacional = models.ForeignKey(
        "DespesaOperacional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    custo_fixo = models.ForeignKey(
        "CustoFixo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    evento_custo_servico = models.ForeignKey(
        "EventoCustoServico",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    evento_custo_extra = models.ForeignKey(
        "EventoCustoExtra",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    parcela_divida = models.ForeignKey(
        "ParcelaDivida",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    investimento = models.ForeignKey(
        "Investimento",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )
    financiamento_movimentacao = models.ForeignKey(
        "FinanciamentoMovimentacao",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras",
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras_criadas",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="obrigacoes_financeiras_atualizadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Obrigação financeira"
        verbose_name_plural = "Obrigações financeiras"
        ordering = ["data_vencimento", "origem", "descricao", "id"]
        indexes = [
            models.Index(fields=["tipo", "status", "data_vencimento"]),
            models.Index(fields=["origem", "data_vencimento"]),
            models.Index(fields=["fluxo", "data_vencimento"]),
            models.Index(fields=["evento", "data_vencimento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_previsto__gte=0),
                name="ck_obrig_fin_previsto_nn",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_realizado__gte=0),
                name="ck_obrig_fin_realizado_nn",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_pendente__gte=0),
                name="ck_obrig_fin_pendente_nn",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_excedente_realizado__gte=0),
                name="ck_obrig_fin_excedente_nn",
            ),
            models.CheckConstraint(
                condition=q_origem_unica_obrigacao(),
                name="ck_obrig_fin_origem_unica",
            ),
            models.CheckConstraint(
                condition=q_origem_consistente_obrigacao(),
                name="ck_obrig_fin_origem_consist",
            ),
            models.UniqueConstraint(
                fields=["receita_operacional"],
                condition=models.Q(receita_operacional__isnull=False),
                name="uq_obrig_fin_receita",
            ),
            models.UniqueConstraint(
                fields=["despesa_operacional"],
                condition=models.Q(despesa_operacional__isnull=False),
                name="uq_obrig_fin_despesa",
            ),
            models.UniqueConstraint(
                fields=["custo_fixo"],
                condition=models.Q(custo_fixo__isnull=False),
                name="uq_obrig_fin_custo_fixo",
            ),
            models.UniqueConstraint(
                fields=["evento_custo_servico", "detalhe_origem"],
                condition=models.Q(evento_custo_servico__isnull=False),
                name="uq_obrig_fin_custo_serv_det",
            ),
            models.UniqueConstraint(
                fields=["evento_custo_extra"],
                condition=models.Q(evento_custo_extra__isnull=False),
                name="uq_obrig_fin_custo_extra",
            ),
            models.UniqueConstraint(
                fields=["parcela_divida"],
                condition=models.Q(parcela_divida__isnull=False),
                name="uq_obrig_fin_parcela",
            ),
            models.UniqueConstraint(
                fields=["investimento"],
                condition=models.Q(investimento__isnull=False),
                name="uq_obrig_fin_invest",
            ),
            models.UniqueConstraint(
                fields=["financiamento_movimentacao"],
                condition=models.Q(financiamento_movimentacao__isnull=False),
                name="uq_obrig_fin_financ",
            ),
        ]

    def __str__(self):
        return f"{self.data_vencimento} - {self.descricao} - {self.valor_previsto}"

    @property
    def liquidada(self):
        return self.status == STATUS_LIQUIDADO_CANONICO

    @property
    def contas_pendentes(self):
        return self.valor_pendente

    @property
    def valor_pendente_pagamento(self):
        return self.valor_pendente if self.tipo == self.TIPO_PAGAR else Decimal("0.00")

    @property
    def valor_pendente_recebimento(self):
        return self.valor_pendente if self.tipo == self.TIPO_RECEBER else Decimal("0.00")

    def campos_origem_preenchidos(self):
        return [
            campo
            for campo in ORIGENS_OBRIGACAO_FINANCEIRA
            if getattr(self, f"{campo}_id")
        ]

    def clean(self):
        erros = {}

        for campo in (
            "valor_previsto",
            "valor_realizado",
            "valor_pendente",
            "valor_excedente_realizado",
        ):
            if getattr(self, campo) < Decimal("0.00"):
                erros[campo] = "O valor não pode ser negativo."

        origens = self.campos_origem_preenchidos()
        if len(origens) != 1:
            erros["__all__"] = "Informe exatamente uma origem para a obrigação financeira."
        elif self.origem != ORIGEM_OBRIGACAO_CANONICA_POR_CAMPO[origens[0]]:
            erros["origem"] = "A origem informada não corresponde ao vínculo preenchido."

        if self.valor_pendente > Decimal("0.00") and self.status == STATUS_LIQUIDADO_CANONICO:
            erros["status"] = "Obrigação liquidada não deve possuir valor pendente."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class BaixaFinanceira(models.Model):
    STATUS_CHOICES = (
        (STATUS_REALIZADO, "Realizado"),
        (STATUS_CANCELADO, "Cancelado"),
    )

    chave_origem = models.CharField(
        max_length=140,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Chave estável da origem legada ou canônica da baixa.",
    )
    tipo = models.CharField(max_length=10, choices=TIPO_FLUXO_CHOICES, db_index=True)
    fluxo = models.CharField(
        max_length=10,
        choices=LancamentoFinanceiro.FLUXO_CHOICES,
        db_index=True,
    )
    natureza = models.CharField(
        max_length=40,
        choices=LancamentoFinanceiro.NATUREZA_CHOICES,
        db_index=True,
    )
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    data_baixa = models.DateField(db_index=True)
    forma_pagamento = models.CharField(max_length=30, blank=True)
    descricao = models.CharField(max_length=255)
    observacao = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REALIZADO,
        db_index=True,
    )
    fonte_escrita = models.CharField(
        max_length=30,
        choices=FONTE_ESCRITA_BAIXA_CHOICES,
        default=FONTE_ESCRITA_LEGACY_ADAPTER_SYNCED,
        db_index=True,
        help_text="Fonte de escrita que criou ou atualizou a baixa canonica.",
    )

    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    evento = models.ForeignKey(
        "Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    lancamento_financeiro = models.OneToOneField(
        "LancamentoFinanceiro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baixa_financeira",
    )

    receita_operacional = models.ForeignKey(
        "ReceitaOperacional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    despesa_operacional = models.ForeignKey(
        "DespesaOperacional",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    custo_fixo = models.ForeignKey(
        "CustoFixo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    pagamento_custo_servico = models.ForeignKey(
        "PagamentoEventoCustoServico",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    pagamento_custo_extra = models.ForeignKey(
        "PagamentoEventoCustoExtra",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    pagamento_parcela_divida = models.ForeignKey(
        "PagamentoParcelaDivida",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    investimento = models.ForeignKey(
        "Investimento",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )
    financiamento_movimentacao = models.ForeignKey(
        "FinanciamentoMovimentacao",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="baixas_financeiras",
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baixas_financeiras_criadas",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baixas_financeiras_atualizadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Baixa financeira"
        verbose_name_plural = "Baixas financeiras"
        ordering = ["-data_baixa", "-id"]
        indexes = [
            models.Index(fields=["tipo", "data_baixa"]),
            models.Index(fields=["fluxo", "data_baixa"]),
            models.Index(fields=["natureza", "data_baixa"]),
            models.Index(fields=["evento", "data_baixa"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_total__gt=0),
                name="ck_baixa_fin_valor_pos",
            ),
        ]

    def __str__(self):
        return f"{self.data_baixa} - {self.get_tipo_display()} - {self.valor_total}"

    @property
    def valor_baixa(self):
        return self.valor_total

    def campos_origem_preenchidos(self):
        return [
            campo
            for campo in ORIGENS_BAIXA_FINANCEIRA
            if getattr(self, f"{campo}_id")
        ]

    def clean(self):
        erros = {}

        if self.valor_total <= Decimal("0.00"):
            erros["valor_total"] = "O valor da baixa deve ser maior que zero."

        if len(self.campos_origem_preenchidos()) > 1:
            erros["__all__"] = "Informe no máximo uma origem legada para a baixa."

        if self.lancamento_financeiro_id:
            lancamento = self.lancamento_financeiro
            if self.tipo != lancamento.tipo:
                erros["tipo"] = "A baixa deve ter o mesmo tipo do lançamento."
            if self.fluxo != lancamento.fluxo:
                erros["fluxo"] = "A baixa deve ter o mesmo fluxo do lançamento."
            if self.natureza != lancamento.natureza:
                erros["natureza"] = "A baixa deve ter a mesma natureza do lançamento."
            if self.valor_total != lancamento.valor:
                erros["valor_total"] = "A baixa deve ter o mesmo valor do lançamento."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class BaixaFinanceiraAlocacao(models.Model):
    baixa = models.ForeignKey(
        "BaixaFinanceira",
        on_delete=models.CASCADE,
        related_name="alocacoes",
    )
    obrigacao = models.ForeignKey(
        "ObrigacaoFinanceira",
        on_delete=models.CASCADE,
        related_name="alocacoes_baixa",
    )
    valor_alocado = models.DecimalField(max_digits=12, decimal_places=2)
    valor_juros = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    valor_multa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    valor_desconto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alocação de baixa financeira"
        verbose_name_plural = "Alocações de baixas financeiras"
        ordering = ["baixa", "obrigacao", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_alocado__gt=0),
                name="ck_aloc_baixa_valor_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_juros__gte=0),
                name="ck_aloc_baixa_juros_nn",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_multa__gte=0),
                name="ck_aloc_baixa_multa_nn",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_desconto__gte=0),
                name="ck_aloc_baixa_desconto_nn",
            ),
            models.UniqueConstraint(
                fields=["baixa", "obrigacao"],
                name="uq_aloc_baixa_obrigacao",
            ),
        ]

    def __str__(self):
        return f"{self.baixa} -> {self.obrigacao} ({self.valor_alocado})"

    def clean(self):
        erros = {}

        for campo in ("valor_alocado", "valor_juros", "valor_multa", "valor_desconto"):
            valor = getattr(self, campo)
            if campo == "valor_alocado" and valor <= Decimal("0.00"):
                erros[campo] = "O valor alocado deve ser maior que zero."
            elif campo != "valor_alocado" and valor < Decimal("0.00"):
                erros[campo] = "O valor não pode ser negativo."

        if self.baixa_id and self.obrigacao_id and self.baixa.tipo == TIPO_FLUXO_ENTRADA:
            if self.obrigacao.tipo != ObrigacaoFinanceira.TIPO_RECEBER:
                erros["obrigacao"] = "Baixa de entrada deve alocar obrigação a receber."

        if self.baixa_id and self.obrigacao_id and self.baixa.tipo == TIPO_FLUXO_SAIDA:
            if self.obrigacao.tipo != ObrigacaoFinanceira.TIPO_PAGAR:
                erros["obrigacao"] = "Baixa de saída deve alocar obrigação a pagar."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
