from django.db.models import Q
from django.utils import timezone

from .constants_dividas import (
    STATUS_DIVIDAS,
    STATUS_PARCELA_CANCELADA,
    STATUS_PARCELA_PAGA,
    STATUS_PARCELAS,
)
from .constants_eventos import STATUS_EVENTOS_ABERTOS
from .constants_financeiros import STATUS_CANCELADO, STATUS_PAGO, STATUS_REALIZADO
from .models import DespesaOperacional, ReceitaOperacional
from .models_custo_fixo import CustoFixo
from .models_custos_extras import EventoCustoExtra
from .models_dividas import ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .models_servico import EventoCustoServico
from .utils_contratos import (
    montar_filtro_evento_ou_orcamento_por_contrato_visual,
    montar_filtro_evento_por_contrato_visual,
    resolver_codigo_contrato_visual_parametros,
)
from .utils_periodos import resolver_periodo_rapido_com_sessao


STATUS_EVENTO_MAP = {
    "pendente": "planejado",
    "parcial": "confirmado",
    "recebido": "concluido",
    "pago": "concluido",
    "vencido": "em_andamento",
    "cancelado": "cancelado",
    "planejado": "planejado",
    "realizado": "concluido",
}


def resolver_filtros_dashboard(params, session):
    contrato_codigo = resolver_codigo_contrato_visual_parametros(params)
    filtros = resolver_periodo_rapido_com_sessao(
        {
            "data_inicial": params.get("data_inicial", "").strip(),
            "data_final": params.get("data_final", "").strip(),
            "evento_id": params.get("evento", "").strip(),
            "cliente_id": params.get("cliente", "").strip(),
            "contrato_codigo": contrato_codigo,
            "status": params.get("status", "").strip(),
            "periodo_rapido": params.get("periodo_rapido", "").strip(),
        },
        session,
        "dashboard_periodo_rapido",
    )

    return {
        "data_inicial": filtros["data_inicial"],
        "data_final": filtros["data_final"],
        "evento_id": filtros["evento_id"],
        "cliente_id": filtros["cliente_id"],
        "contrato_codigo": filtros["contrato_codigo"],
        "status": filtros["status"],
        "periodo_rapido": filtros["periodo_rapido"],
    }


