from decimal import Decimal

from django.utils import timezone

from .constants_financeiros import STATUS_CANCELADO, STATUS_REALIZADO
from .models_fci import Investimento
from .selectors_opcoes_filtros import (
    listar_clientes_filtro,
    listar_contratos_visuais_filtro,
    listar_eventos_filtro_recentes,
)
from .utils_contratos import (
    montar_filtro_evento_ou_orcamento_por_contrato_visual,
    resolver_codigo_contrato_visual_parametros,
)
from .utils_financeiros import quantizar_moeda
from .utils_periodos import (
    PERIODOS_FRONTEND_PARA_RAPIDO,
    intervalo_periodo_frontend,
    normalizar_intervalo_datas,
    normalizar_periodo_frontend,
    normalizar_periodo_rapido,
    resolver_periodo_rapido_com_sessao,
)
from .utils_request import normalizar_data_iso


NOMES_CATEGORIAS_INVESTIMENTO = dict(Investimento.CATEGORIA_CHOICES)


def valor_filtro_operacional(filtros, *nomes):
    for nome in nomes:
        valor = filtros.get(nome)
        if valor not in (None, ""):
            return str(valor).strip()

    return ""


def filtro_id_operacional_invalido(valor):
    valor_id = str(valor or "").strip()
    return bool(valor_id and not valor_id.isdigit())


def valor_filtro_evento(filtros):
    return valor_filtro_operacional(
        filtros,
        "eventId",
        "costCenterId",
        "evento_id",
        "evento",
    )


def valor_filtro_cliente(filtros):
    return valor_filtro_operacional(filtros, "clientId", "cliente_id", "cliente")


def filtro_cliente_id_invalido(filtros):
    return filtro_id_operacional_invalido(valor_filtro_cliente(filtros))


def valor_filtro_codigo_contrato(filtros):
    return resolver_codigo_contrato_visual_parametros(filtros)


def resolver_periodo_investimentos(filtros, session):
    periodo_explicito = any(
        filtros.get(nome)
        for nome in (
            "data_inicial",
            "data_final",
            "startDate",
            "endDate",
            "period",
            "quickPeriod",
            "periodo_rapido",
        )
    )
    data_inicial = normalizar_data_iso(
        filtros.get("data_inicial") or filtros.get("startDate") or ""
    )
    data_final = normalizar_data_iso(
        filtros.get("data_final") or filtros.get("endDate") or ""
    )
    data_inicial, data_final = normalizar_intervalo_datas(data_inicial, data_final)
    periodo = normalizar_periodo_frontend(filtros.get("period"))
    periodo_rapido = normalizar_periodo_rapido(
        filtros.get("quickPeriod") or filtros.get("periodo_rapido")
    )
    categoria = str(filtros.get("category") or filtros.get("categoria") or "").strip()
    tipo_fluxo = str(filtros.get("flowType") or filtros.get("tipo_fluxo") or "").strip()
    status = str(filtros.get("status") or "").strip()
    contrato_codigo = valor_filtro_codigo_contrato(filtros)
    cliente_id = valor_filtro_cliente(filtros)
    filtro_sem_periodo = any(
        [
            categoria,
            tipo_fluxo,
            status,
            valor_filtro_evento(filtros),
            contrato_codigo,
            cliente_id,
        ]
    )

    if data_inicial or data_final:
        periodo_rapido = "vencidos" if periodo_rapido == "vencidos" else ""
    elif periodo in PERIODOS_FRONTEND_PARA_RAPIDO:
        periodo_rapido = PERIODOS_FRONTEND_PARA_RAPIDO[periodo]
    elif periodo:
        data_inicial, data_final = intervalo_periodo_frontend(periodo)
        periodo_rapido = ""
    elif not periodo_explicito and filtro_sem_periodo:
        periodo_rapido = "todos"

    filtros = {
        **filtros,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "period": periodo,
        "periodo_rapido": periodo_rapido,
        "categoria": categoria,
        "tipo_fluxo": tipo_fluxo,
        "status": status,
        "contractCode": contrato_codigo,
        "contrato_codigo": contrato_codigo,
        "cliente": cliente_id,
        "clientId": cliente_id,
        "cliente_id": cliente_id,
    }
    return resolver_periodo_rapido_com_sessao(
        filtros,
        session,
        "fci_periodo_rapido",
    )


