from decimal import Decimal

from django.db import migrations


ZERO = Decimal("0.00")
TIPO_ENTRADA = "entrada"
TIPO_SAIDA = "saida"
FLUXO_FCO = "fco"
FLUXO_FCI = "fci"
FLUXO_FCF = "fcf"
STATUS_REALIZADO = "realizado"


def criar_lancamento(
    *,
    tipo,
    fluxo,
    natureza,
    valor,
    data_lancamento,
    descricao,
    forma="",
    observacao="",
    cliente_id=None,
    contrato_operacional_id=None,
    evento_id=None,
    **origem,
):
    return {
        "tipo": tipo,
        "fluxo": fluxo,
        "natureza": natureza,
        "valor": valor,
        "data_lancamento": data_lancamento,
        "forma": forma or "",
        "descricao": descricao[:255],
        "observacao": observacao or "",
        "status": STATUS_REALIZADO,
        "cliente_id": cliente_id,
        "contrato_operacional_id": contrato_operacional_id,
        "evento_id": evento_id,
        **origem,
    }


def evento_ids(evento):
    if not evento:
        return {
            "cliente_id": None,
            "contrato_operacional_id": None,
            "evento_id": None,
        }

    return {
        "cliente_id": evento.cliente_id,
        "contrato_operacional_id": evento.contrato_operacional_id,
        "evento_id": evento.id,
    }


def criar_lancamentos_de_receitas(apps):
    ReceitaOperacional = apps.get_model("caixa", "ReceitaOperacional")

    for receita in ReceitaOperacional.objects.select_related("evento").filter(
        valor_recebido__gt=ZERO
    ).exclude(status="cancelado").iterator():
        yield criar_lancamento(
            tipo=TIPO_ENTRADA,
            fluxo=FLUXO_FCO,
            natureza="receita_operacional",
            valor=receita.valor_recebido,
            data_lancamento=receita.data_recebimento or receita.data_vencimento,
            descricao=receita.descricao,
            forma=receita.forma_pagamento,
            observacao=receita.observacao,
            cliente_id=receita.cliente_id,
            contrato_operacional_id=receita.evento.contrato_operacional_id,
            evento_id=receita.evento_id,
            receita_operacional_id=receita.id,
        )


def criar_lancamentos_de_despesas_manuais(apps):
    DespesaOperacional = apps.get_model("caixa", "DespesaOperacional")

    for despesa in DespesaOperacional.objects.select_related("evento").filter(
        origem="manual",
        valor_pago__gt=ZERO,
    ).exclude(status="cancelado").iterator():
        yield criar_lancamento(
            tipo=TIPO_SAIDA,
            fluxo=FLUXO_FCO,
            natureza="despesa_operacional",
            valor=despesa.valor_pago,
            data_lancamento=despesa.data_pagamento or despesa.data_vencimento,
            descricao=despesa.descricao,
            forma=despesa.forma_pagamento,
            observacao=despesa.observacao,
            **evento_ids(despesa.evento),
            despesa_operacional_id=despesa.id,
        )


def criar_lancamentos_de_pagamentos_custo_servico(apps):
    PagamentoEventoCustoServico = apps.get_model(
        "caixa",
        "PagamentoEventoCustoServico",
    )

    pagamentos = PagamentoEventoCustoServico.objects.select_related(
        "custo_servico__evento",
        "custo_servico__servico",
    )
    for pagamento in pagamentos.iterator():
        descricao = pagamento.descricao or (
            f"Pagamento de custo de servico "
            f"{pagamento.tipo} - {pagamento.custo_servico.servico.nome}"
        )
        yield criar_lancamento(
            tipo=TIPO_SAIDA,
            fluxo=FLUXO_FCO,
            natureza="custo_servico",
            valor=pagamento.valor_pagamento,
            data_lancamento=pagamento.data_pagamento,
            descricao=descricao,
            observacao=pagamento.observacao,
            **evento_ids(pagamento.custo_servico.evento),
            pagamento_custo_servico_id=pagamento.id,
        )


