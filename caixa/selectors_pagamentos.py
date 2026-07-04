from decimal import Decimal

from django.db.models import Case, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When

from .constants_dividas import STATUS_PARCELAS_FINAIS
from .constants_financeiros import (
    TIPO_CUSTO_ALIMENTACAO,
    TIPO_CUSTO_DIARIAS,
    TIPO_CUSTO_TRANSPORTE,
    TIPOS_CUSTO_SERVICO,
)
from .models_custos_extras import EventoCustoExtra
from .models_dividas import DividaFinanceira, PagamentoParcelaDivida, ParcelaDivida
from .models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from .models_servico import EventoCustoServico
from .selectors_opcoes_filtros import (
    listar_credores_cadastrados_fcf_filtro,
    listar_credores_fcf_filtro,
    listar_eventos_filtro_com_custos_extras,
    listar_eventos_filtro_com_custos_servico,
    listar_tipos_divida_fcf_filtro,
)
from .selectors_dividas import (
    filtrar_por_credor_divida,
    filtro_credor_usa_id_canonico,
    valor_filtro_credor,
)
from .utils_financeiros import quantizar_moeda


SITUACAO_CONTAS_PENDENTES = "contas_pendentes"
SITUACAO_EM_ABERTO_LEGADO = "em_aberto"
SITUACAO_QUITADO = "quitado"
SITUACOES_CONTAS_PENDENTES = {
    SITUACAO_CONTAS_PENDENTES,
    SITUACAO_EM_ABERTO_LEGADO,
    "pendente",
}


def normalizar_situacao_liquidacao(situacao):
    if situacao in SITUACOES_CONTAS_PENDENTES:
        return SITUACAO_CONTAS_PENDENTES

    if situacao == SITUACAO_QUITADO:
        return SITUACAO_QUITADO

    return situacao or SITUACAO_CONTAS_PENDENTES


def _campo_moeda():
    return DecimalField(max_digits=12, decimal_places=2)


def _zero_moeda():
    return Value(Decimal("0.00"), output_field=_campo_moeda())


def listar_custos_servico(filtros):
    custos_query = (
        EventoCustoServico.objects.select_related("evento", "evento__cliente", "servico")
        .prefetch_related("pagamentos")
        .order_by("-evento__data_inicio", "evento__numero", "servico__nome")
    )

    custos_query = filtrar_por_id(custos_query, "evento_id", filtros.get("evento"))

    busca = filtros.get("busca", "").strip()
    if busca:
        custos_query = custos_query.filter(
            Q(evento__numero__icontains=busca)
            | Q(evento__nome_evento__icontains=busca)
            | Q(servico__nome__icontains=busca)
        )

    tipo = filtros.get("tipo")
    if tipo in TIPOS_CUSTO_SERVICO:
        custos_query = custos_query.filter(
            **{f"{TIPOS_CUSTO_SERVICO[tipo]['previsto']}__gt": Decimal("0.00")}
        )

    custos_query = filtrar_situacao_custos_servico(custos_query, filtros.get("situacao"))

    return list(custos_query)


def obter_custo_inicial(custo_id, custos):
    if not custo_id:
        return None

    for custo in custos:
        if str(custo.id) == str(custo_id) and custo.saldo_geral > Decimal("0.00"):
            return custo

    try:
        return (
            queryset_custos_servico_pagaveis()
            .get(pk=custo_id)
        )
    except (EventoCustoServico.DoesNotExist, ValueError, TypeError):
        return None


def queryset_custos_servico_pagaveis(incluir_id=None):
    custos_query = (
        EventoCustoServico.objects.select_related("evento", "evento__cliente", "servico")
        .prefetch_related("pagamentos")
        .order_by("-evento__data_inicio", "evento__numero", "servico__nome")
    )
    custos_query = anotar_saldo_custos_servico(custos_query)

    filtro = Q(_saldo_geral__gt=Decimal("0.00"))
    if incluir_id:
        filtro |= Q(pk=incluir_id)

    return custos_query.filter(filtro)


