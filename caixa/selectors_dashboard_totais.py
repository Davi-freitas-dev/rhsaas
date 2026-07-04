from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .constants_eventos import STATUS_EVENTOS_ABERTOS
from .constants_financeiros import TIPO_FLUXO_ENTRADA, TIPO_FLUXO_SAIDA
from .models import Evento
from .utils_financeiros import decimal_zero, quantizar_moeda


def calcular_totais_basicos_dashboard(receitas, despesas, custos_fixos, custos_evento, custos_extras):
    totais_receitas = receitas.aggregate(
        receita_prevista=Sum("valor_previsto"),
        receita_recebida=Sum("valor_recebido"),
    )
    receita_prevista = decimal_zero(totais_receitas["receita_prevista"])
    receita_recebida = decimal_zero(totais_receitas["receita_recebida"])

    receitas_por_evento_qs = (
        receitas
        .values("evento_id")
        .annotate(total_receita_evento=Sum("valor_previsto"))
    )
    receitas_por_evento = {
        item["evento_id"]: decimal_zero(item["total_receita_evento"])
        for item in receitas_por_evento_qs
    }

    receitas_recebidas_por_evento_qs = (
        receitas
        .values("evento_id")
        .annotate(total_recebido_evento=Sum("valor_recebido"))
    )
    receitas_recebidas_por_evento = {
        item["evento_id"]: decimal_zero(item["total_recebido_evento"])
        for item in receitas_recebidas_por_evento_qs
    }

    totais_despesas = despesas.aggregate(
        despesa_prevista=Sum("valor_previsto"),
        despesa_paga=Sum("valor_pago"),
    )
    despesa_prevista = decimal_zero(totais_despesas["despesa_prevista"])
    despesa_paga = decimal_zero(totais_despesas["despesa_paga"])
    despesas_pessoal_previstas = decimal_zero(
        despesas.filter(categoria="mao_obra").aggregate(
            total=Sum("valor_previsto"),
        )["total"]
    )

    despesas_pagas_por_evento_qs = (
        despesas
        .values("evento_id")
        .annotate(total_pago_evento=Sum("valor_pago"))
    )
    despesas_pagas_por_evento = {
        item["evento_id"]: decimal_zero(item["total_pago_evento"])
        for item in despesas_pagas_por_evento_qs
    }

    totais_custos_fixos = custos_fixos.aggregate(
        total_custo_fixo_previsto=Sum("valor_previsto"),
        total_custo_fixo_pago=Sum("valor_pago"),
    )
    total_custo_fixo_previsto = decimal_zero(totais_custos_fixos["total_custo_fixo_previsto"])
    total_custo_fixo_pago = decimal_zero(totais_custos_fixos["total_custo_fixo_pago"])

    totais_custos = custos_evento.aggregate(
        total_diarias=Sum("valor_diarias"),
        total_alimentacao=Sum("valor_alimentacao"),
        total_transporte=Sum("valor_transporte"),
    )
    total_diarias = decimal_zero(totais_custos["total_diarias"])
    total_alimentacao = decimal_zero(totais_custos["total_alimentacao"])
    total_transporte = decimal_zero(totais_custos["total_transporte"])

    totais_custos_extras = custos_extras.aggregate(
        total_custos_extras=Sum("valor_previsto"),
    )

    return {
        "receita_prevista": receita_prevista,
        "receita_recebida": receita_recebida,
        "receitas_por_evento": receitas_por_evento,
        "receitas_recebidas_por_evento": receitas_recebidas_por_evento,
        "despesa_prevista": despesa_prevista,
        "despesa_paga": despesa_paga,
        "despesas_pessoal_previstas": despesas_pessoal_previstas,
        "despesas_pagas_por_evento": despesas_pagas_por_evento,
        "total_custo_fixo_previsto": total_custo_fixo_previsto,
        "total_custo_fixo_pago": total_custo_fixo_pago,
        "total_diarias": total_diarias,
        "total_alimentacao": total_alimentacao,
        "total_transporte": total_transporte,
        "total_custos_extras": decimal_zero(totais_custos_extras["total_custos_extras"]),
    }


