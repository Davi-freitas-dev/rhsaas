from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.utils import timezone

from .constants_eventos import STATUS_EVENTOS_ABERTOS
from .constants_financeiros import STATUS_CANCELADO, STATUS_PAGO
from .models import Cliente, DespesaOperacional, Evento, Orcamento, ReceitaOperacional
from .models_custos_extras import EventoCustoExtra
from .selectors_opcoes_filtros import listar_eventos_filtro_recentes
from .utils_datas import obter_periodo_rapido
from .utils_financeiros import decimal_zero, quantizar_moeda
from .utils_request import normalizar_data_iso


def filtrar_clientes(busca="", tipo_pessoa="", ativo=""):
    clientes = Cliente.objects.all()

    if busca:
        clientes = clientes.filter(
            Q(nome_razao_social__icontains=busca)
            | Q(nome_fantasia__icontains=busca)
            | Q(cpf_cnpj__icontains=busca)
            | Q(email__icontains=busca)
            | Q(telefone__icontains=busca)
        )

    if tipo_pessoa:
        clientes = clientes.filter(tipo_pessoa=tipo_pessoa)

    if ativo == "sim":
        clientes = clientes.filter(ativo=True)
    elif ativo == "nao":
        clientes = clientes.filter(ativo=False)

    return clientes.order_by("nome_razao_social", "id")


def filtrar_orcamentos(busca="", status=""):
    orcamentos = Orcamento.objects.select_related("cliente", "configuracao_financeira")

    if busca:
        orcamentos = orcamentos.filter(
            Q(numero__icontains=busca)
            | Q(nome_evento__icontains=busca)
            | Q(cliente__nome_razao_social__icontains=busca)
            | Q(cliente__nome_fantasia__icontains=busca)
        )

    if status:
        orcamentos = orcamentos.filter(status=status)

    return orcamentos.order_by("-data_evento", "-id")


def totais_orcamentos(orcamentos):
    totais = orcamentos.aggregate(total_venda=Sum("total_venda"))
    return {
        "total_venda": decimal_zero(totais["total_venda"]),
    }


def status_orcamentos_para_filtro():
    return Orcamento.STATUS_CHOICES


def filtrar_eventos(
    busca="",
    status="",
    data_inicial="",
    data_final="",
    cliente_id="",
    periodo_rapido="",
):
    data_inicial = normalizar_data_iso(data_inicial)
    data_final = normalizar_data_iso(data_final)
    eventos = Evento.objects.select_related("cliente", "orcamento")

    if periodo_rapido == "vencidos":
        eventos = eventos.filter(
            data_inicio__lt=timezone.localdate(),
            status__in=STATUS_EVENTOS_ABERTOS,
        )

    if busca:
        eventos = eventos.filter(
            Q(numero__icontains=busca)
            | Q(nome_evento__icontains=busca)
            | Q(cliente__nome_razao_social__icontains=busca)
            | Q(cliente__nome_fantasia__icontains=busca)
            | Q(local__icontains=busca)
        )

    if status:
        eventos = eventos.filter(status=status)

    if cliente_id:
        eventos = eventos.filter(cliente_id=cliente_id)

    if data_inicial:
        eventos = eventos.filter(data_inicio__gte=data_inicial)

    if data_final:
        eventos = eventos.filter(data_inicio__lte=data_final)

    return eventos.order_by("-data_inicio", "-id")


def resolver_periodo_eventos_lista(filtros):
    filtros = {**filtros}
    tem_filtro_personalizado = any(
        str(filtros.get(campo) or "").strip()
        for campo in ("busca", "status", "cliente")
    )

    if filtros["periodo_rapido"] == "todos":
        if filtros["data_inicial"] or filtros["data_final"]:
            filtros["periodo_rapido"] = ""
        return filtros

    if filtros["periodo_rapido"]:
        periodo_inicial, periodo_final = obter_periodo_rapido(filtros["periodo_rapido"])
        if periodo_inicial is not None:
            if filtros["periodo_rapido"] == "vencidos" and (
                filtros["data_inicial"] or filtros["data_final"]
            ):
                if not filtros["data_final"]:
                    filtros["data_final"] = periodo_final
            else:
                filtros["data_inicial"] = periodo_inicial
                filtros["data_final"] = periodo_final
        else:
            filtros["periodo_rapido"] = ""

    if (
        not filtros["periodo_rapido"]
        and not filtros["data_inicial"]
        and not filtros["data_final"]
        and tem_filtro_personalizado
    ):
        filtros["periodo_rapido"] = "todos"

    return filtros