def obter_tipo_inicial(tipo):
    return tipo if tipo in TIPOS_CUSTO_SERVICO else None


def saldo_por_tipo(custo, tipo):
    if tipo not in TIPOS_CUSTO_SERVICO:
        return Decimal("0.00")

    return getattr(custo, TIPOS_CUSTO_SERVICO[tipo]["saldo"])


def listar_pagamentos_recentes_custo_servico():
    return (
        PagamentoEventoCustoServico.objects.select_related(
            "custo_servico",
            "custo_servico__evento",
            "custo_servico__servico",
        )
        .order_by("-data_pagamento", "-id")[:20]
    )


def listar_eventos_com_custos_servico():
    return listar_eventos_filtro_com_custos_servico()


def total_contas_pendentes_custos_servico(custos):
    return quantizar_moeda(
        sum((custo.saldo_geral for custo in custos), Decimal("0.00"))
    )


def total_em_aberto_custos_servico(custos):
    return total_contas_pendentes_custos_servico(custos)


def listar_custos_extras(filtros):
    custos_query = (
        EventoCustoExtra.objects.select_related("evento", "evento__cliente")
        .prefetch_related("pagamentos")
        .order_by("-evento__data_inicio", "evento__numero", "descricao")
    )

    custos_query = filtrar_por_id(custos_query, "evento_id", filtros.get("evento"))

    if filtros.get("categoria"):
        custos_query = custos_query.filter(categoria=filtros["categoria"])

    busca = filtros.get("busca", "").strip()
    if busca:
        custos_query = custos_query.filter(
            Q(evento__numero__icontains=busca)
            | Q(evento__nome_evento__icontains=busca)
            | Q(descricao__icontains=busca)
        )

    custos_query = filtrar_situacao_custos_extras(custos_query, filtros.get("situacao"))

    return list(custos_query)


def queryset_custos_extras_pagaveis(incluir_id=None):
    custos_query = (
        EventoCustoExtra.objects.select_related("evento", "evento__cliente")
        .prefetch_related("pagamentos")
        .order_by("-evento__data_inicio", "evento__numero", "descricao")
    )
    custos_query = anotar_saldo_custos_extras(custos_query)

    filtro = Q(_saldo_a_pagar__gt=Decimal("0.00"))
    if incluir_id:
        filtro |= Q(pk=incluir_id)

    return custos_query.filter(filtro)


def obter_custo_extra_inicial(custo_id, custos):
    if not custo_id:
        return None

    for custo in custos:
        if str(custo.id) == str(custo_id) and custo.saldo_a_pagar > Decimal("0.00"):
            return custo

    try:
        return (
            queryset_custos_extras_pagaveis()
            .get(pk=custo_id)
        )
    except (EventoCustoExtra.DoesNotExist, ValueError, TypeError):
        return None


def listar_pagamentos_recentes_custos_extras():
    return (
        PagamentoEventoCustoExtra.objects.select_related(
            "custo_extra",
            "custo_extra__evento",
        )
        .order_by("-data_pagamento", "-id")[:20]
    )


def listar_eventos_com_custos_extras():
    return listar_eventos_filtro_com_custos_extras()


def total_contas_pendentes_custos_extras(custos):
    return quantizar_moeda(
        sum((custo.saldo_a_pagar for custo in custos), Decimal("0.00"))
    )


def total_em_aberto_custos_extras(custos):
    return total_contas_pendentes_custos_extras(custos)


def listar_parcelas_fcf(filtros):
    parcelas_query = (
        ParcelaDivida.objects.select_related("divida", "divida__credor_cadastro")
        .prefetch_related("pagamentos")
        .order_by(
            "data_vencimento_atual",
            "divida__credor_cadastro__nome",
            "divida__credor",
            "numero_parcela",
        )
    )

    credor = valor_filtro_credor(filtros)
    if credor:
        parcelas_query = filtrar_por_credor_divida(
            parcelas_query,
            credor,
            id_estrito=filtro_credor_usa_id_canonico(filtros),
        )

    if filtros.get("tipo"):
        parcelas_query = parcelas_query.filter(divida__tipo=filtros["tipo"])

    busca = filtros.get("busca", "").strip()
    if busca:
        parcelas_query = parcelas_query.filter(
            Q(divida__credor_cadastro__nome__icontains=busca)
            | Q(divida__credor__icontains=busca)
            | Q(divida__descricao__icontains=busca)
        )

    parcelas_query = filtrar_situacao_parcelas(parcelas_query, filtros.get("situacao"))

    return list(parcelas_query)


