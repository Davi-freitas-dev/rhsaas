from decimal import Decimal

from django import forms
from django.utils import timezone

from .constants_financeiros import TIPOS_CUSTO_SERVICO
from .models_pagamentos import (
    PagamentoEventoCustoServico,
    PagamentoEventoCustoExtra,
)
from .models_servico import EventoCustoServico
from .selectors_pagamentos import (
    queryset_custos_extras_pagaveis,
    queryset_custos_servico_pagaveis,
    saldo_por_tipo,
)


class BaixaSemPagamentoMixin:
    def _post_clean(self):
        if self._baixar_sem_novo_pagamento():
            return

        super()._post_clean()

    def _baixar_sem_novo_pagamento(self):
        valor_pagamento = self.cleaned_data.get("valor_pagamento")
        return (
            self.cleaned_data.get("baixar_saldo")
            and valor_pagamento == Decimal("0.00")
            and "valor_pagamento" not in self._errors
        )


def configurar_tipos_custo_servico_pagaveis(form, custo_servico=None):
    custo_servico = resolver_custo_servico_selecionado(form, custo_servico)
    if not custo_servico:
        return

    incluir_tipo = form.instance.tipo if form.instance.pk else None
    form.fields["tipo"].choices = escolhas_tipos_custo_servico_pagaveis(
        custo_servico,
        incluir_tipo=incluir_tipo,
    )


def escolhas_tipos_custo_servico_pagaveis(custo_servico, incluir_tipo=None):
    return [
        (tipo, config["rotulo"])
        for tipo, config in TIPOS_CUSTO_SERVICO.items()
        if tipo == incluir_tipo or saldo_por_tipo(custo_servico, tipo) > Decimal("0.00")
    ]


def resolver_custo_servico_selecionado(form, custo_servico=None):
    if custo_servico:
        return custo_servico

    if form.instance and form.instance.pk and form.instance.custo_servico_id:
        return form.instance.custo_servico

    custo_servico_id = form.data.get("custo_servico") if form.is_bound else None
    if not custo_servico_id:
        return None

    try:
        return form.fields["custo_servico"].queryset.get(pk=custo_servico_id)
    except (EventoCustoServico.DoesNotExist, ValueError, TypeError):
        return None


class PagamentoEventoCustoServicoForm(BaixaSemPagamentoMixin, forms.ModelForm):
    baixar_saldo = forms.BooleanField(
        required=False,
        label="Baixar pendência restante",
    )
    motivo_baixa = forms.CharField(
        required=False,
        label="Motivo da baixa do valor pendente",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    class Meta:
        model = PagamentoEventoCustoServico
        fields = [
            "custo_servico",
            "tipo",
            "descricao",
            "valor_pagamento",
            "data_pagamento",
            "observacao",
            "baixar_saldo",
            "motivo_baixa",
        ]
        widgets = {
            "data_pagamento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, custo_servico=None, tipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["custo_servico"].queryset = queryset_custos_servico_pagaveis(
            incluir_id=self.instance.custo_servico_id if self.instance.pk else None,
        )
        if not self.instance.pk:
            self.fields["data_pagamento"].initial = timezone.localdate()
        if custo_servico:
            self.fields["custo_servico"].initial = custo_servico
        if tipo:
            self.fields["tipo"].initial = tipo
        configurar_tipos_custo_servico_pagaveis(self, custo_servico)

    def clean(self):
        cleaned_data = super().clean()
        baixar_saldo = cleaned_data.get("baixar_saldo")
        motivo_baixa = (cleaned_data.get("motivo_baixa") or "").strip()

        if baixar_saldo and not motivo_baixa:
            self.add_error(
                "motivo_baixa",
                "Informe o motivo para baixar a pendência restante.",
            )

        return cleaned_data


class PagamentoEventoCustoServicoAdminForm(forms.ModelForm):
    class Meta:
        model = PagamentoEventoCustoServico
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["custo_servico"].queryset = queryset_custos_servico_pagaveis(
            incluir_id=self.instance.custo_servico_id if self.instance.pk else None,
        )
        configurar_tipos_custo_servico_pagaveis(self)


class PagamentoEventoCustoExtraForm(BaixaSemPagamentoMixin, forms.ModelForm):
    baixar_saldo = forms.BooleanField(
        required=False,
        label="Baixar pendência restante",
    )
    motivo_baixa = forms.CharField(
        required=False,
        label="Motivo da baixa do valor pendente",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    class Meta:
        model = PagamentoEventoCustoExtra
        fields = [
            "custo_extra",
            "descricao",
            "valor_pagamento",
            "data_pagamento",
            "observacao",
            "baixar_saldo",
            "motivo_baixa",
        ]
        widgets = {
            "data_pagamento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, custo_extra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["custo_extra"].queryset = queryset_custos_extras_pagaveis(
            incluir_id=self.instance.custo_extra_id if self.instance.pk else None,
        )
        if not self.instance.pk:
            self.fields["data_pagamento"].initial = timezone.localdate()
        if custo_extra:
            self.fields["custo_extra"].initial = custo_extra

    def clean(self):
        cleaned_data = super().clean()
        baixar_saldo = cleaned_data.get("baixar_saldo")
        motivo_baixa = (cleaned_data.get("motivo_baixa") or "").strip()

        if baixar_saldo and not motivo_baixa:
            self.add_error(
                "motivo_baixa",
                "Informe o motivo para baixar a pendência restante.",
            )

        return cleaned_data


class PagamentoEventoCustoExtraAdminForm(forms.ModelForm):
    class Meta:
        model = PagamentoEventoCustoExtra
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["custo_extra"].queryset = queryset_custos_extras_pagaveis(
            incluir_id=self.instance.custo_extra_id if self.instance.pk else None,
        )
