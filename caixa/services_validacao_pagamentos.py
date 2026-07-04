from decimal import Decimal

from django.db.models import Q, Sum

from .utils_financeiros import ZERO_DECIMAL, decimal_zero, quantizar_moeda


def saldo_disponivel_pagamento(valor_previsto, total_pago, pagamento_original=None):
    total_considerado = total_pago

    if pagamento_original is not None:
        total_considerado -= pagamento_original.valor_pagamento

    return quantizar_moeda(valor_previsto - total_considerado)


def validar_valor_pagamento_positivo(valor_pagamento):
    if valor_pagamento is None:
        return False

    return valor_pagamento > ZERO_DECIMAL


def saldo_caixa_disponivel(data_limite=None, pagamento_original=None):
    saldo = total_entradas_caixa(data_limite) - total_saidas_caixa(data_limite)
    saldo += valor_pagamento_original_no_periodo(pagamento_original, data_limite)
    return quantizar_moeda(saldo)


def erro_caixa_insuficiente(valor_pagamento, data_pagamento, pagamento_original=None):
    valor_pagamento = decimal_zero(valor_pagamento)

    if valor_pagamento <= ZERO_DECIMAL:
        return ""

    saldo_disponivel = saldo_caixa_disponivel(data_pagamento, pagamento_original)

    if valor_pagamento <= saldo_disponivel:
        return ""

    deficit_caixa = quantizar_moeda(valor_pagamento - saldo_disponivel)
    data_referencia = data_pagamento.strftime("%d/%m/%Y") if data_pagamento else "informada"

    return (
        "Caixa insuficiente para registrar este pagamento. "
        f"Caixa disponível até {data_referencia}: {saldo_disponivel}. "
        f"Valor solicitado: {quantizar_moeda(valor_pagamento)}. "
        f"Déficit de caixa: {deficit_caixa}."
    )


def erro_caixa_insuficiente_para_aumento(
    modelo,
    pk,
    campo_valor,
    novo_valor,
    data_pagamento,
):
    novo_valor = decimal_zero(novo_valor)
    valor_original = Decimal("0.00")

    if pk:
        try:
            valor_original = decimal_zero(
                getattr(modelo.objects.only(campo_valor).get(pk=pk), campo_valor)
            )
        except modelo.DoesNotExist:
            valor_original = Decimal("0.00")

    aumento = quantizar_moeda(novo_valor - valor_original)

    if aumento <= ZERO_DECIMAL:
        return ""

    return erro_caixa_insuficiente(aumento, data_pagamento)


def erro_caixa_insuficiente_para_pagamento(
    valor_pagamento,
    data_pagamento,
    pagamento_original=None,
):
    valor_pagamento = decimal_zero(valor_pagamento)

    if (
        pagamento_original
        and getattr(pagamento_original, "pk", None)
    ):
        try:
            original = pagamento_original.__class__.objects.get(pk=pagamento_original.pk)
        except pagamento_original.__class__.DoesNotExist:
            original = None

        if original and original.data_pagamento <= data_pagamento:
            aumento = quantizar_moeda(valor_pagamento - decimal_zero(original.valor_pagamento))

            if aumento <= ZERO_DECIMAL:
                return ""

            return erro_caixa_insuficiente(aumento, data_pagamento)

    return erro_caixa_insuficiente(valor_pagamento, data_pagamento)