def filtrar_investimentos(filtros):
    investimentos = Investimento.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).filter(ativo=True)
    hoje = timezone.localdate()

    if filtros["periodo_rapido"] == "vencidos":
        investimentos = investimentos.filter(data_prevista__lt=hoje).exclude(
            status__in=[STATUS_REALIZADO, STATUS_CANCELADO],
        )

    if filtros["data_inicial"]:
        investimentos = investimentos.filter(data_prevista__gte=filtros["data_inicial"])

    if filtros["data_final"]:
        investimentos = investimentos.filter(data_prevista__lte=filtros["data_final"])

    if filtros["categoria"]:
        investimentos = investimentos.filter(categoria=filtros["categoria"])

    if filtros["tipo_fluxo"]:
        investimentos = investimentos.filter(tipo_fluxo=filtros["tipo_fluxo"])

    if filtros["status"]:
        investimentos = investimentos.filter(status=filtros["status"])

    evento_id = valor_filtro_evento(filtros)
    if evento_id:
        if filtro_id_operacional_invalido(evento_id):
            return investimentos.none()

        investimentos = investimentos.filter(evento_id=evento_id)

    contrato_codigo = valor_filtro_codigo_contrato(filtros)
    if contrato_codigo:
        investimentos = investimentos.filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "evento__",
                contrato_codigo,
            )
        )

    cliente_id = valor_filtro_cliente(filtros)
    if cliente_id:
        if filtro_cliente_id_invalido(filtros):
            return investimentos.none()

        investimentos = investimentos.filter(evento__cliente_id=cliente_id)

    return investimentos


def listar_investimentos_ordenados(investimentos):
    return list(
        investimentos.order_by(
            "categoria",
            "data_prevista",
            "descricao",
            "id",
        )
    )


def listar_investimentos_recentes(lista_investimentos):
    return sorted(
        lista_investimentos,
        key=lambda investimento: (
            investimento.data_prevista,
            investimento.id,
        ),
        reverse=True,
    )


def totais_investimentos(lista_investimentos):
    total_previsto_entrada = Decimal("0.00")
    total_previsto_saida = Decimal("0.00")
    total_realizado_entrada = Decimal("0.00")
    total_realizado_saida = Decimal("0.00")

    for investimento in lista_investimentos:
        if investimento.tipo_fluxo == "entrada":
            total_previsto_entrada += investimento.valor_previsto
            total_realizado_entrada += investimento.valor_realizado
        else:
            total_previsto_saida += investimento.valor_previsto
            total_realizado_saida += investimento.valor_realizado

    resultado_financeiro_projetado = quantizar_moeda(
        total_previsto_entrada - total_previsto_saida
    )
    resultado_financeiro_realizado = quantizar_moeda(
        total_realizado_entrada - total_realizado_saida
    )

    return {
        "total_previsto_entrada": total_previsto_entrada,
        "total_previsto_saida": total_previsto_saida,
        "total_realizado_entrada": total_realizado_entrada,
        "total_realizado_saida": total_realizado_saida,
        "plannedInflowAmount": total_previsto_entrada,
        "plannedOutflowAmount": total_previsto_saida,
        "realizedInflowAmount": total_realizado_entrada,
        "realizedOutflowAmount": total_realizado_saida,
        "entradas_investimento_projetadas": quantizar_moeda(total_previsto_entrada),
        "saidas_investimento_projetadas": quantizar_moeda(total_previsto_saida),
        "entradas_investimento_realizadas": quantizar_moeda(total_realizado_entrada),
        "saidas_investimento_realizadas": quantizar_moeda(total_realizado_saida),
        "projectedInflowAmount": quantizar_moeda(total_previsto_entrada),
        "projectedOutflowAmount": quantizar_moeda(total_previsto_saida),
        "saldo_previsto_fci": resultado_financeiro_projetado,
        "saldo_realizado_fci": resultado_financeiro_realizado,
        "resultado_financeiro_fci_previsto": resultado_financeiro_projetado,
        "resultado_financeiro_fci_projetado": resultado_financeiro_projetado,
        "resultado_financeiro_fci_realizado": resultado_financeiro_realizado,
        "resultado_financeiro_investimentos_projetado": resultado_financeiro_projetado,
        "resultado_financeiro_investimentos_realizado": resultado_financeiro_realizado,
        "plannedFinancialResultAmount": resultado_financeiro_projetado,
        "projectedFinancialResultAmount": resultado_financeiro_projetado,
        "realizedFinancialResultAmount": resultado_financeiro_realizado,
    }


def categorias_investimento_para_filtro():
    return Investimento.CATEGORIA_CHOICES


def tipos_fluxo_investimento_para_filtro():
    return Investimento.TIPO_FLUXO_CHOICES


def status_investimento_para_filtro():
    return Investimento.STATUS_CHOICES


