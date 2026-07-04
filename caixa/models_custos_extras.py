from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords

from .services_movimentos import saldo_nao_negativo
from .utils_financeiros import decimal_zero, quantizar_moeda


class EventoCustoExtra(models.Model):
    CATEGORIA_CHOICES = [
        ("insumo", "Insumo"),
        ("material", "Material"),
        ("uniforme", "Uniforme"),
        ("logistica", "Logística"),
        ("comissao", "Comissão"),
        ("outros", "Outros"),
    ]

    evento = models.ForeignKey(
        "Evento",
        on_delete=models.CASCADE,
        related_name="custos_extras"
    )

    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES,
        default="insumo",
        db_index=True,
    )

    descricao = models.CharField(max_length=150)

    valor_previsto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    quitado = models.BooleanField(default=False, verbose_name="Baixa manual")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")

    data_vencimento = models.DateField(db_index=True)

    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_extras_criados"
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_extras_atualizados"
    )

    class Meta:
        verbose_name = "Custo extra do evento"
        verbose_name_plural = "Custos extras do evento"
        ordering = ["data_vencimento", "id"]
        indexes = [
            models.Index(fields=["evento", "data_vencimento"]),
            models.Index(fields=["categoria", "data_vencimento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_previsto__gte=0)
                    & models.Q(valor_pago__gte=0)
                ),
                name="ck_custo_extra_valores_nn",
            ),
        ]

    def __str__(self):
        return f"{self.evento.numero} - {self.descricao}"

    def _pagamentos_prefetchados(self):
        return getattr(self, "_prefetched_objects_cache", {}).get("pagamentos")

    @property
    def total_pago(self):
        pagamentos = self._pagamentos_prefetchados()
        if pagamentos is not None:
            total = sum(
                (pagamento.valor_pagamento for pagamento in pagamentos),
                Decimal("0.00"),
            )
            return quantizar_moeda(total)

        total = self.pagamentos.aggregate(
            total=models.Sum("valor_pagamento")
        )["total"]
        return quantizar_moeda(decimal_zero(total))

    @property
    def saldo_a_pagar(self):
        if self.quitado:
            return Decimal("0.00")

        return saldo_nao_negativo(self.valor_previsto, self.total_pago)

    @property
    def valor_pendente_pagamento(self):
        return self.saldo_a_pagar

    @property
    def contas_pendentes(self):
        return self.valor_pendente_pagamento

    def _alteracao_pagamento_permitida(self):
        return bool(getattr(self, "_sincronizacao_pagamento", False))

    def _pagamento_alterado_diretamente(self):
        if self._alteracao_pagamento_permitida():
            return False

        if not self.pk:
            return False

        original = (
            self.__class__.objects.filter(pk=self.pk)
            .only("valor_pago", "quitado", "motivo_baixa")
            .first()
        )
        if original is None:
            return False

        return (
            self.valor_pago != original.valor_pago
            or self.quitado != original.quitado
            or self.motivo_baixa != original.motivo_baixa
        )

    def clean(self):
        erros = {}

        if self.valor_previsto < 0:
            erros["valor_previsto"] = "O valor previsto não pode ser negativo."

        if self.valor_pago < 0:
            erros["valor_pago"] = "O valor pago não pode ser negativo."

        if self.valor_pago > self.valor_previsto and self.valor_previsto > 0:
            erros["valor_pago"] = "O valor pago não pode ser maior que o previsto."

        if self.quitado and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        if self._pagamento_alterado_diretamente():
            erros["__all__"] = (
                "Custos extras devem ser pagos em Pagamentos de custos extras."
            )

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        sincronizacao_pagamento = kwargs.pop("sincronizacao_pagamento", False)
        self._sincronizacao_pagamento = sincronizacao_pagamento
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        finally:
            self._sincronizacao_pagamento = False


class OrcamentoCustoExtra(models.Model):
    orcamento = models.ForeignKey(
        "Orcamento",
        on_delete=models.CASCADE,
        related_name="custos_extras",
    )
    evento_custo_extra = models.OneToOneField(
        "EventoCustoExtra",
        on_delete=models.SET_NULL,
        related_name="orcamento_origem",
        null=True,
        blank=True,
    )
    categoria = models.CharField(
        max_length=30,
        choices=EventoCustoExtra.CATEGORIA_CHOICES,
        default="insumo",
        db_index=True,
    )
    descricao = models.CharField(max_length=150)
    valor_previsto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    data_vencimento = models.DateField(db_index=True)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Custo extra do orcamento"
        verbose_name_plural = "Custos extras do orcamento"
        ordering = ["data_vencimento", "id"]
        indexes = [
            models.Index(fields=["orcamento", "data_vencimento"]),
            models.Index(fields=["categoria", "data_vencimento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_previsto__gte=0),
                name="ck_orcamento_custo_extra_valor_nn",
            ),
        ]

    def __str__(self):
        return f"{self.orcamento.numero} - {self.descricao}"

    def clean(self):
        erros = {}

        if self.valor_previsto < 0:
            erros["valor_previsto"] = "O valor previsto nao pode ser negativo."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        if self.pk and not self.evento_custo_extra_id:
            evento_custo_extra_id = (
                self.__class__.objects.filter(pk=self.pk)
                .values_list("evento_custo_extra_id", flat=True)
                .first()
            )
            if evento_custo_extra_id:
                self.evento_custo_extra_id = evento_custo_extra_id

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            custo_evento = self.evento_custo_extra
        except EventoCustoExtra.DoesNotExist:
            custo_evento = None

        super().delete(*args, **kwargs)

        if not custo_evento:
            return

        if self._custo_evento_copiado_removivel(custo_evento):
            custo_evento.delete()
            return

        custo_evento.valor_previsto = Decimal("0.00")
        custo_evento.save(update_fields=["valor_previsto", "atualizado_em"])

    def _custo_evento_copiado_removivel(self, custo_evento):
        return (
            not custo_evento.quitado
            and decimal_zero(custo_evento.valor_pago) <= Decimal("0.00")
            and not custo_evento.pagamentos.exists()
        )
