from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .constants_dividas import (
    STATUS_DIVIDA_ATIVA,
    STATUS_DIVIDA_CANCELADA,
    STATUS_DIVIDA_QUITADA,
    STATUS_DIVIDA_RENEGOCIADA,
    STATUS_PARCELA_ABERTA,
    STATUS_PARCELA_CANCELADA,
    STATUS_PARCELA_PAGA,
    STATUS_PARCELA_PARCIAL,
    STATUS_PARCELA_PRORROGADA,
    STATUS_PARCELA_RENEGOCIADA,
    STATUS_PARCELA_VENCIDA,
    STATUS_PARCELAS_PENDENTES,
)
from .services_dimensoes_operacionais import validar_dimensao_operacional_por_evento
from .services_validacao_pagamentos import erro_caixa_insuficiente_para_pagamento


class Credor(models.Model):
    nome = models.CharField(max_length=150, unique=True, db_index=True)
    documento = models.CharField(max_length=32, blank=True, db_index=True)
    ativo = models.BooleanField(default=True, db_index=True)
    observacao = models.TextField(blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credores_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credores_atualizados",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Credor"
        verbose_name_plural = "Credores"
        ordering = ["nome", "id"]
        indexes = [
            models.Index(fields=["ativo", "nome"]),
        ]

    def __str__(self):
        return self.nome

    def clean(self):
        self.nome = (self.nome or "").strip()
        self.documento = (self.documento or "").strip()

        if not self.nome:
            raise ValidationError({"nome": "Informe o nome do credor."})

        duplicado = Credor.objects.filter(nome__iexact=self.nome)
        if self.pk:
            duplicado = duplicado.exclude(pk=self.pk)

        if duplicado.exists():
            raise ValidationError({
                "nome": "Ja existe um credor cadastrado com este nome."
            })

    @classmethod
    def obter_ou_criar_por_nome(cls, nome, defaults=None):
        nome_normalizado = (nome or "").strip()
        if not nome_normalizado:
            return None, False

        credor_existente = (
            cls.objects.filter(nome__iexact=nome_normalizado)
            .order_by("id")
            .first()
        )
        if credor_existente is not None:
            return credor_existente, False

        return cls.objects.get_or_create(
            nome=nome_normalizado,
            defaults=defaults or {},
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DividaFinanceira(models.Model):
    TIPO_CHOICES = [
        ("emprestimo", "Empréstimo"),
        ("financiamento", "Financiamento"),
        ("fornecedor", "Fornecedor"),
        ("tributaria", "Tributária"),
        ("trabalhista", "Trabalhista"),
        ("cartao", "Cartão"),
        ("outros", "Outros"),
    ]

    STATUS_CHOICES = [
        (STATUS_DIVIDA_ATIVA, "Ativa"),
        (STATUS_DIVIDA_QUITADA, "Quitada"),
        (STATUS_DIVIDA_RENEGOCIADA, "Renegociada"),
        (STATUS_DIVIDA_CANCELADA, "Cancelada"),
    ]

    descricao = models.CharField(max_length=255)
    credor_cadastro = models.ForeignKey(
        "Credor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dividas_financeiras",
        verbose_name="Credor",
    )
    credor = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Credor legado",
        help_text="Alias textual preservado para filtros e integracoes legadas.",
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, db_index=True)
    data_contratacao = models.DateField(db_index=True)

    valor_contratado = models.DecimalField(max_digits=12, decimal_places=2)
    taxa_juros_mensal = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0.0000"),
        help_text="Ex.: 0.0200 para 2% ao mês"
    )
    quantidade_parcelas = models.PositiveIntegerField(default=1)
    dia_vencimento = models.PositiveIntegerField(default=10)

    evento = models.ForeignKey(
        "Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dividas_financeiras",
    )

    observacao = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DIVIDA_ATIVA, db_index=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dividas_criadas"
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dividas_atualizadas"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dívida financeira"
        verbose_name_plural = "Dívidas financeiras"
        ordering = ["-data_contratacao", "-id"]
        indexes = [
            models.Index(fields=["status", "data_contratacao"]),
            models.Index(fields=["tipo", "status"]),
            models.Index(fields=["credor", "status"]),
            models.Index(fields=["credor_cadastro", "status"]),
            models.Index(fields=["evento", "data_contratacao"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(valor_contratado__gte=0)
                    & models.Q(taxa_juros_mensal__gte=0)
                    & models.Q(quantidade_parcelas__gte=1)
                    & models.Q(dia_vencimento__gte=1)
                    & models.Q(dia_vencimento__lte=31)
                ),
                name="ck_divida_parametros_validos",
            ),
        ]

    def __str__(self):
        return f"{self.credor} - {self.descricao}"

    def sincronizar_credor_cadastrado(self):
        nome_credor = (self.credor or "").strip()

        if self.credor_cadastro_id:
            nome_cadastrado = self.credor_cadastro.nome.strip()
            self.credor = nome_cadastrado
            return

        if not nome_credor:
            return

        self.credor = nome_credor
        self.credor_cadastro, _criado = Credor.obter_ou_criar_por_nome(
            nome=nome_credor,
            defaults={
                "criado_por": self.criado_por,
                "atualizado_por": self.atualizado_por,
            },
        )

    def arredondar2(self, valor):
        return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def credor_inativo_preservado(self):
        if not self.pk or not self.credor_cadastro_id:
            return False

        return DividaFinanceira.objects.filter(
            pk=self.pk,
            credor_cadastro_id=self.credor_cadastro_id,
        ).exists()

    def clean(self):
        erros = {}
        self.credor = (self.credor or "").strip()

        if self.credor_cadastro_id:
            self.credor = self.credor_cadastro.nome
            if (
                not self.credor_cadastro.ativo
                and not self.credor_inativo_preservado()
            ):
                erros["credor_cadastro"] = "Selecione um credor ativo."

        if not self.credor:
            erros["credor_cadastro"] = "Informe um credor cadastrado."

        if self.valor_contratado < Decimal("0.00"):
            erros["valor_contratado"] = "O valor contratado não pode ser negativo."

        if self.taxa_juros_mensal < Decimal("0.0000"):
            erros["taxa_juros_mensal"] = "A taxa de juros mensal não pode ser negativa."

        if self.quantidade_parcelas < 1:
            erros["quantidade_parcelas"] = "A quantidade de parcelas deve ser no mínimo 1."

        if self.dia_vencimento < 1 or self.dia_vencimento > 31:
            erros["dia_vencimento"] = "O dia de vencimento deve estar entre 1 e 31."

        validar_dimensao_operacional_por_evento(self, erros)

        if self.pk and self.quantidade_parcelas:
            parcelas_fora_do_novo_plano = ParcelaDivida.objects.filter(
                divida_id=self.pk,
                numero_parcela__gt=self.quantidade_parcelas,
            )
            parcelas_com_movimento = parcelas_fora_do_novo_plano.filter(
                models.Q(valor_pago__gt=Decimal("0.00"))
                | models.Q(baixado_manualmente=True)
                | models.Q(pagamentos__isnull=False)
            ).distinct()
            if parcelas_com_movimento.exists():
                erros["quantidade_parcelas"] = (
                    "Não é possível reduzir a quantidade de parcelas abaixo de "
                    "parcelas que já possuem pagamento ou baixa. Ajuste a "
                    "renegociação manualmente para preservar a contabilidade."
                )

        if erros:
            raise ValidationError(erros)

    @property
    def saldo_devedor(self):
        total = sum(
            (parcela.valor_pendente_pagamento for parcela in self.parcelas.all()),
            Decimal("0.00")
        )
        return self.arredondar2(total)

    @property
    def contas_pendentes(self):
        return self.saldo_devedor

    def atualizar_status(self):
        parcelas = self.parcelas.all()

        if self.status == STATUS_DIVIDA_CANCELADA:
            return

        if not parcelas.exists():
            self.status = STATUS_DIVIDA_ATIVA
            return

        if parcelas.filter(status__in=STATUS_PARCELAS_PENDENTES).exclude(
            status=STATUS_PARCELA_RENEGOCIADA
        ).exists():
            self.status = STATUS_DIVIDA_ATIVA
        elif parcelas.filter(status=STATUS_PARCELA_RENEGOCIADA).exists() and not parcelas.filter(
            status__in=STATUS_PARCELAS_PENDENTES
        ).exclude(
            status=STATUS_PARCELA_RENEGOCIADA
        ).exists():
            self.status = STATUS_DIVIDA_RENEGOCIADA
        else:
            self.status = STATUS_DIVIDA_QUITADA

    def save(self, *args, **kwargs):
        self.sincronizar_credor_cadastrado()
        self.full_clean()
        super().save(*args, **kwargs)

    def valores_principais_parcelas(self, quantidade=None):
        quantidade = quantidade or self.quantidade_parcelas
        if quantidade <= 0:
            raise ValidationError("A quantidade de parcelas deve ser maior que zero.")

        valor_total = self.arredondar2(self.valor_contratado)
        valor_base = self.arredondar2(valor_total / Decimal(quantidade))
        valores = [valor_base for _ in range(quantidade)]
        diferenca_arredondamento = self.arredondar2(
            valor_total - sum(valores, Decimal("0.00"))
        )
        valores[-1] = self.arredondar2(valores[-1] + diferenca_arredondamento)
        return valores

    def data_vencimento_parcela(self, numero_parcela):
        ano = self.data_contratacao.year
        mes = self.data_contratacao.month
        mes_ref = mes + numero_parcela
        ano_calc = ano + ((mes_ref - 1) // 12)
        mes_calc = ((mes_ref - 1) % 12) + 1
        dia = min(self.dia_vencimento, 28)
        return timezone.datetime(ano_calc, mes_calc, dia).date()

    def gerar_parcelas_iniciais(self):
        if self.parcelas.exists():
            return

        valores_principais = self.valores_principais_parcelas()

        for numero, valor_principal in enumerate(valores_principais, start=1):
            vencimento = self.data_vencimento_parcela(numero)
            ParcelaDivida.objects.create(
                divida=self,
                numero_parcela=numero,
                data_vencimento_original=vencimento,
                data_vencimento_atual=vencimento,
                valor_principal=valor_principal,
                valor_juros=Decimal("0.00"),
                valor_multa=Decimal("0.00"),
                valor_desconto=Decimal("0.00"),
            )

    def sincronizar_parcelas_contratadas(self, usuario=None):
        resultado = {
            "criadas": 0,
            "atualizadas": 0,
            "removidas": 0,
        }
        parcelas = list(self.parcelas.order_by("numero_parcela", "id"))
        if not parcelas:
            self.gerar_parcelas_iniciais()
            resultado["criadas"] = self.quantidade_parcelas
            return resultado

        parcelas_por_numero = {parcela.numero_parcela: parcela for parcela in parcelas}
        valores_principais = self.valores_principais_parcelas(self.quantidade_parcelas)

        for numero_parcela, valor_principal in enumerate(valores_principais, start=1):
            data_vencimento = self.data_vencimento_parcela(numero_parcela)
            parcela = parcelas_por_numero.get(numero_parcela)

            if parcela is None:
                ParcelaDivida.objects.create(
                    divida=self,
                    numero_parcela=numero_parcela,
                    data_vencimento_original=data_vencimento,
                    data_vencimento_atual=data_vencimento,
                    valor_principal=valor_principal,
                    valor_juros=Decimal("0.00"),
                    valor_multa=Decimal("0.00"),
                    valor_desconto=Decimal("0.00"),
                    criado_por=usuario,
                    atualizado_por=usuario,
                )
                resultado["criadas"] += 1
                continue

            campos_atualizados = []

            if parcela.valor_principal != valor_principal:
                parcela.valor_principal = valor_principal
                campos_atualizados.append("valor_principal")

            if parcela.data_vencimento_original != data_vencimento:
                parcela.data_vencimento_original = data_vencimento
                campos_atualizados.append("data_vencimento_original")

            if (
                parcela.status
                not in {
                    STATUS_PARCELA_PAGA,
                    STATUS_PARCELA_RENEGOCIADA,
                    STATUS_PARCELA_CANCELADA,
                }
                and parcela.data_vencimento_atual != data_vencimento
            ):
                parcela.data_vencimento_atual = data_vencimento
                campos_atualizados.append("data_vencimento_atual")

            status_original = parcela.status
            if (
                parcela.status == STATUS_PARCELA_PAGA
                and not parcela.baixado_manualmente
                and parcela.valor_pago < parcela.valor_total_devido
            ):
                parcela.status = STATUS_PARCELA_PARCIAL

            if usuario is not None:
                parcela.atualizado_por = usuario
                campos_atualizados.append("atualizado_por")

            if parcela.status != status_original:
                campos_atualizados.append("status")

            if not campos_atualizados:
                continue

            parcela.save(
                update_fields=[*dict.fromkeys(campos_atualizados), "atualizado_em"],
                sincronizacao_pagamento=True,
            )
            resultado["atualizadas"] += 1

        parcelas_excedentes = [
            parcela
            for parcela in parcelas
            if parcela.numero_parcela > self.quantidade_parcelas
        ]
        for parcela in parcelas_excedentes:
            if (
                parcela.valor_pago > Decimal("0.00")
                or parcela.baixado_manualmente
                or parcela.pagamentos.exists()
            ):
                raise ValidationError(
                    "Não é possível remover parcelas com pagamento ou baixa."
                )

            parcela.delete()
            resultado["removidas"] += 1

        return resultado

    def sincronizar_valor_parcelas(self, usuario=None):
        resultado = self.sincronizar_parcelas_contratadas(usuario=usuario)
        return (
            resultado["criadas"]
            + resultado["atualizadas"]
            + resultado["removidas"]
        )


class ParcelaDivida(models.Model):
    STATUS_CHOICES = [
        (STATUS_PARCELA_ABERTA, "Aberta"),
        (STATUS_PARCELA_PARCIAL, "Parcial"),
        (STATUS_PARCELA_PAGA, "Paga"),
        (STATUS_PARCELA_VENCIDA, "Vencida"),
        (STATUS_PARCELA_PRORROGADA, "Prorrogada"),
        (STATUS_PARCELA_RENEGOCIADA, "Renegociada"),
        (STATUS_PARCELA_CANCELADA, "Cancelada"),
    ]

    divida = models.ForeignKey(
        "DividaFinanceira",
        on_delete=models.CASCADE,
        related_name="parcelas"
    )

    numero_parcela = models.PositiveIntegerField()
    data_vencimento_original = models.DateField(db_index=True)
    data_vencimento_atual = models.DateField(db_index=True)

    valor_principal = models.DecimalField(max_digits=12, decimal_places=2)
    valor_juros = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valor_multa = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valor_desconto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PARCELA_ABERTA, db_index=True)
    baixado_manualmente = models.BooleanField(default=False, verbose_name="Baixa manual")
    motivo_baixa = models.TextField(blank=True, verbose_name="Motivo da baixa")
    observacao = models.TextField(blank=True)

    parcela_origem = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parcelas_derivadas"
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parcelas_divida_criadas"
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parcelas_divida_atualizadas"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parcela da dívida"
        verbose_name_plural = "Parcelas das dívidas"
        ordering = ["data_vencimento_atual", "numero_parcela", "id"]
        unique_together = ("divida", "numero_parcela")
        indexes = [
            models.Index(fields=["status", "data_vencimento_atual"]),
            models.Index(fields=["divida", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(numero_parcela__gte=1)
                    & models.Q(valor_principal__gte=0)
                    & models.Q(valor_juros__gte=0)
                    & models.Q(valor_multa__gte=0)
                    & models.Q(valor_desconto__gte=0)
                    & models.Q(valor_pago__gte=0)
                ),
                name="ck_parcela_divida_valores",
            ),
        ]

    @property
    def rotulo_parcela(self):
        total = self.divida.quantidade_parcelas or self.numero_parcela
        return f"{self.numero_parcela}/{total}"

    def __str__(self):
        return (
            f"{self.divida.credor} - {self.divida.descricao} - "
            f"Parcela {self.rotulo_parcela} - "
            f"Contas pendentes: {self.valor_pendente_pagamento}"
        )

    def arredondar2(self, valor):
        return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def valor_total_devido(self):
        total = self.valor_principal + self.valor_juros + self.valor_multa - self.valor_desconto
        return self.arredondar2(total)

    @property
    def saldo_em_aberto(self):
        if self.status in [STATUS_PARCELA_PAGA, STATUS_PARCELA_CANCELADA] or self.baixado_manualmente:
            return Decimal("0.00")

        saldo = self.valor_total_devido - self.valor_pago
        return self.arredondar2(saldo if saldo > 0 else Decimal("0.00"))

    @property
    def valor_pendente_pagamento(self):
        return self.saldo_em_aberto

    @property
    def contas_pendentes(self):
        return self.valor_pendente_pagamento

    @property
    def disponivel_para_pagamento(self):
        return (
            self.status not in [STATUS_PARCELA_PAGA, STATUS_PARCELA_CANCELADA]
            and self.valor_pendente_pagamento > Decimal("0.00")
        )

    def _alteracao_pagamento_permitida(self):
        return bool(getattr(self, "_sincronizacao_pagamento", False))

    def _pagamento_alterado_diretamente(self):
        if self._alteracao_pagamento_permitida():
            return False

        if not self.pk:
            return False

        original = (
            self.__class__.objects.filter(pk=self.pk)
            .only("valor_pago", "baixado_manualmente", "motivo_baixa")
            .first()
        )
        if original is None:
            return False

        return (
            self.valor_pago != original.valor_pago
            or self.baixado_manualmente != original.baixado_manualmente
            or self.motivo_baixa != original.motivo_baixa
        )

    def clean(self):
        erros = {}

        if self.numero_parcela <= 0:
            erros["numero_parcela"] = "O número da parcela deve ser maior que zero."

        for campo in ["valor_principal", "valor_juros", "valor_multa", "valor_desconto", "valor_pago"]:
            valor = getattr(self, campo)
            if valor < 0:
                erros[campo] = "Este valor não pode ser negativo."

        if self.baixado_manualmente and not self.motivo_baixa.strip():
            erros["motivo_baixa"] = "Informe o motivo da baixa manual."

        if self._pagamento_alterado_diretamente():
            erros["__all__"] = (
                "Parcelas devem ser pagas em Pagamentos de parcelas."
            )

        if erros:
            raise ValidationError(erros)

    def atualizar_status(self):
        hoje = timezone.localdate()

        if self.status == STATUS_PARCELA_CANCELADA:
            return

        if self.baixado_manualmente:
            self.status = STATUS_PARCELA_PAGA
            return

        if self.status == STATUS_PARCELA_RENEGOCIADA:
            return

        if (
            self.status == STATUS_PARCELA_PRORROGADA
            and self.valor_pago <= Decimal("0.00")
            and self.data_vencimento_atual >= hoje
        ):
            return

        if self.status == STATUS_PARCELA_PAGA and self.valor_pago > Decimal("0.00"):
            return

        if self.valor_pago <= Decimal("0.00"):
            if self.data_vencimento_atual < hoje:
                self.status = STATUS_PARCELA_VENCIDA
            else:
                self.status = STATUS_PARCELA_ABERTA
        elif self.valor_pago < self.valor_total_devido:
            if self.data_vencimento_atual < hoje:
                self.status = STATUS_PARCELA_VENCIDA
            else:
                self.status = STATUS_PARCELA_PARCIAL
        else:
            self.status = STATUS_PARCELA_PAGA

    def recalcular_pagamento(self):
        from .services_dividas import recalcular_pagamento_parcela

        recalcular_pagamento_parcela(self)

    def save(self, *args, **kwargs):
        sincronizacao_pagamento = kwargs.pop("sincronizacao_pagamento", False)
        self._sincronizacao_pagamento = sincronizacao_pagamento
        try:
            self.full_clean()
            self.atualizar_status()
            super().save(*args, **kwargs)
        finally:
            self._sincronizacao_pagamento = False

        self.divida.atualizar_status()
        DividaFinanceira.objects.filter(pk=self.divida_id).update(
            status=self.divida.status,
            atualizado_em=timezone.now()
        )

    def prorrogar_para_mes_seguinte(self, usuario=None, juros=Decimal("0.00"), multa=Decimal("0.00")):
        if self.status == STATUS_PARCELA_PAGA:
            raise ValidationError("Não é possível prorrogar uma parcela já paga.")

        if self.status == STATUS_PARCELA_CANCELADA:
            raise ValidationError("Não é possível prorrogar uma parcela cancelada.")

        nova_data = self.data_vencimento_atual
        novo_mes = nova_data.month + 1
        novo_ano = nova_data.year

        if novo_mes > 12:
            novo_mes = 1
            novo_ano += 1

        novo_dia = min(nova_data.day, 28)
        novo_vencimento = timezone.datetime(novo_ano, novo_mes, novo_dia).date()

        observacao_prorrogacao = (
            f"Parcela prorrogada de {self.data_vencimento_atual:%d/%m/%Y} "
            f"para {novo_vencimento:%d/%m/%Y}."
        )

        self.data_vencimento_atual = novo_vencimento
        self.valor_juros = self.arredondar2(self.valor_juros + juros)
        self.valor_multa = self.arredondar2(self.valor_multa + multa)
        self.status = STATUS_PARCELA_PRORROGADA
        self.atualizado_por = usuario

        if self.observacao:
            self.observacao += f"\n{observacao_prorrogacao}"
        else:
            self.observacao = observacao_prorrogacao

        self.save()


