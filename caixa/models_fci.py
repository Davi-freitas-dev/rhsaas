from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PLANEJADO,
    STATUS_PREVISTO_REALIZADO_CHOICES,
    STATUS_REALIZADO,
    TIPO_FLUXO_CHOICES,
    TIPO_FLUXO_SAIDA,
)
from .services_dimensoes_operacionais import validar_dimensao_operacional_por_evento
from .services_movimentos import saldo_nao_negativo, status_por_valor_previsto_realizado
from .services_validacao_pagamentos import erro_caixa_insuficiente_para_aumento


class Investimento(models.Model):
    TIPO_FLUXO_CHOICES = TIPO_FLUXO_CHOICES

    STATUS_CHOICES = STATUS_PREVISTO_REALIZADO_CHOICES

    CATEGORIA_CHOICES = [
        ("equipamento", "Equipamento"),
        ("veiculo", "Veículo"),
        ("moveis", "Móveis"),
        ("informatica", "Informática"),
        ("software", "Software"),
        ("reforma", "Reforma"),
        ("imovel", "Imóvel"),
        ("outros", "Outros"),
    ]

    descricao = models.CharField(max_length=255)
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, db_index=True)
    tipo_fluxo = models.CharField(max_length=10, choices=TIPO_FLUXO_CHOICES, default=TIPO_FLUXO_SAIDA, db_index=True)

    valor_previsto = models.DecimalField(max_digits=12, decimal_places=2)
    valor_realizado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    data_prevista = models.DateField(db_index=True)
    data_realizacao = models.DateField(null=True, blank=True, db_index=True)

    evento = models.ForeignKey(
        "Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investimentos",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANEJADO, db_index=True)
    baixado_manualmente = models.BooleanField(default=False, verbose_name="Baixa manual")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")
    observacao = models.TextField(blank=True)

    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Investimento"
        verbose_name_plural = "Investimentos"
        ordering = ["-data_prevista", "-id"]
        indexes = [
            models.Index(fields=["status", "data_prevista"]),
            models.Index(fields=["tipo_fluxo", "data_prevista"]),
            models.Index(fields=["ativo", "data_prevista"]),
            models.Index(fields=["categoria", "data_prevista"]),
            models.Index(fields=["evento", "data_prevista"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_previsto__gte=0)
                    & models.Q(valor_realizado__gte=0)
                ),
                name="ck_investimento_valores_nn",
            ),
        ]

    def __str__(self):
        return self.descricao

    @property
    def saldo_restante(self):
        if self.status in [STATUS_REALIZADO, STATUS_CANCELADO] or self.baixado_manualmente:
            return Decimal("0.00")

        return saldo_nao_negativo(self.valor_previsto, self.valor_realizado)

    @property
    def valor_pendente_realizacao(self):
        return self.saldo_restante

    def clean(self):
        erros = {}

        if self.valor_previsto < 0:
            erros["valor_previsto"] = "O valor previsto não pode ser negativo."

        if self.valor_realizado < 0:
            erros["valor_realizado"] = "O valor realizado não pode ser negativo."

        if self.valor_realizado > self.valor_previsto and self.valor_previsto > 0:
            erros["valor_realizado"] = "O valor realizado não pode ser maior que o previsto."

        if self.baixado_manualmente and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        validar_dimensao_operacional_por_evento(self, erros)

        if (
            "valor_realizado" not in erros
            and self.tipo_fluxo == TIPO_FLUXO_SAIDA
            and self.valor_realizado > Decimal("0.00")
        ):
            erro_caixa = erro_caixa_insuficiente_para_aumento(
                self.__class__,
                self.pk,
                "valor_realizado",
                self.valor_realizado,
                self.data_realizacao or self.data_prevista,
            )
            if erro_caixa:
                erros["valor_realizado"] = erro_caixa

        if erros:
            raise ValidationError(erros)

    def atualizar_status(self):
        if self.status == STATUS_CANCELADO:
            return

        if self.baixado_manualmente:
            self.status = STATUS_REALIZADO
            return

        self.status = status_por_valor_previsto_realizado(
            self.status,
            self.valor_previsto,
            self.valor_realizado,
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.atualizar_status()
        super().save(*args, **kwargs)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investimentos_criados",
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investimentos_atualizados",
    )
