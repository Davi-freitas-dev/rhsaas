from decimal import Decimal

from django import forms
from django.utils import timezone

from .models_dividas import DividaFinanceira, PagamentoParcelaDivida, ParcelaDivida
from .selectors_pagamentos import (
    queryset_dividas_fcf_pagaveis,
    queryset_parcelas_fcf_pagaveis,
)


class PagamentoParcelaDividaAdminForm(forms.ModelForm):
    divida = forms.ModelChoiceField(
        queryset=DividaFinanceira.objects.none(),
        required=False,
        label="Dívida",
    )

    class Meta:
        model = PagamentoParcelaDivida
        fields = "__all__"

    class Media:
        js = ("caixa/js/pagamento_parcela_admin.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["data_pagamento"].initial = timezone.localdate()

        dividas_disponiveis = self._dividas_disponiveis()
        self.fields["divida"].queryset = dividas_disponiveis
        self.fields["parcela"].queryset = ParcelaDivida.objects.none()

        if self.instance and self.instance.pk and self.instance.parcela_id:
            self._configurar_parcela_da_instancia()
            return

        if self.data.get("divida"):
            self._configurar_parcelas_por_divida_id(self.data.get("divida"))
            return

        parcela_inicial = self.initial.get("parcela")
        if parcela_inicial:
            self._configurar_parcela_inicial(parcela_inicial)

    def _dividas_disponiveis(self):
        return queryset_dividas_fcf_pagaveis()

    def _dividas_disponiveis_com_divida(self, divida_id):
        return queryset_dividas_fcf_pagaveis(incluir_id=divida_id)

    def _configurar_parcela_da_instancia(self):
        parcela = self.instance.parcela
        self.fields["divida"].initial = parcela.divida
        self.fields["divida"].queryset = self._dividas_disponiveis_com_divida(parcela.divida_id)
        self.fields["parcela"].queryset = queryset_parcelas_fcf_pagaveis(
            incluir_id=parcela.id,
            divida_id=parcela.divida_id,
        )

    def _configurar_parcelas_por_divida_id(self, divida_id):
        try:
            divida_id = int(divida_id)
        except (ValueError, TypeError):
            return

        self.fields["parcela"].queryset = queryset_parcelas_fcf_pagaveis(
            divida_id=divida_id
        )

    def _configurar_parcela_inicial(self, parcela_inicial):
        try:
            parcela = queryset_parcelas_fcf_pagaveis().get(pk=parcela_inicial)
        except (ParcelaDivida.DoesNotExist, ValueError, TypeError):
            return

        self.fields["divida"].initial = parcela.divida
        self.fields["divida"].queryset = self._dividas_disponiveis_com_divida(parcela.divida_id)
        self.fields["parcela"].queryset = queryset_parcelas_fcf_pagaveis(
            divida_id=parcela.divida_id
        )


class PagamentoParcelaDividaForm(forms.ModelForm):
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
        model = PagamentoParcelaDivida
        fields = (
            "data_pagamento",
            "valor_pagamento",
            "forma_pagamento",
            "observacao",
            "baixar_saldo",
            "motivo_baixa",
        )
        widgets = {
            "data_pagamento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, parcela, **kwargs):
        super().__init__(*args, **kwargs)
        self.parcela = parcela
        self.instance.parcela = parcela

        if not self.instance.pk:
            self.fields["data_pagamento"].initial = timezone.localdate()
            self.fields["valor_pagamento"].initial = parcela.valor_pendente_pagamento

    def save(self, commit=True):
        self.instance.parcela = self.parcela
        return super().save(commit=commit)

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

    def _post_clean(self):
        valor_pagamento = self.cleaned_data.get("valor_pagamento")
        baixar_sem_novo_pagamento = (
            self.cleaned_data.get("baixar_saldo")
            and valor_pagamento == Decimal("0.00")
            and "valor_pagamento" not in self._errors
        )

        if baixar_sem_novo_pagamento:
            return

        super()._post_clean()