class PagamentoParcelaDivida(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ("pix", "Pix"),
        ("boleto", "Boleto"),
        ("transferencia", "Transferência"),
        ("cartao", "Cartão"),
        ("dinheiro", "Dinheiro"),
        ("outro", "Outro"),
    ]

    parcela = models.ForeignKey(
        "ParcelaDivida",
        on_delete=models.CASCADE,
        related_name="pagamentos"
    )

    data_pagamento = models.DateField(db_index=True)
    valor_pagamento = models.DecimalField(max_digits=12, decimal_places=2)
    forma_pagamento = models.CharField(
        max_length=20,
        choices=FORMA_PAGAMENTO_CHOICES,
        blank=True
    )
    observacao = models.TextField(blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_divida_criados"
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_divida_atualizados"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pagamento de parcela"
        verbose_name_plural = "Pagamentos de parcelas"
        ordering = ["data_pagamento", "id"]
        indexes = [
            models.Index(fields=["parcela", "data_pagamento"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_pagamento__gt=0),
                name="ck_pag_parcela_valor_pos",
            ),
        ]

    def __str__(self):
        return f"{self.parcela} - {self.valor_pagamento}"

    def clean(self):
        erros = {}
        valor_pagamento_positivo = (
            self.valor_pagamento is not None
            and self.valor_pagamento > Decimal("0.00")
        )

        if not valor_pagamento_positivo:
            erros["valor_pagamento"] = "O valor do pagamento deve ser maior que zero."

        if self.parcela_id:
            parcela = self.parcela

            if parcela.status == STATUS_PARCELA_PAGA and not self.pk:
                erros["parcela"] = "Não é possível registrar pagamento em uma parcela já paga."

            if parcela.status == STATUS_PARCELA_CANCELADA:
                erros["parcela"] = "Não é possível registrar pagamento em uma parcela cancelada."

            saldo_atual = parcela.valor_pendente_pagamento

            if self.pk:
                pagamento_original = PagamentoParcelaDivida.objects.get(pk=self.pk)
                saldo_atual += pagamento_original.valor_pagamento

            if valor_pagamento_positivo and self.valor_pagamento > saldo_atual:
                erros["valor_pagamento"] = (
                    f"O valor do pagamento não pode ser maior que o valor pendente "
                    f"da parcela ({saldo_atual})."
                )

        if erros:
            raise ValidationError(erros)

        if valor_pagamento_positivo and self.data_pagamento:
            erro_caixa = erro_caixa_insuficiente_para_pagamento(
                self.valor_pagamento,
                self.data_pagamento,
                self if self.pk else None,
            )
            if erro_caixa:
                raise ValidationError({"valor_pagamento": erro_caixa})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.parcela.recalcular_pagamento()

    def delete(self, *args, **kwargs):
        parcela = self.parcela
        super().delete(*args, **kwargs)
        parcela.recalcular_pagamento()