def total_entradas_caixa(data_limite=None):
    from .constants_financeiros import TIPO_FLUXO_ENTRADA
    from .models import ReceitaOperacional
    from .models_fcf import FinanciamentoMovimentacao
    from .models_fci import Investimento

    total = Decimal("0.00")

    receitas = ReceitaOperacional.objects.filter(valor_recebido__gt=ZERO_DECIMAL)
    if data_limite:
        receitas = receitas.filter(
            filtro_data_efetiva("data_recebimento", "data_vencimento", data_limite)
        )
    total += somar_campo(receitas, "valor_recebido")

    investimentos_entrada = Investimento.objects.filter(
        ativo=True,
        tipo_fluxo=TIPO_FLUXO_ENTRADA,
        valor_realizado__gt=ZERO_DECIMAL,
    )
    if data_limite:
        investimentos_entrada = investimentos_entrada.filter(
            filtro_data_efetiva("data_realizacao", "data_prevista", data_limite)
        )
    total += somar_campo(investimentos_entrada, "valor_realizado")

    financiamentos_entrada = FinanciamentoMovimentacao.objects.filter(
        ativo=True,
        tipo_fluxo=TIPO_FLUXO_ENTRADA,
        valor_realizado__gt=ZERO_DECIMAL,
    )
    if data_limite:
        financiamentos_entrada = financiamentos_entrada.filter(
            filtro_data_efetiva("data_realizacao", "data_prevista", data_limite)
        )
    total += somar_campo(financiamentos_entrada, "valor_realizado")

    return quantizar_moeda(total)


def total_saidas_caixa(data_limite=None):
    total = Decimal("0.00")
    total += total_despesas_manuais_e_pagamentos_custos_servico(data_limite)
    total += total_custos_fixos_pagos(data_limite)
    total += total_investimentos_saida_realizados(data_limite)
    total += total_financiamentos_saida_realizados(data_limite)
    total += total_pagamentos_parcelas(data_limite)
    total += total_pagamentos_custos_extras(data_limite)
    total += total_pagamentos_parcelas_legado(data_limite)
    return quantizar_moeda(total)


def total_despesas_manuais_pagas(data_limite=None):
    from .models import DespesaOperacional

    despesas = (
        DespesaOperacional.objects.filter(valor_pago__gt=ZERO_DECIMAL)
        .exclude(descricao__startswith="Custo extra: ")
        .exclude(
            Q(categoria__in=["mao_obra", "alimentacao", "transporte"])
            & (Q(descricao__endswith="prevista") | Q(descricao__endswith="previsto"))
        )
    )

    if data_limite:
        despesas = despesas.filter(
            filtro_data_efetiva("data_pagamento", "data_vencimento", data_limite)
        )

    return somar_campo(despesas, "valor_pago")


def total_despesas_manuais_e_pagamentos_custos_servico(data_limite=None):
    despesas = despesas_operacionais_pagas_para_caixa(data_limite)
    despesas_manuais = [
        despesa
        for despesa in despesas
        if despesa_manual_entra_no_caixa(despesa)
    ]
    despesas_servico_legado = [
        despesa
        for despesa in despesas
        if despesa_candidata_custo_servico_legado(despesa)
    ]
    totais_registrados = totais_pagamentos_custos_servico_por_evento_tipo(
        data_limite=data_limite,
    )
    total_manuais = quantizar_moeda(
        sum(
            (decimal_zero(despesa.valor_pago) for despesa in despesas_manuais),
            Decimal("0.00"),
        )
    )
    total_servico_estruturado = quantizar_moeda(
        sum(totais_registrados.values(), Decimal("0.00"))
    )
    total_servico_legado = somar_itens_legado(
        pagamentos_custos_servico_legado(
            data_limite,
            totais_registrados=totais_registrados,
            despesas=despesas_servico_legado,
        )
    )
    return quantizar_moeda(
        total_manuais + total_servico_estruturado + total_servico_legado
    )


def despesas_operacionais_pagas_para_caixa(data_limite=None):
    from .models import DespesaOperacional

    despesas = DespesaOperacional.objects.select_related("evento").filter(
        valor_pago__gt=ZERO_DECIMAL,
    )
    if data_limite:
        despesas = despesas.filter(
            filtro_data_efetiva("data_pagamento", "data_vencimento", data_limite)
        )

    return list(despesas.order_by("data_vencimento", "id"))