def queryset_parcelas_fcf_pagaveis(incluir_id=None, divida_id=None):
    parcelas_query = (
        ParcelaDivida.objects.select_related("divida", "divida__credor_cadastro")
        .order_by(
            "data_vencimento_atual",
            "divida__credor_cadastro__nome",
            "divida__credor",
            "numero_parcela",
        )
    )

    if divida_id:
        parcelas_query = parcelas_query.filter(divida_id=divida_id)

    parcelas_query = anotar_total_devido_parcelas(parcelas_query)
    filtro = filtro_parcela_disponivel_para_pagamento()

    if incluir_id:
        filtro |= Q(pk=incluir_id)

    return parcelas_query.filter(filtro)


def queryset_dividas_fcf_pagaveis(incluir_id=None):
    parcelas_pagaveis = queryset_parcelas_fcf_pagaveis().values("divida_id")
    dividas_query = (
        DividaFinanceira.objects
        .select_related("credor_cadastro", "evento", "evento__orcamento")
        .order_by("credor_cadastro__nome", "credor", "descricao")
    )

    filtro = Q(pk__in=parcelas_pagaveis)
    if incluir_id:
        filtro |= Q(pk=incluir_id)

    return dividas_query.filter(filtro).distinct()


def listar_pagamentos_recentes_fcf():
    return (
        PagamentoParcelaDivida.objects.select_related("parcela", "parcela__divida")
        .order_by("-data_pagamento", "-id")[:20]
    )


def listar_credores_fcf():
    return listar_credores_fcf_filtro()


def listar_credores_cadastrados_fcf():
    return listar_credores_cadastrados_fcf_filtro()


def normalizar_filtro_credor_fcf(filtros):
    credor = valor_filtro_credor(filtros)
    filtros["credor"] = credor
    if filtro_credor_usa_id_canonico(filtros):
        filtros["creditorId"] = credor
        filtros["credor_id"] = credor
    else:
        filtros["creditorId"] = ""
        filtros["credor_id"] = ""
    return filtros


def listar_tipos_divida_fcf():
    return listar_tipos_divida_fcf_filtro()


def total_contas_pendentes_parcelas(parcelas):
    return quantizar_moeda(
        sum((parcela.valor_pendente_pagamento for parcela in parcelas), Decimal("0.00"))
    )


def total_em_aberto_parcelas(parcelas):
    return total_contas_pendentes_parcelas(parcelas)


def filtrar_situacao_custos_servico(queryset, situacao):
    situacao = normalizar_situacao_liquidacao(situacao)

    if situacao not in {SITUACAO_CONTAS_PENDENTES, SITUACAO_QUITADO}:
        return queryset

    queryset = anotar_saldo_custos_servico(queryset)

    if situacao == SITUACAO_CONTAS_PENDENTES:
        return queryset.filter(_saldo_geral__gt=Decimal("0.00"))

    return queryset.filter(_saldo_geral__lte=Decimal("0.00"))


