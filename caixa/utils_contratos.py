from django.db.models import Q


def normalizar_codigo_contrato_visual(valor):
    valor = str(valor or "").strip()
    if valor.upper().startswith("EVT-"):
        return valor[4:].strip()
    return valor


def codigos_contrato_visual_e_evento(valor):
    codigo = normalizar_codigo_contrato_visual(valor)
    if not codigo:
        return []
    return [codigo, f"EVT-{codigo}"]


def primeiro_codigo_contrato_visual(params, *nomes):
    for nome in nomes:
        valor = params.get(nome) if hasattr(params, "get") else None
        if valor not in (None, ""):
            return valor

    return ""


def resolver_codigo_contrato_visual_parametros(params):
    codigo = primeiro_codigo_contrato_visual(params, "contractCode", "contrato_codigo")
    return normalizar_codigo_contrato_visual(codigo)


def montar_filtro_evento_por_contrato_visual(
    prefixo_evento,
    contrato_codigo,
):
    filtro = Q()

    for codigo in codigos_contrato_visual_e_evento(contrato_codigo):
        filtro |= Q(**{f"{prefixo_evento}numero__iexact": codigo})
        filtro |= Q(**{f"{prefixo_evento}orcamento__numero__iexact": codigo})

    return filtro


def montar_filtro_evento_ou_orcamento_por_contrato_visual(
    prefixo_evento,
    contrato_codigo,
):
    filtro = montar_filtro_evento_por_contrato_visual(
        prefixo_evento,
        contrato_codigo,
    )

    return filtro