def despesa_manual_entra_no_caixa(despesa):
    from .models import DespesaOperacional

    if despesa.origem != DespesaOperacional.ORIGEM_MANUAL:
        return False

    if despesa.descricao.startswith("Custo extra: "):
        return False

    if (
        despesa.categoria in ["mao_obra", "alimentacao", "transporte"]
        and (
            despesa.descricao.endswith("prevista")
            or despesa.descricao.endswith("previsto")
        )
    ):
        return False

    return True


def despesa_candidata_custo_servico_legado(despesa):
    from .models import DespesaOperacional

    if despesa.origem == DespesaOperacional.ORIGEM_CUSTO_SERVICO:
        return True

    descricoes_reservadas = [
        config[0]
        for config in DespesaOperacional.CUSTOS_SERVICO_DERIVADOS.values()
    ]
    return (
        despesa.origem == DespesaOperacional.ORIGEM_MANUAL
        and despesa.categoria in DespesaOperacional.CUSTOS_SERVICO_DERIVADOS
        and despesa.descricao in descricoes_reservadas
    )


def total_custos_fixos_pagos(data_limite=None):
    from .models_custo_fixo import CustoFixo

    custos_fixos = CustoFixo.objects.filter(valor_pago__gt=ZERO_DECIMAL)
    if data_limite:
        custos_fixos = custos_fixos.filter(
            filtro_data_efetiva("data_pagamento", "data_vencimento", data_limite)
        )

    return somar_campo(custos_fixos, "valor_pago")


def total_investimentos_saida_realizados(data_limite=None):
    from .constants_financeiros import TIPO_FLUXO_SAIDA
    from .models_fci import Investimento

    investimentos = Investimento.objects.filter(
        ativo=True,
        tipo_fluxo=TIPO_FLUXO_SAIDA,
        valor_realizado__gt=ZERO_DECIMAL,
    )
    if data_limite:
        investimentos = investimentos.filter(
            filtro_data_efetiva("data_realizacao", "data_prevista", data_limite)
        )

    return somar_campo(investimentos, "valor_realizado")


def total_financiamentos_saida_realizados(data_limite=None):
    from .constants_financeiros import TIPO_FLUXO_SAIDA
    from .models_fcf import FinanciamentoMovimentacao

    financiamentos = FinanciamentoMovimentacao.objects.filter(
        ativo=True,
        tipo_fluxo=TIPO_FLUXO_SAIDA,
        valor_realizado__gt=ZERO_DECIMAL,
    )
    if data_limite:
        financiamentos = financiamentos.filter(
            filtro_data_efetiva("data_realizacao", "data_prevista", data_limite)
        )

    return somar_campo(financiamentos, "valor_realizado")


def total_pagamentos_parcelas(data_limite=None):
    from .models_dividas import PagamentoParcelaDivida

    pagamentos = PagamentoParcelaDivida.objects.filter(valor_pagamento__gt=ZERO_DECIMAL)
    if data_limite:
        pagamentos = pagamentos.filter(data_pagamento__lte=data_limite)

    return somar_campo(pagamentos, "valor_pagamento")


def total_pagamentos_custos_servico(data_limite=None):
    from .models_pagamentos import PagamentoEventoCustoServico

    pagamentos = PagamentoEventoCustoServico.objects.filter(valor_pagamento__gt=ZERO_DECIMAL)
    if data_limite:
        pagamentos = pagamentos.filter(data_pagamento__lte=data_limite)

    return somar_campo(pagamentos, "valor_pagamento")


def total_pagamentos_custos_servico_legado(data_limite=None):
    return somar_itens_legado(pagamentos_custos_servico_legado(data_limite))


