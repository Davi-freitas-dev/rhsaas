from decimal import Decimal

from django.utils import timezone

from .constants_financeiros import STATUS_CANCELADO, STATUS_PAGO
from .models_custo_fixo import CustoFixo
from .utils_financeiros import quantizar_moeda
from .utils_periodos import resolver_periodo_rapido_com_sessao


NOMES_CATEGORIAS_CUSTO_FIXO = dict(CustoFixo.CATEGORIA_CHOICES)

OPCOES_RECORRENTE_CUSTO_FIXO = (
    ("sim", "Sim"),
    ("nao", "Não"),
)

OPCOES_TIPO_REGISTRO_CUSTO_FIXO = (
    ("manual", "Manual"),
    ("automatico", "Automático"),
)


def resolver_periodo_custos_fixos(filtros, session):
    return resolver_periodo_rapido_com_sessao(
        filtros,
        session,
        "custos_fixos_periodo_rapido",
    )


def filtrar_custos_fixos(filtros):
    custos = CustoFixo.objects.filter(ativo=True)
    hoje = timezone.localdate()

    if filtros["periodo_rapido"] == "vencidos":
        custos = custos.filter(data_vencimento__lt=hoje).exclude(
            status__in=[STATUS_PAGO, STATUS_CANCELADO],
        )

    if filtros["data_inicial"]:
        custos = custos.filter(data_vencimento__gte=filtros["data_inicial"])

    if filtros["data_final"]:
        custos = custos.filter(data_vencimento__lte=filtros["data_final"])

    if filtros["categoria"]:
        custos = custos.filter(categoria=filtros["categoria"])

    if filtros["status"]:
        custos = custos.filter(status=filtros["status"])

    if filtros["recorrente"] == "sim":
        custos = custos.filter(recorrente=True)
    elif filtros["recorrente"] == "nao":
        custos = custos.filter(recorrente=False)

    if filtros["tipo_registro"] == "manual":
        custos = custos.filter(gerado_automaticamente=False)
    elif filtros["tipo_registro"] == "automatico":
        custos = custos.filter(gerado_automaticamente=True)

    return custos


def listar_custos_fixos_ordenados(custos):
    return list(
        custos.order_by("categoria", "data_vencimento", "descricao", "id")
    )


def totais_custos_fixos(lista_custos):
    total_previsto = sum(
        (custo.valor_previsto for custo in lista_custos),
        Decimal("0.00"),
    )
    total_pago = sum(
        (custo.valor_pago for custo in lista_custos),
        Decimal("0.00"),
    )
    total_contas_pendentes = sum(
        (quantizar_moeda(custo.valor_pendente_pagamento) for custo in lista_custos),
        Decimal("0.00"),
    )
    total_contas_pendentes = quantizar_moeda(total_contas_pendentes)
    quantidade_manuais = sum(
        (1 for custo in lista_custos if not custo.gerado_automaticamente),
        0,
    )
    quantidade_automaticos = sum(
        (1 for custo in lista_custos if custo.gerado_automaticamente),
        0,
    )

    return {
        "total_previsto": quantizar_moeda(total_previsto),
        "total_pago": quantizar_moeda(total_pago),
        "total_contas_pendentes": total_contas_pendentes,
        "total_valor_pendente_pagamento": total_contas_pendentes,
        "total_em_aberto": total_contas_pendentes,
        "pendingAccountsAmount": total_contas_pendentes,
        "pendingPaymentAmount": total_contas_pendentes,
        "quantidade": len(lista_custos),
        "quantidade_manuais": quantidade_manuais,
        "quantidade_automaticos": quantidade_automaticos,
    }


def categorias_custo_fixo_para_filtro():
    return CustoFixo.CATEGORIA_CHOICES


def status_custo_fixo_para_filtro():
    return CustoFixo.STATUS_CHOICES


def recorrencia_custo_fixo_para_filtro():
    return OPCOES_RECORRENTE_CUSTO_FIXO


