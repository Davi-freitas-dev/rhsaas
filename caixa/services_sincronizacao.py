from django.db import transaction

from .services_custos_extras import sincronizar_despesas_custos_extras_evento
from .services_evento import sincronizar_despesas_operacionais_evento


def sincronizar_evento_financeiro(evento):
    """Atualiza despesas derivadas e recalcula os totais salvos do evento."""
    with transaction.atomic():
        sincronizar_despesas_operacionais_evento(evento, recalcular=False)
        sincronizar_despesas_custos_extras_evento(evento, recalcular=False)
        evento_atualizado = evento.__class__.objects.get(pk=evento.pk)
        evento_atualizado.recalcular_custo_previsto()
        evento_atualizado.recalcular_realizado()
        evento.refresh_from_db()
