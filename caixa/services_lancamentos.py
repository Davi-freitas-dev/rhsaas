from .constants_financeiros import STATUS_REALIZADO, TIPO_FLUXO_ENTRADA, TIPO_FLUXO_SAIDA
from .models import DespesaOperacional, LancamentoFinanceiro
from .services_dimensoes_operacionais import dados_dimensao_operacional


def dados_evento(evento):
    if not evento:
        return {
            "cliente": None,
            "evento": None,
        }

    return {
        "cliente": evento.cliente,
        "evento": evento,
    }


def atualizar_lancamento_por_origem(campo_origem, origem, defaults):
    lookup = {campo_origem: origem}
    return LancamentoFinanceiro.objects.update_or_create(
        **lookup,
        defaults=defaults,
    )


def remover_lancamento_por_origem(campo_origem, origem):
    LancamentoFinanceiro.objects.filter(**{campo_origem: origem}).delete()


def sincronizar_lancamento_receita(receita):
    if receita.valor_recebido <= 0 or receita.status == "cancelado":
        remover_lancamento_por_origem("receita_operacional", receita)
        return None

    return atualizar_lancamento_por_origem(
        "receita_operacional",
        receita,
        {
            "tipo": TIPO_FLUXO_ENTRADA,
            "fluxo": LancamentoFinanceiro.FLUXO_FCO,
            "natureza": LancamentoFinanceiro.NATUREZA_RECEITA_OPERACIONAL,
            "valor": receita.valor_recebido,
            "data_lancamento": receita.data_recebimento or receita.data_vencimento,
            "forma": receita.forma_pagamento,
            "descricao": receita.descricao,
            "observacao": receita.observacao,
            "status": STATUS_REALIZADO,
            "cliente": receita.cliente,
            "evento": receita.evento,
        },
    )


def sincronizar_lancamento_despesa_manual(despesa):
    if (
        despesa.origem != DespesaOperacional.ORIGEM_MANUAL
        or despesa.valor_pago <= 0
        or despesa.status == "cancelado"
    ):
        remover_lancamento_por_origem("despesa_operacional", despesa)
        return None

    return atualizar_lancamento_por_origem(
        "despesa_operacional",
        despesa,
        {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": LancamentoFinanceiro.FLUXO_FCO,
            "natureza": LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            "valor": despesa.valor_pago,
            "data_lancamento": despesa.data_pagamento or despesa.data_vencimento,
            "forma": despesa.forma_pagamento,
            "descricao": despesa.descricao,
            "observacao": despesa.observacao,
            "status": STATUS_REALIZADO,
            **dados_evento(despesa.evento),
        },
    )


def sincronizar_lancamento_custo_fixo(custo_fixo):
    if custo_fixo.valor_pago <= 0 or custo_fixo.status == "cancelado":
        remover_lancamento_por_origem("custo_fixo", custo_fixo)
        return None

    return atualizar_lancamento_por_origem(
        "custo_fixo",
        custo_fixo,
        {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": LancamentoFinanceiro.FLUXO_FCO,
            "natureza": LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            "valor": custo_fixo.valor_pago,
            "data_lancamento": custo_fixo.data_pagamento or custo_fixo.data_vencimento,
            "forma": "",
            "descricao": custo_fixo.descricao,
            "observacao": custo_fixo.observacao,
            "status": STATUS_REALIZADO,
            "cliente": None,
            "evento": None,
        },
    )


def sincronizar_lancamento_pagamento_custo_servico(pagamento):
    custo_servico = pagamento.custo_servico
    descricao = pagamento.descricao or (
        f"Pagamento de custo de serviço {pagamento.tipo} - {custo_servico.servico.nome}"
    )

    return atualizar_lancamento_por_origem(
        "pagamento_custo_servico",
        pagamento,
        {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": LancamentoFinanceiro.FLUXO_FCO,
            "natureza": LancamentoFinanceiro.NATUREZA_CUSTO_SERVICO,
            "valor": pagamento.valor_pagamento,
            "data_lancamento": pagamento.data_pagamento,
            "forma": "",
            "descricao": descricao,
            "observacao": pagamento.observacao,
            "status": STATUS_REALIZADO,
            **dados_evento(custo_servico.evento),
        },
    )


def sincronizar_lancamento_pagamento_custo_extra(pagamento):
    custo_extra = pagamento.custo_extra

    return atualizar_lancamento_por_origem(
        "pagamento_custo_extra",
        pagamento,
        {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": LancamentoFinanceiro.FLUXO_FCO,
            "natureza": LancamentoFinanceiro.NATUREZA_CUSTO_EXTRA,
            "valor": pagamento.valor_pagamento,
            "data_lancamento": pagamento.data_pagamento,
            "forma": "",
            "descricao": pagamento.descricao or custo_extra.descricao,
            "observacao": pagamento.observacao,
            "status": STATUS_REALIZADO,
            **dados_evento(custo_extra.evento),
        },
    )


def sincronizar_lancamento_pagamento_parcela(pagamento):
    parcela = pagamento.parcela
    divida = parcela.divida

    return atualizar_lancamento_por_origem(
        "pagamento_parcela_divida",
        pagamento,
        {
            "tipo": TIPO_FLUXO_SAIDA,
            "fluxo": LancamentoFinanceiro.FLUXO_FCF,
            "natureza": LancamentoFinanceiro.NATUREZA_PARCELA_DIVIDA,
            "valor": pagamento.valor_pagamento,
            "data_lancamento": pagamento.data_pagamento,
            "forma": pagamento.forma_pagamento,
            "descricao": (
                f"{divida.credor} - {divida.descricao} - Parcela {parcela.numero_parcela}"
            ),
            "observacao": pagamento.observacao,
            "status": STATUS_REALIZADO,
            **dados_dimensao_operacional(divida),
        },
    )


def sincronizar_lancamento_investimento(investimento):
    if investimento.valor_realizado <= 0 or investimento.status == "cancelado":
        remover_lancamento_por_origem("investimento", investimento)
        return None

    return atualizar_lancamento_por_origem(
        "investimento",
        investimento,
        {
            "tipo": investimento.tipo_fluxo,
            "fluxo": LancamentoFinanceiro.FLUXO_FCI,
            "natureza": LancamentoFinanceiro.NATUREZA_INVESTIMENTO,
            "valor": investimento.valor_realizado,
            "data_lancamento": investimento.data_realizacao or investimento.data_prevista,
            "forma": "",
            "descricao": investimento.descricao,
            "observacao": investimento.observacao,
            "status": STATUS_REALIZADO,
            **dados_dimensao_operacional(investimento),
        },
    )


def sincronizar_lancamento_financiamento(financiamento):
    if financiamento.valor_realizado <= 0 or financiamento.status == "cancelado":
        remover_lancamento_por_origem("financiamento_movimentacao", financiamento)
        return None

    return atualizar_lancamento_por_origem(
        "financiamento_movimentacao",
        financiamento,
        {
            "tipo": financiamento.tipo_fluxo,
            "fluxo": LancamentoFinanceiro.FLUXO_FCF,
            "natureza": LancamentoFinanceiro.NATUREZA_FINANCIAMENTO,
            "valor": financiamento.valor_realizado,
            "data_lancamento": financiamento.data_realizacao
            or financiamento.data_prevista,
            "forma": "",
            "descricao": financiamento.descricao,
            "observacao": financiamento.observacao,
            "status": STATUS_REALIZADO,
            **dados_dimensao_operacional(financiamento),
        },
    )
