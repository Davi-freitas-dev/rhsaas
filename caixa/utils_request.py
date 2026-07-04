from datetime import date


def texto_filtro(request, nome):
    return request.GET.get(nome, "").strip()


def filtros_texto(request, nomes, defaults=None):
    defaults = defaults or {}
    return {
        nome: texto_filtro(request, nome) or defaults.get(nome, "")
        for nome in nomes
    }


def normalizar_data_iso(valor):
    valor = str(valor or "").strip()
    if not valor:
        return ""

    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError:
        return ""


def normalizar_mes_iso(valor):
    valor = str(valor or "").strip()
    if not valor:
        return ""

    try:
        ano, mes = [int(parte) for parte in valor.split("-", 1)]
        date(ano, mes, 1)
    except (ValueError, TypeError):
        return ""

    return f"{ano:04d}-{mes:02d}"


def data_filtro(request, nome):
    return normalizar_data_iso(request.GET.get(nome, ""))


def mes_filtro(request, nome):
    return normalizar_mes_iso(request.GET.get(nome, ""))