def querysets_dashboard_filtrados(filtros):
    qs = {
        "receitas": ReceitaOperacional.objects.select_related(
            "cliente",
            "evento",
            "evento__orcamento",
        ).all(),
        "despesas": DespesaOperacional.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
            "origem_custo_extra",
        ).prefetch_related("evento__custos_servicos").all(),
        "custos_fixos": CustoFixo.objects.filter(ativo=True),
        "investimentos": Investimento.objects.select_related(
            "evento",
            "evento__orcamento",
            "evento__cliente",
        ).filter(ativo=True),
        "parcelas_divida": ParcelaDivida.objects.select_related(
            "divida",
            "divida__evento",
            "divida__evento__orcamento",
            "divida__evento__cliente",
        ).all(),
        "financiamentos": FinanciamentoMovimentacao.objects.select_related(
            "evento",
            "evento__orcamento",
            "evento__cliente",
        ).filter(ativo=True),
        "custos_evento": EventoCustoServico.objects.select_related(
            "evento",
            "evento__orcamento",
            "servico",
        ).prefetch_related("pagamentos"),
        "custos_extras": EventoCustoExtra.objects.select_related(
            "evento",
            "evento__orcamento",
        ).prefetch_related("pagamentos"),
    }

    data_inicial = filtros["data_inicial"]
    data_final = filtros["data_final"]
    evento_id = filtros["evento_id"]
    cliente_id = filtros["cliente_id"]
    contrato_codigo = filtros.get("contrato_codigo", "")
    status = filtros["status"]
    periodo_rapido = filtros["periodo_rapido"]

    if periodo_rapido == "vencidos":
        qs = _filtrar_querysets_vencidos(qs)

    if data_inicial:
        qs["receitas"] = qs["receitas"].filter(data_vencimento__gte=data_inicial)
        qs["despesas"] = qs["despesas"].filter(data_vencimento__gte=data_inicial)
        qs["custos_fixos"] = qs["custos_fixos"].filter(data_vencimento__gte=data_inicial)
        qs["investimentos"] = qs["investimentos"].filter(data_prevista__gte=data_inicial)
        qs["parcelas_divida"] = qs["parcelas_divida"].filter(data_vencimento_atual__gte=data_inicial)
        qs["financiamentos"] = qs["financiamentos"].filter(data_prevista__gte=data_inicial)
        qs["custos_evento"] = qs["custos_evento"].filter(evento__data_inicio__gte=data_inicial)
        qs["custos_extras"] = qs["custos_extras"].filter(evento__data_inicio__gte=data_inicial)

    if data_final:
        qs["receitas"] = qs["receitas"].filter(data_vencimento__lte=data_final)
        qs["despesas"] = qs["despesas"].filter(data_vencimento__lte=data_final)
        qs["custos_fixos"] = qs["custos_fixos"].filter(data_vencimento__lte=data_final)
        qs["investimentos"] = qs["investimentos"].filter(data_prevista__lte=data_final)
        qs["parcelas_divida"] = qs["parcelas_divida"].filter(data_vencimento_atual__lte=data_final)
        qs["financiamentos"] = qs["financiamentos"].filter(data_prevista__lte=data_final)
        qs["custos_evento"] = qs["custos_evento"].filter(evento__data_inicio__lte=data_final)
        qs["custos_extras"] = qs["custos_extras"].filter(evento__data_inicio__lte=data_final)

    if evento_id:
        qs["receitas"] = qs["receitas"].filter(evento_id=evento_id)
        qs["despesas"] = qs["despesas"].filter(evento_id=evento_id)
        qs["custos_evento"] = qs["custos_evento"].filter(evento_id=evento_id)
        qs["custos_extras"] = qs["custos_extras"].filter(evento_id=evento_id)
        qs["investimentos"] = qs["investimentos"].filter(evento_id=evento_id)
        qs["financiamentos"] = qs["financiamentos"].filter(evento_id=evento_id)
        qs["parcelas_divida"] = qs["parcelas_divida"].filter(divida__evento_id=evento_id)

    if cliente_id:
        qs["receitas"] = qs["receitas"].filter(cliente_id=cliente_id)
        qs["despesas"] = qs["despesas"].filter(evento__cliente_id=cliente_id)
        qs["custos_evento"] = qs["custos_evento"].filter(evento__cliente_id=cliente_id)
        qs["custos_extras"] = qs["custos_extras"].filter(evento__cliente_id=cliente_id)
        qs["investimentos"] = qs["investimentos"].filter(
            Q(evento__cliente_id=cliente_id)
        )
        qs["financiamentos"] = qs["financiamentos"].filter(
            Q(evento__cliente_id=cliente_id)
        )
        qs["parcelas_divida"] = qs["parcelas_divida"].filter(
            Q(divida__evento__cliente_id=cliente_id)
        )

    if contrato_codigo:
        filtro_evento = montar_filtro_evento_por_contrato_visual(
            "evento__",
            contrato_codigo,
        )
        qs["receitas"] = qs["receitas"].filter(filtro_evento)
        qs["despesas"] = qs["despesas"].filter(filtro_evento)
        qs["custos_evento"] = qs["custos_evento"].filter(filtro_evento)
        qs["custos_extras"] = qs["custos_extras"].filter(filtro_evento)

        filtro_contrato_visual = montar_filtro_evento_ou_orcamento_por_contrato_visual(
            "evento__",
            contrato_codigo,
        )
        qs["investimentos"] = qs["investimentos"].filter(filtro_contrato_visual)
        qs["financiamentos"] = qs["financiamentos"].filter(filtro_contrato_visual)
        qs["parcelas_divida"] = qs["parcelas_divida"].filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "divida__evento__",
                contrato_codigo,
            )
        )

    if evento_id or cliente_id or contrato_codigo:
        qs["custos_fixos"] = qs["custos_fixos"].none()

    if status == "vencido":
        qs = _filtrar_querysets_vencidos(qs)
    elif status:
        qs["receitas"] = qs["receitas"].filter(status=status)
        qs["despesas"] = qs["despesas"].filter(status=status)
        qs["custos_fixos"] = qs["custos_fixos"].filter(status=status)
        qs["investimentos"] = qs["investimentos"].filter(status=status)
        qs["financiamentos"] = qs["financiamentos"].filter(status=status)

        if status in STATUS_PARCELAS:
            qs["parcelas_divida"] = qs["parcelas_divida"].filter(status=status)
        elif status in STATUS_DIVIDAS:
            qs["parcelas_divida"] = qs["parcelas_divida"].filter(divida__status=status)
        else:
            qs["parcelas_divida"] = qs["parcelas_divida"].none()

        status_evento = STATUS_EVENTO_MAP.get(status)

        if status_evento:
            qs["custos_evento"] = qs["custos_evento"].filter(evento__status=status_evento)
            qs["custos_extras"] = qs["custos_extras"].filter(evento__status=status_evento)
        else:
            qs["custos_evento"] = qs["custos_evento"].none()
            qs["custos_extras"] = qs["custos_extras"].none()

    return qs


def _filtrar_querysets_vencidos(qs):
    hoje = timezone.localdate()
    qs["receitas"] = qs["receitas"].filter(
        data_vencimento__lt=hoje,
    ).exclude(status__in=["recebido", "cancelado"])
    qs["despesas"] = qs["despesas"].filter(
        data_vencimento__lt=hoje,
    ).exclude(status__in=[STATUS_PAGO, STATUS_CANCELADO])
    qs["custos_fixos"] = qs["custos_fixos"].filter(
        data_vencimento__lt=hoje,
    ).exclude(status__in=[STATUS_PAGO, STATUS_CANCELADO])
    qs["investimentos"] = qs["investimentos"].filter(
        data_prevista__lt=hoje,
    ).exclude(status__in=[STATUS_REALIZADO, STATUS_CANCELADO])
    qs["parcelas_divida"] = qs["parcelas_divida"].filter(
        data_vencimento_atual__lt=hoje,
    ).exclude(status__in=[STATUS_PARCELA_PAGA, STATUS_PARCELA_CANCELADA])
    qs["financiamentos"] = qs["financiamentos"].filter(
        data_prevista__lt=hoje,
        tipo_fluxo="saida",
    ).exclude(status__in=[STATUS_REALIZADO, STATUS_CANCELADO])
    qs["custos_evento"] = qs["custos_evento"].filter(
        evento__data_inicio__lt=hoje,
        evento__status__in=STATUS_EVENTOS_ABERTOS,
    )
    qs["custos_extras"] = qs["custos_extras"].filter(
        evento__data_inicio__lt=hoje,
        evento__status__in=STATUS_EVENTOS_ABERTOS,
    )
    return qs
