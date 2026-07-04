from datetime import date
import calendar
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
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