def total_pagamentos_custos_servico_com_legado(data_limite=None):
    totais_registrados = totais_pagamentos_custos_servico_por_evento_tipo(
        data_limite=data_limite,
    )
    total_registrado = quantizar_moeda(
        sum(totais_registrados.values(), Decimal("0.00"))
    )
    total_legado = somar_itens_legado(
        pagamentos_custos_servico_legado(
            data_limite,
            totais_registrados=totais_registrados,
        )
    )
    return quantizar_moeda(total_registrado + total_legado)


def pagamentos_custos_servico_legado(
    data_limite=None,
    totais_registrados=None,
    despesas=None,
):
    from .models import DespesaOperacional

    if despesas is None:
        descricoes_reservadas = [
            config[0]
            for config in DespesaOperacional.CUSTOS_SERVICO_DERIVADOS.values()
        ]
        despesas = DespesaOperacional.objects.select_related("evento").filter(
            valor_pago__gt=ZERO_DECIMAL,
        ).filter(
            Q(origem=DespesaOperacional.ORIGEM_CUSTO_SERVICO)
            | Q(
                origem=DespesaOperacional.ORIGEM_MANUAL,
                categoria__in=DespesaOperacional.CUSTOS_SERVICO_DERIVADOS.keys(),
                descricao__in=descricoes_reservadas,
            )
        )
        if data_limite:
            despesas = despesas.filter(
                filtro_data_efetiva("data_pagamento", "data_vencimento", data_limite)
            )
        despesas = list(despesas.order_by("data_vencimento", "id"))
    else:
        despesas = sorted(
            despesas,
            key=lambda despesa: (despesa.data_vencimento, despesa.id),
        )

    tipos_por_despesa = {
        despesa.id: tipo_custo_servico_despesa(despesa)
        for despesa in despesas
    }
    tipos = {tipo for tipo in tipos_por_despesa.values() if tipo}
    event_ids = {despesa.evento_id for despesa in despesas}
    if totais_registrados is None:
        totais_registrados = totais_pagamentos_custos_servico_por_evento_tipo(
            event_ids=event_ids,
            tipos=tipos,
            data_limite=data_limite,
        )
    chaves_estruturadas = chaves_custos_servico_estruturados(despesas)

    itens = []
    for despesa in despesas:
        tipo = tipos_por_despesa[despesa.id]
        if not tipo:
            continue

        if (
            despesa.origem == DespesaOperacional.ORIGEM_MANUAL
            and (despesa.evento_id, despesa.categoria) not in chaves_estruturadas
        ):
            continue

        total_registrado = totais_registrados.get(
            (despesa.evento_id, tipo),
            Decimal("0.00"),
        )
        valor_legado = quantizar_moeda(
            decimal_zero(despesa.valor_pago) - total_registrado
        )
        if valor_legado <= ZERO_DECIMAL:
            continue

        itens.append({
            "data": data_efetiva(despesa, "data_pagamento", "data_vencimento"),
            "descricao": f"{despesa.evento} / {despesa.descricao}",
            "valor": valor_legado,
            "despesa": despesa,
        })

    return itens


def totais_pagamentos_custos_servico_por_evento_tipo(
    event_ids=None,
    tipos=None,
    data_limite=None,
):
    from .models_pagamentos import PagamentoEventoCustoServico

    if event_ids is not None and not event_ids:
        return {}

    if tipos is not None and not tipos:
        return {}

    pagamentos = PagamentoEventoCustoServico.objects.filter(
        valor_pagamento__gt=ZERO_DECIMAL,
    )
    if event_ids is not None:
        pagamentos = pagamentos.filter(custo_servico__evento_id__in=event_ids)
    if tipos is not None:
        pagamentos = pagamentos.filter(tipo__in=tipos)
    if data_limite:
        pagamentos = pagamentos.filter(data_pagamento__lte=data_limite)

    return {
        (item["custo_servico__evento_id"], item["tipo"]): quantizar_moeda(
            item["total"]
        )
        for item in pagamentos.values(
            "custo_servico__evento_id",
            "tipo",
        ).annotate(total=Sum("valor_pagamento"))
    }


