from django import forms

from .models import Evento
from .models_custos_extras import EventoCustoExtra


class EventoCustoExtraForm(forms.ModelForm):
    class Meta:
        model = EventoCustoExtra
        fields = [
            "evento",
            "categoria",
            "descricao",
            "valor_previsto",
            "valor_pago",
            "data_vencimento",
            "observacao",
        ]
        widgets = {
            "data_vencimento": forms.DateInput(attrs={"type": "date"}),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evento"].queryset = Evento.objects.select_related("cliente").order_by("-data_inicio", "-id")
        self.fields["valor_pago"].disabled = True
