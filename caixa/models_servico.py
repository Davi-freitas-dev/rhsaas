from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from .constants_financeiros import (
    TIPO_CUSTO_ALIMENTACAO,
    TIPO_CUSTO_DIARIAS,
    TIPO_CUSTO_TRANSPORTE,
)
from .services_movimentos import saldo_nao_negativo
from .utils_financeiros import decimal_zero, quantizar_moeda


class EventoCustoServico(models.Model):
    evento = models.ForeignKey(
        "Evento",
        on_delete=models.CASCADE,
        related_name="custos_servicos"
    )
    servico = models.ForeignKey(
        "Servico",
        on_delete=models.PROTECT,
        related_name="custos_evento"
    )

    valor_diarias = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    valor_alimentacao = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    valor_transporte = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    diarias_quitadas = models.BooleanField(default=False, verbose_name="Diárias baixadas")
    alimentacao_quitada = models.BooleanField(default=False, verbose_name="Alimentação baixada")
    transporte_quitado = models.BooleanField(default=False, verbose_name="Transporte baixado")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")

    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_servico_criados"
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_servico_atualizados"
    )

    class Meta:
        verbose_name = "Custo de serviço do evento"
        verbose_name_plural = "Custos de serviço dos eventos"
        ordering = ["evento", "servico__nome"]
        unique_together = ("evento", "servico")
        indexes = [
            models.Index(fields=["servico", "evento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_diarias__gte=0)
                    & models.Q(valor_alimentacao__gte=0)
                    & models.Q(valor_transporte__gte=0)
                ),
                name="ck_custo_servico_valores_nn",
            ),
        ]

    def __str__(self):
        return f"{self.evento.numero} - {self.servico.nome}"

    def _pagamentos_prefetchados(self):
        return getattr(self, "_prefetched_objects_cache", {}).get("pagamentos")

    def _total_pago_prefetchado(self, tipo=None):
        pagamentos = self._pagamentos_prefetchados()
        if pagamentos is None:
            return None

        total = sum(
            (
                pagamento.valor_pagamento
                for pagamento in pagamentos
                if tipo is None or pagamento.tipo == tipo
            ),
            Decimal("0.00"),
        )
        return quantizar_moeda(total)

    @property
    def total(self):
        return quantizar_moeda(
            self.valor_diarias
            + self.valor_alimentacao
            + self.valor_transporte
        )

    @property
    def total_pago_diarias(self):
        total_prefetchado = self._total_pago_prefetchado(TIPO_CUSTO_DIARIAS)
        if total_prefetchado is not None:
            return total_prefetchado

        total = self.pagamentos.filter(tipo=TIPO_CUSTO_DIARIAS).aggregate(
            total=models.Sum("valor_pagamento")
        )["total"]
        return quantizar_moeda(decimal_zero(total))

    @property
    def total_pago_alimentacao(self):
        total_prefetchado = self._total_pago_prefetchado(TIPO_CUSTO_ALIMENTACAO)
        if total_prefetchado is not None:
            return total_prefetchado

        total = self.pagamentos.filter(tipo=TIPO_CUSTO_ALIMENTACAO).aggregate(
            total=models.Sum("valor_pagamento")
        )["total"]
        return quantizar_moeda(decimal_zero(total))

    @property
    def total_pago_transporte(self):
        total_prefetchado = self._total_pago_prefetchado(TIPO_CUSTO_TRANSPORTE)
        if total_prefetchado is not None:
            return total_prefetchado

        total = self.pagamentos.filter(tipo=TIPO_CUSTO_TRANSPORTE).aggregate(
            total=models.Sum("valor_pagamento")
        )["total"]
        return quantizar_moeda(decimal_zero(total))

    @property
    def total_pago_geral(self):
        total_prefetchado = self._total_pago_prefetchado()
        if total_prefetchado is not None:
            return total_prefetchado

        total = self.pagamentos.aggregate(
            total=models.Sum("valor_pagamento")
        )["total"]
        return quantizar_moeda(decimal_zero(total))

    @property
    def saldo_diarias(self):
        if self.diarias_quitadas:
            return Decimal("0.00")

        return saldo_nao_negativo(self.valor_diarias, self.total_pago_diarias)

    @property
    def valor_pendente_diarias(self):
        return self.saldo_diarias
    
    @property
    def saldo_alimentacao(self):
        if self.alimentacao_quitada:
            return Decimal("0.00")

        return saldo_nao_negativo(self.valor_alimentacao, self.total_pago_alimentacao)

    @property
    def valor_pendente_alimentacao(self):
        return self.saldo_alimentacao
    
    @property
    def saldo_transporte(self):
        if self.transporte_quitado:
            return Decimal("0.00")

        return saldo_nao_negativo(self.valor_transporte, self.total_pago_transporte)

    @property
    def valor_pendente_transporte(self):
        return self.saldo_transporte
    
    @property
    def saldo_geral(self):
        return quantizar_moeda(
            self.saldo_diarias
            + self.saldo_alimentacao
            + self.saldo_transporte
        )

    @property
    def valor_pendente_total(self):
        return self.saldo_geral

    @property
    def valor_pendente_pagamento(self):
        return self.saldo_geral

    @property
    def contas_pendentes(self):
        return self.valor_pendente_pagamento

    def clean(self):
        erros = {}

        if self.valor_diarias < 0:
            erros["valor_diarias"] = "O valor de diárias não pode ser negativo."

        if self.valor_alimentacao < 0:
            erros["valor_alimentacao"] = "O valor de alimentação não pode ser negativo."

        if self.valor_transporte < 0:
            erros["valor_transporte"] = "O valor de transporte não pode ser negativo."

        if (
            self.diarias_quitadas
            or self.alimentacao_quitada
            or self.transporte_quitado
        ) and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        if erros:
            raise ValidationError(erros)