def anotar_saldo_custos_servico(queryset):
    return queryset.annotate(
        _pago_diarias=Sum(
            "pagamentos__valor_pagamento",
            filter=Q(pagamentos__tipo=TIPO_CUSTO_DIARIAS),
            default=Decimal("0.00"),
        ),
        _pago_alimentacao=Sum(
            "pagamentos__valor_pagamento",
            filter=Q(pagamentos__tipo=TIPO_CUSTO_ALIMENTACAO),
            default=Decimal("0.00"),
        ),
        _pago_transporte=Sum(
            "pagamentos__valor_pagamento",
            filter=Q(pagamentos__tipo=TIPO_CUSTO_TRANSPORTE),
            default=Decimal("0.00"),
        ),
    ).annotate(
        _saldo_diarias=Case(
            When(diarias_quitadas=True, then=_zero_moeda()),
            default=ExpressionWrapper(
                F("valor_diarias") - F("_pago_diarias"),
                output_field=_campo_moeda(),
            ),
            output_field=_campo_moeda(),
        ),
        _saldo_alimentacao=Case(
            When(alimentacao_quitada=True, then=_zero_moeda()),
            default=ExpressionWrapper(
                F("valor_alimentacao") - F("_pago_alimentacao"),
                output_field=_campo_moeda(),
            ),
            output_field=_campo_moeda(),
        ),
        _saldo_transporte=Case(
            When(transporte_quitado=True, then=_zero_moeda()),
            default=ExpressionWrapper(
                F("valor_transporte") - F("_pago_transporte"),
                output_field=_campo_moeda(),
            ),
            output_field=_campo_moeda(),
        ),
    ).annotate(
        _saldo_geral=ExpressionWrapper(
            F("_saldo_diarias") + F("_saldo_alimentacao") + F("_saldo_transporte"),
            output_field=_campo_moeda(),
        )
    )


def filtrar_situacao_custos_extras(queryset, situacao):
    situacao = normalizar_situacao_liquidacao(situacao)

    if situacao not in {SITUACAO_CONTAS_PENDENTES, SITUACAO_QUITADO}:
        return queryset

    queryset = anotar_saldo_custos_extras(queryset)

    if situacao == SITUACAO_CONTAS_PENDENTES:
        return queryset.filter(_saldo_a_pagar__gt=Decimal("0.00"))

    return queryset.filter(_saldo_a_pagar__lte=Decimal("0.00"))


def anotar_saldo_custos_extras(queryset):
    return queryset.annotate(
        _total_pago=Sum(
            "pagamentos__valor_pagamento",
            default=Decimal("0.00"),
        ),
    ).annotate(
        _saldo_a_pagar=Case(
            When(quitado=True, then=_zero_moeda()),
            default=ExpressionWrapper(
                F("valor_previsto") - F("_total_pago"),
                output_field=_campo_moeda(),
            ),
            output_field=_campo_moeda(),
        )
    )


def filtrar_situacao_parcelas(queryset, situacao):
    situacao = normalizar_situacao_liquidacao(situacao)

    if situacao not in {SITUACAO_CONTAS_PENDENTES, SITUACAO_QUITADO}:
        return queryset

    queryset = anotar_total_devido_parcelas(queryset)

    if situacao == SITUACAO_CONTAS_PENDENTES:
        return queryset.filter(filtro_parcela_disponivel_para_pagamento())

    return queryset.filter(
        Q(status__in=STATUS_PARCELAS_FINAIS)
        | Q(baixado_manualmente=True)
        | Q(_valor_total_devido__lte=F("valor_pago"))
    )


def anotar_total_devido_parcelas(queryset):
    return queryset.annotate(
        _valor_total_devido=ExpressionWrapper(
            F("valor_principal")
            + F("valor_juros")
            + F("valor_multa")
            - F("valor_desconto"),
            output_field=_campo_moeda(),
        )
    )


def filtro_parcela_disponivel_para_pagamento():
    return (
        ~Q(status__in=STATUS_PARCELAS_FINAIS)
        & Q(baixado_manualmente=False)
        & Q(_valor_total_devido__gt=F("valor_pago"))
    )


def filtrar_parcelas_disponiveis_para_pagamento(queryset):
    return anotar_total_devido_parcelas(queryset).filter(
        filtro_parcela_disponivel_para_pagamento()
    )


def filtrar_por_id(queryset, campo, valor):
    if not valor:
        return queryset

    try:
        valor_id = int(valor)
    except (TypeError, ValueError):
        return queryset.none()

    return queryset.filter(**{campo: valor_id})