def calcular_totais_financeiros_dashboard(
    filtros_dashboard,
    receitas,
    despesas,
    custos_fixos,
    investimentos,
    parcelas_divida,
    totais_basicos,
    financiamentos=None,
):
    receita_prevista = totais_basicos["receita_prevista"]
    receita_recebida = totais_basicos["receita_recebida"]
    despesa_prevista = totais_basicos["despesa_prevista"]
    despesa_paga = totais_basicos["despesa_paga"]
    total_custo_fixo_previsto = totais_basicos["total_custo_fixo_previsto"]
    total_custo_fixo_pago = totais_basicos["total_custo_fixo_pago"]
    total_diarias = totais_basicos["total_diarias"]
    total_alimentacao = totais_basicos["total_alimentacao"]
    total_transporte = totais_basicos["total_transporte"]
    total_custos_extras = totais_basicos["total_custos_extras"]

    data_inicial = filtros_dashboard["data_inicial"]
    data_final = filtros_dashboard["data_final"]
    evento_id = filtros_dashboard["evento_id"]
    cliente_id = filtros_dashboard["cliente_id"]

    eventos_base = Evento.objects.select_related("cliente").all()

    if data_inicial:
        eventos_base = eventos_base.filter(data_inicio__gte=data_inicial)

    if data_final:
        eventos_base = eventos_base.filter(data_inicio__lte=data_final)

    if evento_id:
        eventos_base = eventos_base.filter(id=evento_id)

    if cliente_id:
        eventos_base = eventos_base.filter(cliente_id=cliente_id)

    totais_eventos = eventos_base.aggregate(
        total_eventos=Count("id"),
        eventos_abertos=Count(
            "id",
            filter=Q(status__in=STATUS_EVENTOS_ABERTOS),
        ),
    )

    contas_a_receber = quantizar_moeda(
        sum((receita.saldo_a_receber for receita in receitas), Decimal("0.00"))
    )
    despesas_a_pagar = quantizar_moeda(
        sum((despesa.saldo_a_pagar for despesa in despesas), Decimal("0.00"))
    )
    custos_fixos_a_pagar = quantizar_moeda(
        sum(
            (custo_fixo.valor_pendente_pagamento for custo_fixo in custos_fixos),
            Decimal("0.00"),
        )
    )
    contas_a_pagar = quantizar_moeda(
        despesas_a_pagar + custos_fixos_a_pagar
    )

    totais_impostos = despesas.filter(categoria="imposto").aggregate(
        total_imposto_previsto=Sum("valor_previsto"),
        total_imposto_pago=Sum("valor_pago"),
    )
    total_imposto_previsto = decimal_zero(totais_impostos["total_imposto_previsto"])
    total_imposto_pago = decimal_zero(totais_impostos["total_imposto_pago"])

    total_pagar_operacional = quantizar_moeda(
        (despesa_prevista - total_imposto_previsto)
        + total_custo_fixo_previsto
    )
    total_pago_operacional = quantizar_moeda(
        (despesa_paga - total_imposto_pago)
        + total_custo_fixo_pago
    )
    resultado_operacional_previsto = quantizar_moeda(
        receita_prevista
        - total_pagar_operacional
        - total_imposto_previsto
    )
    resultado_operacional_realizado = quantizar_moeda(
        receita_recebida
        - total_pago_operacional
        - total_imposto_pago
    )
    custo_variavel = quantizar_moeda(despesa_prevista)
    margem_contribuicao = quantizar_moeda(receita_prevista - custo_variavel)
    margem_contribuicao_percentual = (
        ((margem_contribuicao / receita_prevista) * Decimal("100")).quantize(
            Decimal("0.01")
        )
        if receita_prevista > Decimal("0.00")
        else Decimal("0.00")
    )
    lucro_operacional_ebit = quantizar_moeda(
        margem_contribuicao - total_custo_fixo_previsto
    )

    totais_investimentos = investimentos.aggregate(
        total_previsto_entrada_fci=Sum("valor_previsto", filter=Q(tipo_fluxo="entrada")),
        total_previsto_saida_fci=Sum("valor_previsto", filter=Q(tipo_fluxo="saida")),
        total_realizado_entrada_fci=Sum("valor_realizado", filter=Q(tipo_fluxo="entrada")),
        total_realizado_saida_fci=Sum("valor_realizado", filter=Q(tipo_fluxo="saida")),
    )
    total_previsto_entrada_fci = decimal_zero(totais_investimentos["total_previsto_entrada_fci"])
    total_previsto_saida_fci = decimal_zero(totais_investimentos["total_previsto_saida_fci"])
    total_realizado_entrada_fci = decimal_zero(totais_investimentos["total_realizado_entrada_fci"])
    total_realizado_saida_fci = decimal_zero(totais_investimentos["total_realizado_saida_fci"])
    resultado_investimentos_previsto = quantizar_moeda(
        total_previsto_entrada_fci - total_previsto_saida_fci
    )
    resultado_investimentos_realizado = quantizar_moeda(
        total_realizado_entrada_fci - total_realizado_saida_fci
    )

    lista_parcelas_divida = list(
        parcelas_divida.order_by("data_vencimento_atual", "numero_parcela", "id")
    )
    lista_financiamentos = []

    if financiamentos is not None:
        lista_financiamentos = list(
            financiamentos.order_by("data_prevista", "descricao", "id")
        )

    total_previsto_entrada_fcf = Decimal("0.00")
    total_realizado_entrada_fcf = Decimal("0.00")
    total_previsto_saida_fcf = Decimal("0.00")
    total_realizado_saida_fcf = Decimal("0.00")
    contas_pendentes_fcf = Decimal("0.00")
    contas_vencidas_fcf = Decimal("0.00")
    hoje = timezone.localdate()

    for financiamento in lista_financiamentos:
        if financiamento.tipo_fluxo == TIPO_FLUXO_ENTRADA:
            total_previsto_entrada_fcf += financiamento.valor_previsto
            total_realizado_entrada_fcf += financiamento.valor_realizado
            continue

        total_previsto_saida_fcf += financiamento.valor_previsto
        total_realizado_saida_fcf += financiamento.valor_realizado
        valor_pendente_financiamento = financiamento.valor_pendente_realizacao
        contas_pendentes_fcf += valor_pendente_financiamento

        if financiamento.data_prevista < hoje and valor_pendente_financiamento > Decimal("0.00"):
            contas_vencidas_fcf += valor_pendente_financiamento

    for parcela in lista_parcelas_divida:
        valor_pendente_parcela = parcela.valor_pendente_pagamento
        total_previsto_saida_fcf += parcela.valor_total_devido
        total_realizado_saida_fcf += parcela.valor_pago
        contas_pendentes_fcf += valor_pendente_parcela

        if parcela.data_vencimento_atual < hoje and valor_pendente_parcela > Decimal("0.00"):
            contas_vencidas_fcf += valor_pendente_parcela

    resultado_financiamentos_previsto = quantizar_moeda(
        total_previsto_entrada_fcf - total_previsto_saida_fcf
    )
    resultado_financiamentos_realizado = quantizar_moeda(
        total_realizado_entrada_fcf - total_realizado_saida_fcf
    )

    total_previsto_entrada_fcf = quantizar_moeda(total_previsto_entrada_fcf)
    total_previsto_saida_fcf = quantizar_moeda(total_previsto_saida_fcf)
    total_realizado_entrada_fcf = quantizar_moeda(total_realizado_entrada_fcf)
    total_realizado_saida_fcf = quantizar_moeda(total_realizado_saida_fcf)
    contas_pendentes_fcf = quantizar_moeda(contas_pendentes_fcf)
    contas_vencidas_fcf = quantizar_moeda(contas_vencidas_fcf)

    resultado_consolidado_previsto = quantizar_moeda(
        resultado_operacional_previsto
        + resultado_investimentos_previsto
        + resultado_financiamentos_previsto
    )
    resultado_consolidado_realizado = quantizar_moeda(
        resultado_operacional_realizado
        + resultado_investimentos_realizado
        + resultado_financiamentos_realizado
    )

    total_custos_operacionais = quantizar_moeda(
        total_diarias
        + total_alimentacao
        + total_transporte
        + total_custos_extras
    )

    eventos_operacionais_ativos = totais_eventos["eventos_abertos"] or 0

    return {
        "total_eventos": totais_eventos["total_eventos"] or 0,
        "eventos_operacionais_ativos": eventos_operacionais_ativos,
        "eventos_abertos": eventos_operacionais_ativos,
        "contratos_ativos": eventos_operacionais_ativos,
        "contas_a_receber": contas_a_receber,
        "despesas_a_pagar": despesas_a_pagar,
        "custos_fixos_a_pagar": custos_fixos_a_pagar,
        "contas_a_pagar": contas_a_pagar,
        "contas_pendentes": contas_a_pagar,
        "contas_a_pagar_periodo": contas_pendentes_fcf,
        "contas_pendentes_periodo": contas_pendentes_fcf,
        "total_imposto_previsto": total_imposto_previsto,
        "total_imposto_pago": total_imposto_pago,
        "total_pagar_operacional": total_pagar_operacional,
        "total_pago_operacional": total_pago_operacional,
        "custo_variavel": custo_variavel,
        "margem_contribuicao": margem_contribuicao,
        "margem_contribuicao_percentual": margem_contribuicao_percentual,
        "lucro_operacional_ebit": lucro_operacional_ebit,
        "variableCostAmount": custo_variavel,
        "contributionMarginAmount": margem_contribuicao,
        "contributionMarginPercent": margem_contribuicao_percentual,
        "operatingProfitEbitAmount": lucro_operacional_ebit,
        "resultado_operacional_previsto": resultado_operacional_previsto,
        "resultado_operacional_realizado": resultado_operacional_realizado,
        "resultado_financeiro_operacional_projetado": resultado_operacional_previsto,
        "resultado_financeiro_operacional_realizado": resultado_operacional_realizado,
        "total_previsto_entrada_fci": total_previsto_entrada_fci,
        "total_previsto_saida_fci": total_previsto_saida_fci,
        "total_realizado_entrada_fci": total_realizado_entrada_fci,
        "total_realizado_saida_fci": total_realizado_saida_fci,
        "resultado_investimentos_previsto": resultado_investimentos_previsto,
        "resultado_investimentos_realizado": resultado_investimentos_realizado,
        "resultado_financeiro_fci_projetado": resultado_investimentos_previsto,
        "resultado_financeiro_fci_realizado": resultado_investimentos_realizado,
        "total_previsto_entrada_fcf": total_previsto_entrada_fcf,
        "total_previsto_saida_fcf": total_previsto_saida_fcf,
        "total_realizado_entrada_fcf": total_realizado_entrada_fcf,
        "total_realizado_saida_fcf": total_realizado_saida_fcf,
        "resultado_financiamentos_previsto": resultado_financiamentos_previsto,
        "resultado_financiamentos_realizado": resultado_financiamentos_realizado,
        "resultado_financeiro_fcf_projetado": resultado_financiamentos_previsto,
        "resultado_financeiro_fcf_realizado": resultado_financiamentos_realizado,
        "total_contas_pendentes_fcf": contas_pendentes_fcf,
        "total_em_aberto_fcf": contas_pendentes_fcf,
        "contas_pendentes_fcf": contas_pendentes_fcf,
        "total_contas_vencidas_fcf": contas_vencidas_fcf,
        "total_vencido_fcf": contas_vencidas_fcf,
        "contas_vencidas_fcf": contas_vencidas_fcf,
        "resultado_consolidado_previsto": resultado_consolidado_previsto,
        "resultado_consolidado_realizado": resultado_consolidado_realizado,
        "resultado_financeiro_consolidado_projetado": resultado_consolidado_previsto,
        "resultado_financeiro_consolidado_realizado": resultado_consolidado_realizado,
        "total_custos_operacionais": total_custos_operacionais,
        "total_entrada_fco_prevista": quantizar_moeda(receita_prevista),
        "total_saida_fco_prevista": quantizar_moeda(
            despesa_prevista + total_custo_fixo_previsto
        ),
        "total_entrada_fco_realizada": quantizar_moeda(receita_recebida),
        "total_saida_fco_realizada": quantizar_moeda(
            despesa_paga + total_custo_fixo_pago
        ),
        "lista_parcelas_divida": lista_parcelas_divida,
        "lista_financiamentos": lista_financiamentos,
        "hoje": hoje,
    }
