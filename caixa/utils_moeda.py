from decimal import Decimal, InvalidOperation


def formatar_moeda_br(valor):
    try:
        valor = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return "R$ 0,00"

    valor_formatado = f"{valor:,.2f}"
    valor_formatado = valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"R$ {valor_formatado}"


def formatar_percentual_br(valor):
    try:
        valor = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return "0,00%"

    valor_formatado = f"{valor:,.2f}"
    valor_formatado = valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{valor_formatado}%"