def criar_lancamentos_de_pagamentos_custo_extra(apps):
    PagamentoEventoCustoExtra = apps.get_model("caixa", "PagamentoEventoCustoExtra")

    pagamentos = PagamentoEventoCustoExtra.objects.select_related(
        "custo_extra__evento",
    )
    for pagamento in pagamentos.iterator():
        yield criar_lancamento(
            tipo=TIPO_SAIDA,
            fluxo=FLUXO_FCO,
            natureza="custo_extra",
            valor=pagamento.valor_pagamento,
            data_lancamento=pagamento.data_pagamento,
            descricao=pagamento.descricao or pagamento.custo_extra.descricao,
            observacao=pagamento.observacao,
            **evento_ids(pagamento.custo_extra.evento),
            pagamento_custo_extra_id=pagamento.id,
        )


def criar_lancamentos_de_pagamentos_parcela(apps):
    PagamentoParcelaDivida = apps.get_model("caixa", "PagamentoParcelaDivida")

    pagamentos = PagamentoParcelaDivida.objects.select_related(
        "parcela__divida",
    )
    for pagamento in pagamentos.iterator():
        parcela = pagamento.parcela
        divida = parcela.divida
        yield criar_lancamento(
            tipo=TIPO_SAIDA,
            fluxo=FLUXO_FCF,
            natureza="parcela_divida",
            valor=pagamento.valor_pagamento,
            data_lancamento=pagamento.data_pagamento,
            descricao=(
                f"{divida.credor} - {divida.descricao} - "
                f"Parcela {parcela.numero_parcela}"
            ),
            forma=pagamento.forma_pagamento,
            observacao=pagamento.observacao,
            pagamento_parcela_divida_id=pagamento.id,
        )


def criar_lancamentos_de_investimentos(apps):
    Investimento = apps.get_model("caixa", "Investimento")

    for investimento in Investimento.objects.filter(
        valor_realizado__gt=ZERO
    ).exclude(status="cancelado").iterator():
        yield criar_lancamento(
            tipo=investimento.tipo_fluxo,
            fluxo=FLUXO_FCI,
            natureza="investimento",
            valor=investimento.valor_realizado,
            data_lancamento=investimento.data_realizacao or investimento.data_prevista,
            descricao=investimento.descricao,
            observacao=investimento.observacao,
            investimento_id=investimento.id,
        )


def criar_lancamentos_de_financiamentos(apps):
    FinanciamentoMovimentacao = apps.get_model("caixa", "FinanciamentoMovimentacao")

    for financiamento in FinanciamentoMovimentacao.objects.filter(
        valor_realizado__gt=ZERO
    ).exclude(status="cancelado").iterator():
        yield criar_lancamento(
            tipo=financiamento.tipo_fluxo,
            fluxo=FLUXO_FCF,
            natureza="financiamento",
            valor=financiamento.valor_realizado,
            data_lancamento=financiamento.data_realizacao
            or financiamento.data_prevista,
            descricao=financiamento.descricao,
            observacao=financiamento.observacao,
            financiamento_movimentacao_id=financiamento.id,
        )


def backfill_lancamentos_financeiros(apps, schema_editor):
    LancamentoFinanceiro = apps.get_model("caixa", "LancamentoFinanceiro")
    criadores = (
        criar_lancamentos_de_receitas,
        criar_lancamentos_de_despesas_manuais,
        criar_lancamentos_de_pagamentos_custo_servico,
        criar_lancamentos_de_pagamentos_custo_extra,
        criar_lancamentos_de_pagamentos_parcela,
        criar_lancamentos_de_investimentos,
        criar_lancamentos_de_financiamentos,
    )
    lote = []

    for criar_lancamentos in criadores:
        for dados in criar_lancamentos(apps):
            lote.append(LancamentoFinanceiro(**dados))

            if len(lote) >= 500:
                LancamentoFinanceiro.objects.bulk_create(lote)
                lote = []

    if lote:
        LancamentoFinanceiro.objects.bulk_create(lote)


class Migration(migrations.Migration):

    dependencies = [
        ("caixa", "0019_historicallancamentofinanceiro_lancamentofinanceiro"),
    ]

    operations = [
        migrations.RunPython(
            backfill_lancamentos_financeiros,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