def totais_eventos(eventos):
    totais = eventos.aggregate(
        receita_prevista=Sum("valor_total_previsto"),
        receita_realizada=Sum("valor_total_realizado"),
        custo_previsto=Sum("custo_total_previsto"),
        custo_realizado=Sum("custo_total_realizado"),
        lucro_previsto=Sum("lucro_previsto"),
        lucro_realizado=Sum("lucro_realizado"),
    )

    return {
        "receita_prevista": decimal_zero(totais["receita_prevista"]),
        "receita_realizada": decimal_zero(totais["receita_realizada"]),
        "custo_previsto": decimal_zero(totais["custo_previsto"]),
        "custo_realizado": decimal_zero(totais["custo_realizado"]),
        "lucro_previsto": decimal_zero(totais["lucro_previsto"]),
        "lucro_realizado": decimal_zero(totais["lucro_realizado"]),
    }


def status_eventos_para_filtro():
    return Evento.STATUS_CHOICES


def filtrar_receitas(
    busca="",
    status="",
    data_inicial="",
    data_final="",
    evento_id="",
    cliente_id="",
    periodo_rapido="",
):
    data_inicial = normalizar_data_iso(data_inicial)
    data_final = normalizar_data_iso(data_final)
    receitas = ReceitaOperacional.objects.select_related("evento", "cliente")

    if periodo_rapido == "vencidos":
        receitas = receitas.filter(
            data_vencimento__lt=timezone.localdate(),
        ).exclude(status__in=["recebido", STATUS_CANCELADO])

    if busca:
        receitas = receitas.filter(
            Q(descricao__icontains=busca)
            | Q(evento__numero__icontains=busca)
            | Q(evento__nome_evento__icontains=busca)
            | Q(cliente__nome_razao_social__icontains=busca)
            | Q(cliente__nome_fantasia__icontains=busca)
        )

    if status:
        receitas = receitas.filter(status=status)

    if evento_id:
        receitas = receitas.filter(evento_id=evento_id)

    if cliente_id:
        receitas = receitas.filter(cliente_id=cliente_id)

    if data_inicial:
        receitas = receitas.filter(data_vencimento__gte=data_inicial)

    if data_final:
        receitas = receitas.filter(data_vencimento__lte=data_final)

    return receitas.order_by("data_vencimento", "id")