def tipos_registro_custo_fixo_para_filtro():
    return OPCOES_TIPO_REGISTRO_CUSTO_FIXO


def agrupar_custos_fixos_por_categoria(lista_custos):
    hoje = timezone.localdate()
    grupos_categoria = []
    categoria_atual = None
    grupo_atual = None

    for item in lista_custos:
        if item.categoria != categoria_atual:
            if grupo_atual:
                _finalizar_grupo(grupo_atual)
                grupos_categoria.append(grupo_atual)

            grupo_atual = {
                "categoria": item.categoria,
                "categoria_nome": NOMES_CATEGORIAS_CUSTO_FIXO.get(item.categoria, item.categoria),
                "itens": [],
                "subtotal_previsto": Decimal("0.00"),
                "subtotal_pago": Decimal("0.00"),
                "subtotal_contas_pendentes": Decimal("0.00"),
                "subtotal_valor_pendente_pagamento": Decimal("0.00"),
                "subtotal_em_aberto": Decimal("0.00"),
                "quantidade": 0,
                "quantidade_vencidos": 0,
            }
            categoria_atual = item.categoria

        valor_pendente_item = quantizar_moeda(item.valor_pendente_pagamento)

        grupo_atual["itens"].append(item)
        grupo_atual["subtotal_previsto"] += item.valor_previsto
        grupo_atual["subtotal_pago"] += item.valor_pago
        grupo_atual["subtotal_contas_pendentes"] += valor_pendente_item
        grupo_atual["subtotal_valor_pendente_pagamento"] += valor_pendente_item
        grupo_atual["subtotal_em_aberto"] += valor_pendente_item
        grupo_atual["quantidade"] += 1

        if item.data_vencimento < hoje and valor_pendente_item > Decimal("0.00"):
            grupo_atual["quantidade_vencidos"] += 1

    if grupo_atual:
        _finalizar_grupo(grupo_atual)
        grupos_categoria.append(grupo_atual)

    return grupos_categoria


def _finalizar_grupo(grupo):
    grupo["subtotal_previsto"] = quantizar_moeda(grupo["subtotal_previsto"])
    grupo["subtotal_pago"] = quantizar_moeda(grupo["subtotal_pago"])
    grupo["subtotal_contas_pendentes"] = quantizar_moeda(
        grupo["subtotal_contas_pendentes"]
    )
    grupo["subtotal_valor_pendente_pagamento"] = quantizar_moeda(
        grupo["subtotal_valor_pendente_pagamento"]
    )
    grupo["subtotal_em_aberto"] = quantizar_moeda(grupo["subtotal_em_aberto"])
    grupo["subtotalPendingAccountsAmount"] = grupo["subtotal_contas_pendentes"]
    grupo["subtotalPendingPaymentAmount"] = grupo[
        "subtotal_valor_pendente_pagamento"
    ]


def montar_contexto_custos_fixos(filtros_raw, session):
    filtros = resolver_periodo_custos_fixos(filtros_raw, session)
    custos = filtrar_custos_fixos(filtros)
    lista_custos = listar_custos_fixos_ordenados(custos)
    totais = totais_custos_fixos(lista_custos)

    return {
        "grupos_categoria": agrupar_custos_fixos_por_categoria(lista_custos),
        **totais,
        "categorias_custo_fixo": categorias_custo_fixo_para_filtro(),
        "status_custo_fixo": status_custo_fixo_para_filtro(),
        "opcoes_recorrente": recorrencia_custo_fixo_para_filtro(),
        "opcoes_tipo_registro": tipos_registro_custo_fixo_para_filtro(),
        "periodo_rapido": filtros["periodo_rapido"],
        "filtros": {
            "data_inicial": filtros["data_inicial"],
            "data_final": filtros["data_final"],
            "categoria": filtros["categoria"],
            "status": filtros["status"],
            "recorrente": filtros["recorrente"],
            "tipo_registro": filtros["tipo_registro"],
        },
    }