def chaves_custos_servico_estruturados(despesas):
    from .models import DespesaOperacional
    from .models_servico import EventoCustoServico

    despesas_manuais = [
        despesa
        for despesa in despesas
        if despesa.origem == DespesaOperacional.ORIGEM_MANUAL
    ]
    if not despesas_manuais:
        return set()

    event_ids = {despesa.evento_id for despesa in despesas_manuais}
    chaves = set()
    for categoria, (_descricao, campo_valor, _tipo) in (
        DespesaOperacional.CUSTOS_SERVICO_DERIVADOS.items()
    ):
        ids = EventoCustoServico.objects.filter(
            evento_id__in=event_ids,
            **{f"{campo_valor}__gt": ZERO_DECIMAL},
        ).values_list("evento_id", flat=True)
        chaves.update((evento_id, categoria) for evento_id in ids)

    return chaves


def tipo_custo_servico_despesa(despesa):
    from .models import DespesaOperacional

    if (
        despesa.origem == DespesaOperacional.ORIGEM_CUSTO_SERVICO
        and despesa.origem_custo_servico_tipo
    ):
        return despesa.origem_custo_servico_tipo

    config = DespesaOperacional.CUSTOS_SERVICO_DERIVADOS.get(despesa.categoria)
    if not config:
        return ""

    descricao, _campo_valor, tipo = config
    if despesa.descricao != descricao:
        return ""

    return tipo


def total_pagamentos_custos_extras(data_limite=None):
    from .models_pagamentos import PagamentoEventoCustoExtra

    pagamentos = PagamentoEventoCustoExtra.objects.filter(valor_pagamento__gt=ZERO_DECIMAL)
    if data_limite:
        pagamentos = pagamentos.filter(data_pagamento__lte=data_limite)

    return somar_campo(pagamentos, "valor_pagamento")


def total_pagamentos_parcelas_legado(data_limite=None):
    from .models_dividas import ParcelaDivida

    parcelas = ParcelaDivida.objects.filter(valor_pago__gt=ZERO_DECIMAL).annotate(
        total_registrado=Sum("pagamentos__valor_pagamento")
    )
    if data_limite:
        parcelas = parcelas.filter(data_vencimento_atual__lte=data_limite)

    total = Decimal("0.00")
    for parcela in parcelas:
        valor_legado = decimal_zero(parcela.valor_pago) - decimal_zero(parcela.total_registrado)
        if valor_legado > ZERO_DECIMAL:
            total += valor_legado

    return quantizar_moeda(total)


def valor_pagamento_original_no_periodo(pagamento_original, data_limite=None):
    if not pagamento_original or not getattr(pagamento_original, "pk", None):
        return Decimal("0.00")

    try:
        original = pagamento_original.__class__.objects.get(pk=pagamento_original.pk)
    except pagamento_original.__class__.DoesNotExist:
        return Decimal("0.00")

    data_original = getattr(original, "data_pagamento", None)
    if data_limite and data_original and data_original > data_limite:
        return Decimal("0.00")

    return decimal_zero(getattr(original, "valor_pagamento", Decimal("0.00")))


def filtro_data_efetiva(campo_realizado, campo_previsto, data_limite):
    return (
        Q(**{f"{campo_realizado}__lte": data_limite})
        | (
            Q(**{f"{campo_realizado}__isnull": True})
            & Q(**{f"{campo_previsto}__lte": data_limite})
        )
    )


def data_efetiva(objeto, campo_realizado, campo_previsto):
    return getattr(objeto, campo_realizado) or getattr(objeto, campo_previsto)


def somar_campo(queryset, campo):
    return quantizar_moeda(decimal_zero(queryset.aggregate(total=Sum(campo))["total"]))


def somar_itens_legado(itens):
    return quantizar_moeda(
        sum((decimal_zero(item["valor"]) for item in itens), Decimal("0.00"))
    )
