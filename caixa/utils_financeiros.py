from decimal import Decimal


ZERO_DECIMAL = Decimal("0.00")
DUAS_CASAS = Decimal("0.01")


def decimal_zero(valor):
    return valor or ZERO_DECIMAL


def quantizar_moeda(valor):
    return decimal_zero(valor).quantize(DUAS_CASAS)
