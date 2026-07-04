from decimal import Decimal
from django.db import transaction

from .models import DespesaOperacional
from .models_custos_extras import EventoCustoExtra


MAPA_CATEGORIA_DESPESA = {
    "insumo": "material",
    "material": "material",
    "uniforme": "uniforme",
    "logistica": "outros",
    "comissao": "comissao",
    "outros": "outros",
}


def sincronizar_despesas_custos_extras_evento(evento, recalcular=True):
    custos = EventoCustoExtra.objects.filter(evento=evento).order_by("id")

    with transaction.atomic():
        DespesaOperacional.objects.filter(
            evento=evento,
            categoria="outros",
            descricao="Custos extras previstos",
        ).delete()

        despesas_ids_validas = []

        for custo in custos:
            categoria_despesa = MAPA_CATEGORIA_DESPESA.get(custo.categoria, "outros")
            descricao = f"Custo extra: {custo.descricao}"

            despesas_sincronizadas = list(
                DespesaOperacional.objects.filter(
                    evento=evento,
                    origem=DespesaOperacional.ORIGEM_CUSTO_EXTRA,
                    origem_custo_extra=custo,
                )
                .order_by("id")
            )
            despesas_legadas_reservadas = list(
                DespesaOperacional.objects.filter(
                    evento=evento,
                    origem=DespesaOperacional.ORIGEM_MANUAL,
                    descricao=descricao,
                ).order_by("id")
            )

            if despesas_sincronizadas:
                despesa = despesas_sincronizadas[0]
                despesas_duplicadas = (
                    despesas_sincronizadas[1:] + despesas_legadas_reservadas
                )
            elif despesas_legadas_reservadas:
                despesa = despesas_legadas_reservadas[0]
                despesas_duplicadas = despesas_legadas_reservadas[1:]
            else:
                despesa = DespesaOperacional(
                    evento=evento,
                    descricao=descricao,
                    categoria=categoria_despesa,
                    valor_previsto=custo.valor_previsto,
                    valor_pago=custo.valor_pago,
                    data_vencimento=custo.data_vencimento,
                    observacao=custo.observacao,
                    origem=DespesaOperacional.ORIGEM_CUSTO_EXTRA,
                    origem_custo_extra=custo,
                )
                despesas_duplicadas = []

            # Atualiza sempre
            despesa.descricao = descricao
            despesa.categoria = categoria_despesa
            despesa.valor_previsto = custo.valor_previsto
            despesa.valor_pago = custo.valor_pago
            despesa.data_vencimento = custo.data_vencimento
            despesa.observacao = custo.observacao
            despesa.origem = DespesaOperacional.ORIGEM_CUSTO_EXTRA
            despesa.origem_custo_servico_tipo = ""
            despesa.origem_custo_extra = custo
            despesa.baixado_manualmente = custo.quitado
            despesa.motivo_baixa = (
                custo.motivo_baixa.strip()
                if custo.quitado and custo.motivo_baixa.strip()
                else "Baixa manual informada no custo extra."
                if custo.quitado
                else ""
            )

            # Define status automaticamente
            if (
                custo.valor_previsto == Decimal("0.00")
                and custo.valor_pago == Decimal("0.00")
            ):
                despesa.status = "cancelado"
            elif custo.quitado:
                despesa.status = "pago"
            elif custo.valor_pago >= custo.valor_previsto:
                despesa.status = "pago"
            elif custo.valor_pago > Decimal("0.00"):
                despesa.status = "parcial"
            else:
                despesa.status = "pendente"

            despesa.save(sincronizacao_origem=True)

            if despesas_duplicadas:
                DespesaOperacional.objects.filter(
                    id__in=[item.id for item in despesas_duplicadas]
                ).delete()

            despesas_ids_validas.append(despesa.id)

        # Remove despesas antigas que não existem mais
        DespesaOperacional.objects.filter(
            evento=evento,
            origem=DespesaOperacional.ORIGEM_CUSTO_EXTRA,
        ).exclude(id__in=despesas_ids_validas).delete()

    if recalcular:
        evento.recalcular_custo_previsto()
        evento.recalcular_realizado()
