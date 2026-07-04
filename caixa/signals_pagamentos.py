from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models_pagamentos import PagamentoEventoCustoExtra
from .services_pagamentos_custos_extras import atualizar_total_pago_custo_extra as atualizar_total_pago_custo_extra_service


@receiver(post_save, sender=PagamentoEventoCustoExtra)
@receiver(post_delete, sender=PagamentoEventoCustoExtra)
def atualizar_total_pago_custo_extra_apos_pagamento(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    atualizar_total_pago_custo_extra_service(instance.custo_extra)
