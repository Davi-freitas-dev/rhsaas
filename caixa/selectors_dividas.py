from django.db.models import Q


def valor_filtro_credor(filtros):
    return (
        filtros.get("creditorId")
        or filtros.get("credor_id")
        or filtros.get("creditor")
        or filtros.get("credor")
        or ""
    )


def filtro_credor_usa_id_canonico(filtros):
    return bool(filtros.get("creditorId") or filtros.get("credor_id"))


def filtrar_por_credor_divida(queryset, valor, prefixo="divida__", id_estrito=False):
    valor_credor = str(valor or "").strip()
    if not valor_credor:
        return queryset

    filtro_id = {f"{prefixo}credor_cadastro_id": valor_credor}
    if id_estrito:
        if not valor_credor.isdigit():
            return queryset.none()

        return queryset.filter(**filtro_id)

    filtro_nome = {
        f"{prefixo}credor_cadastro__nome__icontains": valor_credor,
    }
    filtro_legado = {f"{prefixo}credor__icontains": valor_credor}

    if valor_credor.isdigit():
        return queryset.filter(Q(**filtro_id) | Q(**filtro_legado))

    return queryset.filter(Q(**filtro_nome) | Q(**filtro_legado))
