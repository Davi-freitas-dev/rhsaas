from django import template
from ..utils_moeda import formatar_moeda_br, formatar_percentual_br

register = template.Library()


@register.filter
def moeda_br(valor):
    return formatar_moeda_br(valor)


@register.filter
def percentual_br(valor):
    return formatar_percentual_br(valor)