def agrupar_investimentos_por_categoria(lista_investimentos):
    grupos_categoria = []
    categoria_atual = None
    grupo_atual = None

    for item in lista_investimentos:
        if item.categoria != categoria_atual:
            if grupo_atual:
                _finalizar_grupo(grupo_atual)
                grupos_categoria.append(grupo_atual)

            grupo_atual = {
                "categoria": item.categoria,
                "categoria_nome": NOMES_CATEGORIAS_INVESTIMENTO.get(item.categoria, item.categoria),
                "itens": [],
                "subtotal_previsto_entrada": Decimal("0.00"),
                "subtotal_previsto_saida": Decimal("0.00"),
                "subtotal_realizado_entrada": Decimal("0.00"),
                "subtotal_realizado_saida": Decimal("0.00"),
                "subtotal_resultado_financeiro_previsto": Decimal("0.00"),
                "subtotal_resultado_financeiro_realizado": Decimal("0.00"),
                "subtotal_saldo_previsto": Decimal("0.00"),
                "subtotal_saldo_realizado": Decimal("0.00"),
                "subtotal_entradas_projetadas": Decimal("0.00"),
                "subtotal_saidas_projetadas": Decimal("0.00"),
                "subtotal_entradas_realizadas": Decimal("0.00"),
                "subtotal_saidas_realizadas": Decimal("0.00"),
                "quantidade": 0,
            }
            categoria_atual = item.categoria

        grupo_atual["itens"].append(item)
        grupo_atual["quantidade"] += 1

        if item.tipo_fluxo == "entrada":
            grupo_atual["subtotal_previsto_entrada"] += item.valor_previsto
            grupo_atual["subtotal_realizado_entrada"] += item.valor_realizado
            grupo_atual["subtotal_entradas_projetadas"] += item.valor_previsto
            grupo_atual["subtotal_entradas_realizadas"] += item.valor_realizado
        else:
            grupo_atual["subtotal_previsto_saida"] += item.valor_previsto
            grupo_atual["subtotal_realizado_saida"] += item.valor_realizado
            grupo_atual["subtotal_saidas_projetadas"] += item.valor_previsto
            grupo_atual["subtotal_saidas_realizadas"] += item.valor_realizado

    if grupo_atual:
        _finalizar_grupo(grupo_atual)
        grupos_categoria.append(grupo_atual)

    return grupos_categoria


def _finalizar_grupo(grupo):
    grupo["subtotal_saldo_previsto"] = quantizar_moeda(
        grupo["subtotal_previsto_entrada"] - grupo["subtotal_previsto_saida"]
    )
    grupo["subtotal_saldo_realizado"] = quantizar_moeda(
        grupo["subtotal_realizado_entrada"] - grupo["subtotal_realizado_saida"]
    )
    grupo["subtotal_resultado_financeiro_previsto"] = grupo["subtotal_saldo_previsto"]
    grupo["subtotal_resultado_financeiro_projetado"] = grupo["subtotal_saldo_previsto"]
    grupo["subtotal_resultado_financeiro_realizado"] = grupo["subtotal_saldo_realizado"]
    grupo["subtotal_resultado_investimento_projetado"] = grupo["subtotal_saldo_previsto"]
    grupo["subtotal_resultado_investimento_realizado"] = grupo["subtotal_saldo_realizado"]


def montar_contexto_investimentos(filtros_raw, session):
    filtros = resolver_periodo_investimentos(filtros_raw, session)
    investimentos = filtrar_investimentos(filtros)
    lista_investimentos = listar_investimentos_ordenados(investimentos)
    totais = totais_investimentos(lista_investimentos)

    return {
        "investimentos": listar_investimentos_recentes(lista_investimentos),
        "grupos_categoria": agrupar_investimentos_por_categoria(lista_investimentos),
        **totais,
        "categorias_investimento": categorias_investimento_para_filtro(),
        "tipos_fluxo_investimento": tipos_fluxo_investimento_para_filtro(),
        "status_investimento": status_investimento_para_filtro(),
        "contratos_filtro": listar_contratos_visuais_filtro(),
        "eventos_filtro": listar_eventos_filtro_recentes(),
        "clientes_filtro": listar_clientes_filtro(),
        "periodo_rapido": filtros["periodo_rapido"],
        "filtros": {
            "data_inicial": filtros["data_inicial"],
            "data_final": filtros["data_final"],
            "startDate": filtros["data_inicial"],
            "endDate": filtros["data_final"],
            "period": filtros["period"],
            "quickPeriod": filtros["periodo_rapido"],
            "category": filtros["categoria"],
            "categoria": filtros["categoria"],
            "flowType": filtros["tipo_fluxo"],
            "tipo_fluxo": filtros["tipo_fluxo"],
            "status": filtros["status"],
            "contractCode": filtros["contractCode"],
            "contrato_codigo": filtros["contrato_codigo"],
            "evento": valor_filtro_evento(filtros),
            "costCenterId": valor_filtro_evento(filtros),
            "eventId": valor_filtro_evento(filtros),
            "evento_id": valor_filtro_evento(filtros),
            "cliente": filtros["cliente"],
            "clientId": filtros["clientId"],
            "cliente_id": filtros["cliente_id"],
        },
    }
