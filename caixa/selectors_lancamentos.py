from decimal import Decimal

from django.db.models import Q, Sum

from .constants_financeiros import TIPO_FLUXO_ENTRADA, TIPO_FLUXO_SAIDA
from .models import LancamentoFinanceiro, ORIGENS_LANCAMENTO_FINANCEIRO
from .utils_contratos import (
    montar_filtro_evento_ou_orcamento_por_contrato_visual,
    resolver_codigo_contrato_visual_parametros,
)
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")

FILTROS_ORIGEM_OBRIGACAO_LEDGER = {
    "despesa_operacional": "despesa_operacional_id",
    "custo_fixo": "custo_fixo_id",
    "custo_servico": "pagamento_custo_servico__custo_servico_id",
    "custo_extra": "pagamento_custo_extra__custo_extra_id",
    "parcela_divida": "pagamento_parcela_divida__parcela_id",
    "investimento": "investimento_id",
    "financiamento_movimentacao": "financiamento_movimentacao_id",
}


def filtrar_lancamentos_financeiros(filtros=None):
    filtros = filtros or {}
    queryset = LancamentoFinanceiro.objects.all()
    if _filtro_operacional_invalido(filtros):
        return queryset.none()

    data_inicial = filtros.get("data_inicial") or filtros.get("startDate")
    data_final = filtros.get("data_final") or filtros.get("endDate")
    evento_id = (
        filtros.get("evento")
        or filtros.get("evento_id")
        or filtros.get("eventId")
        or filtros.get("costCenterId")
    )
    cliente_id = filtros.get("cliente") or filtros.get("cliente_id") or filtros.get("clientId")
    contrato_codigo = resolver_codigo_contrato_visual_parametros(filtros)
    fluxo = filtros.get("fluxo") or filtros.get("cashFlowGroup")
    natureza = filtros.get("natureza") or filtros.get("nature")
    origem = filtros.get("origem") or filtros.get("origin")
    source_filter = filtros.get("source") or filtros.get("origem_obrigacao")
    origem_id = (
        filtros.get("sourceId")
        or filtros.get("source_id")
        or filtros.get("originId")
        or filtros.get("origin_id")
    )
    origem_obrigacao = (
        source_filter
        if origem_id and source_filter in FILTROS_ORIGEM_OBRIGACAO_LEDGER
        else ""
    )
    if not origem and not origem_obrigacao and source_filter in ORIGENS_LANCAMENTO_FINANCEIRO:
        origem = source_filter

    origem_detalhe = filtros.get("sourceDetail") or filtros.get("source_detail")
    status = filtros.get("status")
    tipo = filtros.get("tipo") or filtros.get("type")
    busca = filtros.get("busca") or filtros.get("search")

    if data_inicial:
        queryset = queryset.filter(data_lancamento__gte=data_inicial)

    if data_final:
        queryset = queryset.filter(data_lancamento__lte=data_final)

    if evento_id:
        queryset = queryset.filter(evento_id=evento_id)

    if cliente_id:
        queryset = queryset.filter(cliente_id=cliente_id)

    if contrato_codigo:
        queryset = queryset.filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "evento__",
                contrato_codigo,
            )
        )

    if fluxo:
        queryset = queryset.filter(fluxo=fluxo)

    if natureza:
        queryset = queryset.filter(natureza=natureza)

    queryset = filtrar_por_origem_obrigacao(
        queryset,
        origem_obrigacao,
        origem_id,
        origem_detalhe,
    )

    if not origem_obrigacao and origem in ORIGENS_LANCAMENTO_FINANCEIRO:
        queryset = queryset.filter(**{f"{origem}__isnull": False})
        if origem_id:
            queryset = queryset.filter(**{f"{origem}_id": origem_id})

    if status:
        queryset = queryset.filter(status=status)

    if tipo:
        queryset = queryset.filter(tipo=tipo)

    if busca:
        queryset = queryset.filter(
            Q(descricao__icontains=busca)
            | Q(observacao__icontains=busca)
            | Q(cliente__nome_razao_social__icontains=busca)
            | Q(evento__orcamento__numero__icontains=busca)
            | Q(evento__numero__icontains=busca)
            | Q(evento__nome_evento__icontains=busca)
        )

    return queryset


def filtrar_por_origem_obrigacao(queryset, origem, origem_id, origem_detalhe=""):
    if not origem or not origem_id:
        return queryset

    campo_id = FILTROS_ORIGEM_OBRIGACAO_LEDGER.get(origem)
    if not campo_id:
        return queryset

    queryset = queryset.filter(**{campo_id: origem_id})

    if origem == "custo_servico" and origem_detalhe:
        queryset = queryset.filter(pagamento_custo_servico__tipo=origem_detalhe)

    return queryset


def _filtro_operacional_invalido(filtros):
    return any(
        filtros.get(nome) == "__invalid__"
        for nome in (
            "eventId",
            "evento",
            "evento_id",
            "clientId",
            "cliente",
            "cliente_id",
            "sourceId",
            "source_id",
            "originId",
            "origin_id",
        )
    )


def somar_lancamentos(queryset, condicao):
    return quantizar_moeda(
        queryset.filter(condicao).aggregate(total=Sum("valor"))["total"] or ZERO
    )


