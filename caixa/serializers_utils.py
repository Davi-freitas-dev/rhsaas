from decimal import Decimal


def serializar_valor(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor


def serializar_choices(opcoes):
    return [
        {
            "valor": valor,
            "rotulo": rotulo,
        }
        for valor, rotulo in opcoes
    ]


def serializar_choices_value_label(opcoes):
    return [
        {
            "valor": valor,
            "rotulo": rotulo,
            "value": valor,
            "label": rotulo,
        }
        for valor, rotulo in opcoes
    ]
