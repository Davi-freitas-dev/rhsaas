from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PARCIAL,
    STATUS_PLANEJADO,
    STATUS_REALIZADO,
)
from .utils_financeiros import ZERO_DECIMAL, quantizar_moeda


def saldo_nao_negativo(valor_previsto, valor_realizado):
    saldo = valor_previsto - valor_realizado
    return quantizar_moeda(saldo if saldo > ZERO_DECIMAL else ZERO_DECIMAL)


def status_por_valor_previsto_realizado(status_atual, valor_previsto, valor_realizado):
    if status_atual == STATUS_CANCELADO:
        return status_atual

    if status_atual == STATUS_REALIZADO and valor_realizado > ZERO_DECIMAL:
        return status_atual

    if valor_realizado <= ZERO_DECIMAL:
        return STATUS_PLANEJADO

    if valor_realizado < valor_previsto:
        return STATUS_PARCIAL

    return STATUS_REALIZADO