def calcular_totais_lancamentos_financeiros(filtros=None):
    queryset = filtrar_lancamentos_financeiros(filtros)
    totais = queryset.aggregate(
        entradas=Sum("valor", filter=Q(tipo=TIPO_FLUXO_ENTRADA)),
        saidas=Sum("valor", filter=Q(tipo=TIPO_FLUXO_SAIDA)),
        fco_entradas=Sum(
            "valor",
            filter=Q(fluxo=LancamentoFinanceiro.FLUXO_FCO, tipo=TIPO_FLUXO_ENTRADA),
        ),
        fco_saidas=Sum(
            "valor",
            filter=Q(fluxo=LancamentoFinanceiro.FLUXO_FCO, tipo=TIPO_FLUXO_SAIDA),
        ),
        fci_entradas=Sum(
            "valor",
            filter=Q(fluxo=LancamentoFinanceiro.FLUXO_FCI, tipo=TIPO_FLUXO_ENTRADA),
        ),
        fci_saidas=Sum(
            "valor",
            filter=Q(fluxo=LancamentoFinanceiro.FLUXO_FCI, tipo=TIPO_FLUXO_SAIDA),
        ),
        fcf_entradas=Sum(
            "valor",
            filter=Q(fluxo=LancamentoFinanceiro.FLUXO_FCF, tipo=TIPO_FLUXO_ENTRADA),
        ),
        fcf_saidas=Sum(
            "valor",
            filter=Q(fluxo=LancamentoFinanceiro.FLUXO_FCF, tipo=TIPO_FLUXO_SAIDA),
        ),
    )
    entradas = decimal_total(totais["entradas"])
    saidas = decimal_total(totais["saidas"])

    return {
        "entradas": entradas,
        "saidas": saidas,
        "resultado_financeiro": quantizar_moeda(entradas - saidas),
        "fco": montar_totais_fluxo_agregado(totais, "fco"),
        "fci": montar_totais_fluxo_agregado(totais, "fci"),
        "fcf": montar_totais_fluxo_agregado(totais, "fcf"),
    }


def decimal_total(valor):
    return quantizar_moeda(valor or ZERO)


def montar_totais_fluxo_agregado(totais, fluxo):
    entradas = decimal_total(totais[f"{fluxo}_entradas"])
    saidas = decimal_total(totais[f"{fluxo}_saidas"])

    return {
        "entradas": entradas,
        "saidas": saidas,
        "resultado_financeiro": quantizar_moeda(entradas - saidas),
    }


def calcular_totais_fluxo(queryset, fluxo):
    queryset_fluxo = queryset.filter(fluxo=fluxo)
    entradas = somar_lancamentos(queryset_fluxo, Q(tipo=TIPO_FLUXO_ENTRADA))
    saidas = somar_lancamentos(queryset_fluxo, Q(tipo=TIPO_FLUXO_SAIDA))

    return {
        "entradas": entradas,
        "saidas": saidas,
        "resultado_financeiro": quantizar_moeda(entradas - saidas),
    }


def calcular_totais_realizados_legados_dashboard(totais_financeiros):
    fco = {
        "entradas": totais_financeiros["total_entrada_fco_realizada"],
        "saidas": totais_financeiros["total_saida_fco_realizada"],
        "resultado_financeiro": totais_financeiros[
            "resultado_financeiro_operacional_realizado"
        ],
    }
    fci = {
        "entradas": totais_financeiros["total_realizado_entrada_fci"],
        "saidas": totais_financeiros["total_realizado_saida_fci"],
        "resultado_financeiro": totais_financeiros[
            "resultado_financeiro_fci_realizado"
        ],
    }
    fcf = {
        "entradas": totais_financeiros["total_realizado_entrada_fcf"],
        "saidas": totais_financeiros["total_realizado_saida_fcf"],
        "resultado_financeiro": totais_financeiros[
            "resultado_financeiro_fcf_realizado"
        ],
    }
    entradas = quantizar_moeda(fco["entradas"] + fci["entradas"] + fcf["entradas"])
    saidas = quantizar_moeda(fco["saidas"] + fci["saidas"] + fcf["saidas"])

    return {
        "entradas": entradas,
        "saidas": saidas,
        "resultado_financeiro": totais_financeiros[
            "resultado_financeiro_consolidado_realizado"
        ],
        "fco": fco,
        "fci": fci,
        "fcf": fcf,
    }


def comparar_totais_dashboard_com_lancamentos(params=None, session=None):
    from .selectors_dashboard import montar_dados_dashboard

    dados_dashboard = montar_dados_dashboard(params or {}, session or {})
    filtros_dashboard = dados_dashboard["filtros_dashboard"]
    totais_legados = calcular_totais_realizados_legados_dashboard(
        dados_dashboard["totais_financeiros"]
    )
    totais_lancamentos = calcular_totais_lancamentos_financeiros(filtros_dashboard)
    diferencas = calcular_diferencas_totais(totais_legados, totais_lancamentos)

    return {
        "filtros": filtros_dashboard,
        "legado": totais_legados,
        "lancamentos": totais_lancamentos,
        "diferencas": diferencas,
        "equivalente": all(valor == ZERO for valor in diferencas.values()),
    }


def calcular_diferencas_totais(totais_legados, totais_lancamentos):
    diferencas = {}

    for chave in ("entradas", "saidas", "resultado_financeiro"):
        diferencas[chave] = quantizar_moeda(
            totais_lancamentos[chave] - totais_legados[chave]
        )

    for fluxo in ("fco", "fci", "fcf"):
        for chave in ("entradas", "saidas", "resultado_financeiro"):
            diferencas[f"{fluxo}_{chave}"] = quantizar_moeda(
                totais_lancamentos[fluxo][chave] - totais_legados[fluxo][chave]
            )

    return diferencas
