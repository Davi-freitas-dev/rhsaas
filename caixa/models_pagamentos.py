from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.conf import settings
from simple_history.models import HistoricalRecords

from .constants_financeiros import (
    TIPO_CUSTO_ALIMENTACAO,
    TIPO_CUSTO_DIARIAS,
    TIPO_CUSTO_TRANSPORTE,
)
from .services_validacao_pagamentos import (
    erro_caixa_insuficiente_para_pagamento,
    saldo_disponivel_pagamento,
    validar_valor_pagamento_positivo,
)
from .utils_financeiros import ZERO_DECIMAL, decimal_zero


MENSAGEM_PAGAMENTO_ZERO = (
    "O valor do pagamento deve ser maior que zero. "
    "Para cancelar um pagamento lançado incorretamente, remova o registro "
    "em vez de trocar o valor para zero."
)


class PagamentoEventoCustoServico(models.Model):
    TIPO_CHOICES = [
        (TIPO_CUSTO_DIARIAS, "Diárias"),
        (TIPO_CUSTO_ALIMENTACAO, "Alimentação"),
        (TIPO_CUSTO_TRANSPORTE, "Transporte"),
    ]

    custo_servico = models.ForeignKey(
        "EventoCustoServico",
        on_delete=models.CASCADE,
        related_name="pagamentos"
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    descricao = models.CharField(max_length=150, blank=True)
    valor_pagamento = models.DecimalField(max_digits=12, decimal_places=2)
    data_pagamento = models.DateField(db_index=True)
    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_evento_custo_servico_criados"
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_evento_custo_servico_atualizados"
    )

    class Meta:
        verbose_name = "Pagamento de custo de serviço"
        verbose_name_plural = "Pagamentos de custos de serviço"
        ordering = ["data_pagamento", "id"]
        indexes = [
            models.Index(fields=["custo_servico", "data_pagamento"]),
            models.Index(fields=["tipo", "data_pagamento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_pagamento__gt=0),
                name="ck_pag_custo_serv_valor_pos",
            ),
        ]

    def __str__(self):
        return f"{self.custo_servico} - {self.get_tipo_display()} - {self.valor_pagamento}"

    def clean(self):
        erros = {}
        valor_pagamento_positivo = validar_valor_pagamento_positivo(
            self.valor_pagamento
        )

        if not valor_pagamento_positivo:
            erros["valor_pagamento"] = MENSAGEM_PAGAMENTO_ZERO

        if self.custo_servico_id and self.tipo and valor_pagamento_positivo:
            total_pago = self.custo_servico.pagamentos.filter(tipo=self.tipo).aggregate(
                total=Sum("valor_pagamento")
            )["total"]

            pagamento_original = None
            if self.pk:
                pagamento_original = PagamentoEventoCustoServico.objects.get(pk=self.pk)
                if not (
                    pagamento_original.custo_servico_id == self.custo_servico_id
                    and pagamento_original.tipo == self.tipo
                ):
                    pagamento_original = None

            saldo_por_tipo = {
                TIPO_CUSTO_DIARIAS: self.custo_servico.valor_diarias,
                TIPO_CUSTO_ALIMENTACAO: self.custo_servico.valor_alimentacao,
                TIPO_CUSTO_TRANSPORTE: self.custo_servico.valor_transporte,
            }
            valor_previsto = saldo_por_tipo.get(self.tipo, Decimal("0.00"))
            saldo_disponivel = saldo_disponivel_pagamento(
                valor_previsto,
                decimal_zero(total_pago),
                pagamento_original,
            )

            if self.valor_pagamento > saldo_disponivel:
                erros["valor_pagamento"] = (
                    f"O valor do pagamento não pode ser maior que o saldo "
                    f"disponível ({saldo_disponivel})."
                )

        if (
            "valor_pagamento" not in erros
            and valor_pagamento_positivo
            and self.data_pagamento
        ):
            erro_caixa = erro_caixa_insuficiente_para_pagamento(
                self.valor_pagamento,
                self.data_pagamento,
                self if self.pk else None,
            )
            if erro_caixa:
                erros["valor_pagamento"] = erro_caixa

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PagamentoEventoCustoExtra(models.Model):
    custo_extra = models.ForeignKey(
        "EventoCustoExtra",
        on_delete=models.CASCADE,
        related_name="pagamentos"
    )
    descricao = models.CharField(max_length=150, blank=True)
    valor_pagamento = models.DecimalField(max_digits=12, decimal_places=2)
    data_pagamento = models.DateField(db_index=True)
    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_evento_custo_extra_criados"
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_evento_custo_extra_atualizados"
    )

    class Meta:
        verbose_name = "Pagamento de custo extra"
        verbose_name_plural = "Pagamentos de custos extras"
        ordering = ["data_pagamento", "id"]
        indexes = [
            models.Index(fields=["custo_extra", "data_pagamento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_pagamento__gt=0),
                name="ck_pag_custo_extra_valor_pos",
            ),
        ]

    def __str__(self):
        return f"{self.custo_extra} - {self.valor_pagamento}"

    def clean(self):
        erros = {}
        valor_pagamento_positivo = validar_valor_pagamento_positivo(
            self.valor_pagamento
        )

        if not valor_pagamento_positivo:
            erros["valor_pagamento"] = MENSAGEM_PAGAMENTO_ZERO

        if self.custo_extra_id and valor_pagamento_positivo:
            total_pago = self.custo_extra.pagamentos.aggregate(
                total=Sum("valor_pagamento")
            )["total"]

            pagamento_original = None
            if self.pk:
                pagamento_original = PagamentoEventoCustoExtra.objects.get(pk=self.pk)
                if pagamento_original.custo_extra_id != self.custo_extra_id:
                    pagamento_original = None

            saldo_disponivel = saldo_disponivel_pagamento(
                self.custo_extra.valor_previsto,
                decimal_zero(total_pago),
                pagamento_original,
            )

            if self.valor_pagamento > saldo_disponivel:
                erros["valor_pagamento"] = (
                    f"O valor do pagamento não pode ser maior que o saldo "
                    f"disponível ({saldo_disponivel})."
                )

        if (
            "valor_pagamento" not in erros
            and valor_pagamento_positivo
            and self.data_pagamento
        ):
            erro_caixa = erro_caixa_insuficiente_para_pagamento(
                self.valor_pagamento,
                self.data_pagamento,
                self if self.pk else None,
            )
            if erro_caixa:
                erros["valor_pagamento"] = erro_caixa

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