def totais_receitas(receitas):
    totais = receitas.aggregate(
        previsto=Sum("valor_previsto"),
        recebido=Sum("valor_recebido"),
        aberto=Sum(
            Case(
                When(
                    Q(status__in=["recebido", STATUS_CANCELADO])
                    | Q(baixado_manualmente=True),
                    then=Value(0),
                ),
                When(
                    valor_previsto__gt=F("valor_recebido"),
                    then=ExpressionWrapper(
                        F("valor_previsto") - F("valor_recebido"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    ),
                ),
                default=Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ),
    )
    previsto = decimal_zero(totais["previsto"])
    recebido = decimal_zero(totais["recebido"])
    aberto = decimal_zero(totais["aberto"])

    return {
        "total_previsto": previsto,
        "total_recebido": recebido,
        "total_contas_pendentes": quantizar_moeda(aberto),
        "total_aberto": quantizar_moeda(aberto),
    }


def status_receitas_para_filtro():
    return ReceitaOperacional.STATUS_CHOICES


def filtrar_despesas(
    busca="",
    status="",
    categoria="",
    origem="",
    data_inicial="",
    data_final="",
    evento_id="",
    cliente_id="",
    periodo_rapido="",
):
    data_inicial = normalizar_data_iso(data_inicial)
    data_final = normalizar_data_iso(data_final)
    despesas = DespesaOperacional.objects.select_related(
        "evento",
        "evento__cliente",
    ).prefetch_related("evento__custos_servicos")

    if periodo_rapido == "vencidos":
        despesas = despesas.filter(
            data_vencimento__lt=timezone.localdate(),
        ).exclude(status__in=[STATUS_PAGO, STATUS_CANCELADO])

    if busca:
        despesas = despesas.filter(
            Q(descricao__icontains=busca)
            | Q(evento__numero__icontains=busca)
            | Q(evento__nome_evento__icontains=busca)
            | Q(evento__cliente__nome_razao_social__icontains=busca)
            | Q(evento__cliente__nome_fantasia__icontains=busca)
        )

    if status:
        despesas = despesas.filter(status=status)

    if categoria:
        despesas = despesas.filter(categoria=categoria)

    if origem:
        despesas = despesas.filter(origem=origem)

    if evento_id:
        despesas = despesas.filter(evento_id=evento_id)

    if cliente_id:
        despesas = despesas.filter(evento__cliente_id=cliente_id)

    if data_inicial:
        despesas = despesas.filter(data_vencimento__gte=data_inicial)

    if data_final:
        despesas = despesas.filter(data_vencimento__lte=data_final)

    return despesas.order_by("data_vencimento", "id")


def totais_despesas(despesas):
    totais = despesas.aggregate(
        previsto=Sum("valor_previsto"),
        pago=Sum("valor_pago"),
        aberto=Sum(
            Case(
                When(
                    Q(status__in=[STATUS_PAGO, STATUS_CANCELADO])
                    | Q(baixado_manualmente=True),
                    then=Value(0),
                ),
                default=ExpressionWrapper(
                    F("valor_previsto") - F("valor_pago"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ),
    )
    previsto = decimal_zero(totais["previsto"])
    pago = decimal_zero(totais["pago"])
    aberto = decimal_zero(totais["aberto"])

    return {
        "total_previsto": previsto,
        "total_pago": pago,
        "total_contas_pendentes": quantizar_moeda(aberto),
        "total_aberto": quantizar_moeda(aberto),
    }


def categorias_despesas_para_filtro():
    return DespesaOperacional.CATEGORIA_CHOICES


def status_despesas_para_filtro():
    return DespesaOperacional.STATUS_CHOICES


def origens_despesas_para_filtro():
    return DespesaOperacional.ORIGEM_CHOICES


def listar_custos_extras_recentes(busca="", categoria="", evento_id="", data_inicial="", data_final=""):
    data_inicial = normalizar_data_iso(data_inicial)
    data_final = normalizar_data_iso(data_final)
    custos_extras = EventoCustoExtra.objects.select_related("evento", "evento__cliente")
    eventos_filtro = listar_eventos_filtro_recentes()
    evento_id_efetivo = evento_id

    if not any([busca, categoria, evento_id, data_inicial, data_final]):
        ultimo_evento = eventos_filtro.first()
        if ultimo_evento:
            evento_id_efetivo = str(ultimo_evento.id)

    if busca:
        custos_extras = custos_extras.filter(
            Q(descricao__icontains=busca)
            | Q(observacao__icontains=busca)
            | Q(evento__numero__icontains=busca)
            | Q(evento__nome_evento__icontains=busca)
            | Q(evento__cliente__nome_razao_social__icontains=busca)
            | Q(evento__cliente__nome_fantasia__icontains=busca)
        )

    if categoria:
        custos_extras = custos_extras.filter(categoria=categoria)

    if evento_id_efetivo:
        custos_extras = custos_extras.filter(evento_id=evento_id_efetivo)

    if data_inicial:
        custos_extras = custos_extras.filter(data_vencimento__gte=data_inicial)

    if data_final:
        custos_extras = custos_extras.filter(data_vencimento__lte=data_final)

    return {
        "custos_extras": custos_extras.order_by("-data_vencimento", "-id")[:50],
        "eventos_filtro": eventos_filtro,
        "evento_id_efetivo": evento_id_efetivo,
    }
