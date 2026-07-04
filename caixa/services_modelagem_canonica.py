from decimal import Decimal

from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
    STATUS_REALIZADO,
    TIPO_CUSTO_ALIMENTACAO,
    TIPO_CUSTO_DIARIAS,
    TIPO_CUSTO_TRANSPORTE,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from .models import (
    BaixaFinanceira,
    BaixaFinanceiraAlocacao,
    DespesaOperacional,
    LancamentoFinanceiro,
    ObrigacaoFinanceira,
    ReceitaOperacional,
    STATUS_LIQUIDADO_CANONICO,
)
from .models_custo_fixo import CustoFixo
from .models_custos_extras import EventoCustoExtra
from .models_dividas import ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .models_servico import EventoCustoServico
from .services_dimensoes_operacionais import dados_dimensao_operacional
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")

CUSTOS_SERVICO_CANONICOS = (
    {
        "detalhe": TIPO_CUSTO_DIARIAS,
        "rotulo": "Diarias",
        "campo_previsto": "valor_diarias",
        "campo_realizado": "total_pago_diarias",
        "campo_pendente": "valor_pendente_diarias",
    },
    {
        "detalhe": TIPO_CUSTO_ALIMENTACAO,
        "rotulo": "Alimentacao",
        "campo_previsto": "valor_alimentacao",
        "campo_realizado": "total_pago_alimentacao",
        "campo_pendente": "valor_pendente_alimentacao",
    },
    {
        "detalhe": TIPO_CUSTO_TRANSPORTE,
        "rotulo": "Transporte",
        "campo_previsto": "valor_transporte",
        "campo_realizado": "total_pago_transporte",
        "campo_pendente": "valor_pendente_transporte",
    },
)

FK_OBRIGACAO_PARIDADE = (
    "cliente",
    "evento",
    "receita_operacional",
    "despesa_operacional",
    "custo_fixo",
    "evento_custo_servico",
    "evento_custo_extra",
    "parcela_divida",
    "investimento",
    "financiamento_movimentacao",
)

CAMPOS_OBRIGACAO_PARIDADE = (
    "tipo",
    "origem",
    "detalhe_origem",
    "fluxo",
    "natureza",
    "descricao",
    "referencia",
    "data_vencimento",
    "valor_previsto",
    "valor_realizado",
    "valor_pendente",
    "valor_excedente_realizado",
    "status",
    *FK_OBRIGACAO_PARIDADE,
)

FK_BAIXA_PARIDADE = (
    "cliente",
    "evento",
    "lancamento_financeiro",
    "receita_operacional",
    "despesa_operacional",
    "custo_fixo",
    "pagamento_custo_servico",
    "pagamento_custo_extra",
    "pagamento_parcela_divida",
    "investimento",
    "financiamento_movimentacao",
)

CAMPOS_BAIXA_PARIDADE = (
    "tipo",
    "fluxo",
    "natureza",
    "valor_total",
    "data_baixa",
    "forma_pagamento",
    "descricao",
    "observacao",
    "status",
    *FK_BAIXA_PARIDADE,
)

CAMPOS_DECIMAIS_PARIDADE = (
    "valor_previsto",
    "valor_realizado",
    "valor_pendente",
    "valor_excedente_realizado",
    "valor_total",
    "valor_alocado",
)


def sincronizar_modelagem_financeira_canonica(aplicar=False):
    resultado = {
        "aplicar": aplicar,
        "obrigacoes": {"criadas": 0, "atualizadas": 0},
        "baixas": {"criadas": 0, "atualizadas": 0},
        "alocacoes": {"criadas": 0, "atualizadas": 0, "semObrigacao": 0},
    }

    for chave, dados in iterar_obrigacoes_canonicas():
        criada = _salvar_ou_simular(
            ObrigacaoFinanceira,
            chave,
            dados,
            aplicar,
        )
        if criada:
            resultado["obrigacoes"]["criadas"] += 1
        else:
            resultado["obrigacoes"]["atualizadas"] += 1

    for lancamento in _lancamentos_realizados():
        chave, dados = dados_baixa_por_lancamento(lancamento)
        criada = _salvar_ou_simular(
            BaixaFinanceira,
            chave,
            dados,
            aplicar,
        )
        if criada:
            resultado["baixas"]["criadas"] += 1
        else:
            resultado["baixas"]["atualizadas"] += 1

        obrigacao_chave = chave_obrigacao_por_lancamento(lancamento)
        if not obrigacao_chave:
            resultado["alocacoes"]["semObrigacao"] += 1
            continue

        obrigacao = ObrigacaoFinanceira.objects.filter(
            chave_origem=obrigacao_chave
        ).first()
        if not obrigacao and not aplicar:
            resultado["alocacoes"]["criadas"] += 1
            continue
        if not obrigacao:
            resultado["alocacoes"]["semObrigacao"] += 1
            continue

        baixa = BaixaFinanceira.objects.filter(chave_origem=chave).first()
        if not baixa and not aplicar:
            resultado["alocacoes"]["criadas"] += 1
            continue
        if not baixa:
            resultado["alocacoes"]["semObrigacao"] += 1
            continue

        criada_alocacao = _salvar_alocacao_ou_simular(
            baixa,
            obrigacao,
            lancamento.valor,
            aplicar,
        )
        if criada_alocacao:
            resultado["alocacoes"]["criadas"] += 1
        else:
            resultado["alocacoes"]["atualizadas"] += 1

    return resultado


def sincronizar_obrigacao_receita_canonica(receita):
    chave = f"receita_operacional:{receita.id}"
    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_RECEBER,
            origem="receita_operacional",
            detalhe="",
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_RECEITA_OPERACIONAL,
            descricao=receita.descricao,
            referencia=receita.evento.nome_evento,
            data_vencimento=receita.data_vencimento,
            valor_previsto=receita.valor_previsto,
            valor_realizado=receita.valor_recebido,
            valor_pendente=receita.valor_pendente_recebimento,
            status_origem=receita.status,
            dimensao_fonte=receita,
            receita_operacional=receita,
        ),
    )


def sincronizar_obrigacao_despesa_manual_canonica(despesa):
    chave = f"despesa_operacional:{despesa.id}"
    if despesa.origem != DespesaOperacional.ORIGEM_MANUAL:
        ObrigacaoFinanceira.objects.filter(chave_origem=chave).delete()
        return None

    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="despesa_operacional",
            detalhe=despesa.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            descricao=despesa.descricao,
            referencia=despesa.evento.nome_evento,
            data_vencimento=despesa.data_vencimento,
            valor_previsto=despesa.valor_previsto,
            valor_realizado=despesa.valor_pago,
            valor_pendente=despesa.valor_pendente_pagamento,
            status_origem=despesa.status,
            dimensao_fonte=despesa,
            despesa_operacional=despesa,
        ),
    )


def sincronizar_obrigacao_custo_fixo_canonica(custo):
    chave = f"custo_fixo:{custo.id}"
    if not custo.ativo:
        ObrigacaoFinanceira.objects.filter(chave_origem=chave).delete()
        return None

    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="custo_fixo",
            detalhe=custo.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            descricao=custo.descricao,
            referencia=custo.get_categoria_display(),
            data_vencimento=custo.data_vencimento,
            valor_previsto=custo.valor_previsto,
            valor_realizado=custo.valor_pago,
            valor_pendente=custo.valor_pendente_pagamento,
            status_origem=custo.status,
            dimensao_fonte=None,
            custo_fixo=custo,
        ),
    )


def sincronizar_obrigacoes_custo_servico_canonicas(custo):
    obrigacoes = []
    for componente in CUSTOS_SERVICO_CANONICOS:
        previsto = getattr(custo, componente["campo_previsto"])
        realizado = getattr(custo, componente["campo_realizado"])
        pendente = getattr(custo, componente["campo_pendente"])
        detalhe = componente["detalhe"]
        chave = f"custo_servico:{custo.id}:{detalhe}"

        if previsto <= ZERO and realizado <= ZERO and pendente <= ZERO:
            ObrigacaoFinanceira.objects.filter(chave_origem=chave).delete()
            continue

        obrigacoes.append(
            _salvar_obrigacao_canonica(
                chave,
                _dados_obrigacao(
                    chave=chave,
                    tipo=ObrigacaoFinanceira.TIPO_PAGAR,
                    origem="custo_servico",
                    detalhe=detalhe,
                    fluxo=LancamentoFinanceiro.FLUXO_FCO,
                    natureza=LancamentoFinanceiro.NATUREZA_CUSTO_SERVICO,
                    descricao=f"{custo.servico.nome} - {componente['rotulo']}",
                    referencia=custo.evento.nome_evento,
                    data_vencimento=custo.evento.data_inicio,
                    valor_previsto=previsto,
                    valor_realizado=realizado,
                    valor_pendente=pendente,
                    status_origem=STATUS_PENDENTE,
                    dimensao_fonte=custo,
                    evento_custo_servico=custo,
                ),
            )
        )

    return obrigacoes


def sincronizar_obrigacao_custo_extra_canonica(custo):
    chave = f"custo_extra:{custo.id}"
    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="custo_extra",
            detalhe=custo.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_CUSTO_EXTRA,
            descricao=custo.descricao,
            referencia=custo.evento.nome_evento,
            data_vencimento=custo.data_vencimento,
            valor_previsto=custo.valor_previsto,
            valor_realizado=custo.total_pago,
            valor_pendente=custo.valor_pendente_pagamento,
            status_origem=STATUS_PENDENTE,
            dimensao_fonte=custo,
            evento_custo_extra=custo,
        ),
    )


def sincronizar_obrigacao_parcela_divida_canonica(parcela):
    chave = f"parcela_divida:{parcela.id}"
    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="parcela_divida",
            detalhe=parcela.divida.tipo,
            fluxo=LancamentoFinanceiro.FLUXO_FCF,
            natureza=LancamentoFinanceiro.NATUREZA_PARCELA_DIVIDA,
            descricao=parcela.divida.descricao,
            referencia=f"{parcela.divida.credor} / Parcela {parcela.rotulo_parcela}",
            data_vencimento=parcela.data_vencimento_atual,
            valor_previsto=parcela.valor_total_devido,
            valor_realizado=parcela.valor_pago,
            valor_pendente=parcela.valor_pendente_pagamento,
            status_origem=parcela.status,
            dimensao_fonte=parcela.divida,
            parcela_divida=parcela,
        ),
    )


def sincronizar_obrigacao_investimento_canonica(investimento):
    chave = f"investimento:{investimento.id}"
    if not investimento.ativo:
        ObrigacaoFinanceira.objects.filter(chave_origem=chave).delete()
        return None

    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=_tipo_obrigacao_por_fluxo(investimento.tipo_fluxo),
            origem="investimento",
            detalhe=investimento.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCI,
            natureza=LancamentoFinanceiro.NATUREZA_INVESTIMENTO,
            descricao=investimento.descricao,
            referencia=investimento.get_categoria_display(),
            data_vencimento=investimento.data_prevista,
            valor_previsto=investimento.valor_previsto,
            valor_realizado=investimento.valor_realizado,
            valor_pendente=investimento.valor_pendente_realizacao,
            status_origem=investimento.status,
            dimensao_fonte=investimento,
            investimento=investimento,
        ),
    )


def sincronizar_obrigacao_financiamento_canonica(financiamento):
    chave = f"financiamento_movimentacao:{financiamento.id}"
    if not financiamento.ativo:
        ObrigacaoFinanceira.objects.filter(chave_origem=chave).delete()
        return None

    return _salvar_obrigacao_canonica(
        chave,
        _dados_obrigacao(
            chave=chave,
            tipo=_tipo_obrigacao_por_fluxo(financiamento.tipo_fluxo),
            origem="financiamento_movimentacao",
            detalhe=financiamento.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCF,
            natureza=LancamentoFinanceiro.NATUREZA_FINANCIAMENTO,
            descricao=financiamento.descricao,
            referencia=financiamento.get_categoria_display(),
            data_vencimento=financiamento.data_prevista,
            valor_previsto=financiamento.valor_previsto,
            valor_realizado=financiamento.valor_realizado,
            valor_pendente=financiamento.valor_pendente_realizacao,
            status_origem=financiamento.status,
            dimensao_fonte=financiamento,
            financiamento_movimentacao=financiamento,
        ),
    )


def sincronizar_baixa_canonica_por_lancamento(lancamento):
    chave, dados = dados_baixa_por_lancamento(lancamento)
    if lancamento.status != STATUS_REALIZADO:
        BaixaFinanceira.objects.filter(chave_origem=chave).delete()
        return None

    baixa = _salvar_baixa_canonica(chave, dados)
    obrigacao_chave = chave_obrigacao_por_lancamento(lancamento)
    if not obrigacao_chave:
        return baixa

    obrigacao = ObrigacaoFinanceira.objects.filter(chave_origem=obrigacao_chave).first()
    if not obrigacao:
        return baixa

    _salvar_alocacao_ou_simular(
        baixa,
        obrigacao,
        lancamento.valor,
        aplicar=True,
    )
    return baixa


def sincronizar_baixa_canonica_por_origem(campo_origem, objeto_origem):
    lancamento = LancamentoFinanceiro.objects.filter(
        **{campo_origem: objeto_origem}
    ).first()
    if not lancamento:
        BaixaFinanceira.objects.filter(
            chave_origem=f"{campo_origem}:{objeto_origem.id}"
        ).delete()
        return None

    return sincronizar_baixa_canonica_por_lancamento(lancamento)


def verificar_paridade_modelagem_financeira_canonica(limit=20):
    limit = max(int(limit or 20), 1)
    resultado = {
        "consistent": True,
        "limit": limit,
        "obrigacoes": _resumo_paridade(),
        "baixas": _resumo_paridade(),
        "alocacoes": {
            **_resumo_paridade(),
            "semObrigacao": 0,
            "semBaixa": 0,
        },
        "issues": [],
    }

    _verificar_paridade_obrigacoes(resultado, limit)
    _verificar_paridade_baixas(resultado, limit)
    _verificar_paridade_alocacoes(resultado, limit)
    resultado["consistent"] = not resultado["issues"]
    return resultado


def iterar_obrigacoes_canonicas():
    yield from _obrigacoes_receitas()
    yield from _obrigacoes_despesas_manuais()
    yield from _obrigacoes_custos_fixos()
    yield from _obrigacoes_custos_servico()
    yield from _obrigacoes_custos_extras()
    yield from _obrigacoes_parcelas_divida()
    yield from _obrigacoes_investimentos()
    yield from _obrigacoes_financiamentos()


def _obrigacoes_receitas():
    for receita in ReceitaOperacional.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
        "cliente",
    ):
        chave = f"receita_operacional:{receita.id}"
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_RECEBER,
            origem="receita_operacional",
            detalhe="",
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_RECEITA_OPERACIONAL,
            descricao=receita.descricao,
            referencia=receita.evento.nome_evento,
            data_vencimento=receita.data_vencimento,
            valor_previsto=receita.valor_previsto,
            valor_realizado=receita.valor_recebido,
            valor_pendente=receita.valor_pendente_recebimento,
            status_origem=receita.status,
            dimensao_fonte=receita,
            receita_operacional=receita,
        )


def _obrigacoes_despesas_manuais():
    query = DespesaOperacional.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).filter(origem=DespesaOperacional.ORIGEM_MANUAL)
    for despesa in query:
        chave = f"despesa_operacional:{despesa.id}"
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="despesa_operacional",
            detalhe=despesa.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            descricao=despesa.descricao,
            referencia=despesa.evento.nome_evento,
            data_vencimento=despesa.data_vencimento,
            valor_previsto=despesa.valor_previsto,
            valor_realizado=despesa.valor_pago,
            valor_pendente=despesa.valor_pendente_pagamento,
            status_origem=despesa.status,
            dimensao_fonte=despesa,
            despesa_operacional=despesa,
        )


def _obrigacoes_custos_fixos():
    for custo in CustoFixo.objects.filter(ativo=True):
        chave = f"custo_fixo:{custo.id}"
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="custo_fixo",
            detalhe=custo.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_DESPESA_OPERACIONAL,
            descricao=custo.descricao,
            referencia=custo.get_categoria_display(),
            data_vencimento=custo.data_vencimento,
            valor_previsto=custo.valor_previsto,
            valor_realizado=custo.valor_pago,
            valor_pendente=custo.valor_pendente_pagamento,
            status_origem=custo.status,
            dimensao_fonte=None,
            custo_fixo=custo,
        )


def _obrigacoes_custos_servico():
    query = EventoCustoServico.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
        "servico",
    ).prefetch_related("pagamentos")
    for custo in query:
        for componente in CUSTOS_SERVICO_CANONICOS:
            previsto = getattr(custo, componente["campo_previsto"])
            realizado = getattr(custo, componente["campo_realizado"])
            pendente = getattr(custo, componente["campo_pendente"])
            if previsto <= ZERO and realizado <= ZERO and pendente <= ZERO:
                continue

            detalhe = componente["detalhe"]
            chave = f"custo_servico:{custo.id}:{detalhe}"
            yield chave, _dados_obrigacao(
                chave=chave,
                tipo=ObrigacaoFinanceira.TIPO_PAGAR,
                origem="custo_servico",
                detalhe=detalhe,
                fluxo=LancamentoFinanceiro.FLUXO_FCO,
                natureza=LancamentoFinanceiro.NATUREZA_CUSTO_SERVICO,
                descricao=f"{custo.servico.nome} - {componente['rotulo']}",
                referencia=custo.evento.nome_evento,
                data_vencimento=custo.evento.data_inicio,
                valor_previsto=previsto,
                valor_realizado=realizado,
                valor_pendente=pendente,
                status_origem=STATUS_PENDENTE,
                dimensao_fonte=custo,
                evento_custo_servico=custo,
            )


def _obrigacoes_custos_extras():
    query = EventoCustoExtra.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).prefetch_related("pagamentos")
    for custo in query:
        chave = f"custo_extra:{custo.id}"
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="custo_extra",
            detalhe=custo.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCO,
            natureza=LancamentoFinanceiro.NATUREZA_CUSTO_EXTRA,
            descricao=custo.descricao,
            referencia=custo.evento.nome_evento,
            data_vencimento=custo.data_vencimento,
            valor_previsto=custo.valor_previsto,
            valor_realizado=custo.total_pago,
            valor_pendente=custo.valor_pendente_pagamento,
            status_origem=STATUS_PENDENTE,
            dimensao_fonte=custo,
            evento_custo_extra=custo,
        )


def _obrigacoes_parcelas_divida():
    query = ParcelaDivida.objects.select_related(
        "divida",
        "divida__evento",
        "divida__evento__cliente",
        "divida__evento__orcamento",
    )
    for parcela in query:
        chave = f"parcela_divida:{parcela.id}"
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=ObrigacaoFinanceira.TIPO_PAGAR,
            origem="parcela_divida",
            detalhe=parcela.divida.tipo,
            fluxo=LancamentoFinanceiro.FLUXO_FCF,
            natureza=LancamentoFinanceiro.NATUREZA_PARCELA_DIVIDA,
            descricao=parcela.divida.descricao,
            referencia=f"{parcela.divida.credor} / Parcela {parcela.rotulo_parcela}",
            data_vencimento=parcela.data_vencimento_atual,
            valor_previsto=parcela.valor_total_devido,
            valor_realizado=parcela.valor_pago,
            valor_pendente=parcela.valor_pendente_pagamento,
            status_origem=parcela.status,
            dimensao_fonte=parcela.divida,
            parcela_divida=parcela,
        )


def _obrigacoes_investimentos():
    for investimento in Investimento.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).filter(ativo=True):
        chave = f"investimento:{investimento.id}"
        tipo = _tipo_obrigacao_por_fluxo(investimento.tipo_fluxo)
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=tipo,
            origem="investimento",
            detalhe=investimento.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCI,
            natureza=LancamentoFinanceiro.NATUREZA_INVESTIMENTO,
            descricao=investimento.descricao,
            referencia=investimento.get_categoria_display(),
            data_vencimento=investimento.data_prevista,
            valor_previsto=investimento.valor_previsto,
            valor_realizado=investimento.valor_realizado,
            valor_pendente=investimento.valor_pendente_realizacao,
            status_origem=investimento.status,
            dimensao_fonte=investimento,
            investimento=investimento,
        )


def _obrigacoes_financiamentos():
    for financiamento in FinanciamentoMovimentacao.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
    ).filter(ativo=True):
        chave = f"financiamento_movimentacao:{financiamento.id}"
        tipo = _tipo_obrigacao_por_fluxo(financiamento.tipo_fluxo)
        yield chave, _dados_obrigacao(
            chave=chave,
            tipo=tipo,
            origem="financiamento_movimentacao",
            detalhe=financiamento.categoria,
            fluxo=LancamentoFinanceiro.FLUXO_FCF,
            natureza=LancamentoFinanceiro.NATUREZA_FINANCIAMENTO,
            descricao=financiamento.descricao,
            referencia=financiamento.get_categoria_display(),
            data_vencimento=financiamento.data_prevista,
            valor_previsto=financiamento.valor_previsto,
            valor_realizado=financiamento.valor_realizado,
            valor_pendente=financiamento.valor_pendente_realizacao,
            status_origem=financiamento.status,
            dimensao_fonte=financiamento,
            financiamento_movimentacao=financiamento,
        )


def _dados_obrigacao(
    *,
    chave,
    tipo,
    origem,
    detalhe,
    fluxo,
    natureza,
    descricao,
    referencia,
    data_vencimento,
    valor_previsto,
    valor_realizado,
    valor_pendente,
    status_origem,
    dimensao_fonte,
    **origem_fk,
):
    valor_previsto = quantizar_moeda(valor_previsto)
    valor_realizado = quantizar_moeda(valor_realizado)
    valor_pendente = max(quantizar_moeda(valor_pendente), ZERO)
    dimensao = _dimensao(dimensao_fonte)
    dados = {
        "tipo": tipo,
        "origem": origem,
        "detalhe_origem": detalhe or "",
        "fluxo": fluxo,
        "natureza": natureza,
        "descricao": descricao,
        "referencia": referencia or "",
        "data_vencimento": data_vencimento,
        "valor_previsto": valor_previsto,
        "valor_realizado": valor_realizado,
        "valor_pendente": valor_pendente,
        "valor_excedente_realizado": _excedente(valor_previsto, valor_realizado),
        "status": _status_obrigacao(status_origem, valor_realizado, valor_pendente),
        **dimensao,
    }
    dados.update(_origens_obrigacao_vazias())
    dados.update(origem_fk)
    return dados


def dados_baixa_por_lancamento(lancamento):
    chave = chave_baixa_por_lancamento(lancamento)
    origem_campo, origem_objeto = origem_baixa_por_lancamento(lancamento)
    dados = {
        "tipo": lancamento.tipo,
        "fluxo": lancamento.fluxo,
        "natureza": lancamento.natureza,
        "valor_total": lancamento.valor,
        "data_baixa": lancamento.data_lancamento,
        "forma_pagamento": lancamento.forma or "",
        "descricao": lancamento.descricao,
        "observacao": lancamento.observacao or "",
        "status": lancamento.status,
        "cliente": lancamento.cliente,
        "evento": lancamento.evento,
        "lancamento_financeiro": lancamento,
        **_origens_baixa_vazias(),
    }
    if origem_campo:
        dados[origem_campo] = origem_objeto
    return chave, dados


def chave_baixa_por_lancamento(lancamento):
    origem_campo, origem_objeto = origem_baixa_por_lancamento(lancamento)
    if origem_campo and origem_objeto:
        return f"{origem_campo}:{origem_objeto.id}"
    return f"lancamento_financeiro:{lancamento.id}"


def chave_obrigacao_por_lancamento(lancamento):
    if lancamento.receita_operacional_id:
        return f"receita_operacional:{lancamento.receita_operacional_id}"
    if lancamento.despesa_operacional_id:
        return f"despesa_operacional:{lancamento.despesa_operacional_id}"
    if lancamento.custo_fixo_id:
        return f"custo_fixo:{lancamento.custo_fixo_id}"
    if lancamento.pagamento_custo_servico_id:
        pagamento = lancamento.pagamento_custo_servico
        return f"custo_servico:{pagamento.custo_servico_id}:{pagamento.tipo}"
    if lancamento.pagamento_custo_extra_id:
        return f"custo_extra:{lancamento.pagamento_custo_extra.custo_extra_id}"
    if lancamento.pagamento_parcela_divida_id:
        return f"parcela_divida:{lancamento.pagamento_parcela_divida.parcela_id}"
    if lancamento.investimento_id:
        return f"investimento:{lancamento.investimento_id}"
    if lancamento.financiamento_movimentacao_id:
        return f"financiamento_movimentacao:{lancamento.financiamento_movimentacao_id}"
    return ""


def origem_baixa_por_lancamento(lancamento):
    for campo in (
        "receita_operacional",
        "despesa_operacional",
        "custo_fixo",
        "pagamento_custo_servico",
        "pagamento_custo_extra",
        "pagamento_parcela_divida",
        "investimento",
        "financiamento_movimentacao",
    ):
        if getattr(lancamento, f"{campo}_id"):
            return campo, getattr(lancamento, campo)
    return "", None


def _salvar_ou_simular(modelo, chave, dados, aplicar):
    existe = modelo.objects.filter(chave_origem=chave).exists()
    if aplicar:
        modelo.objects.update_or_create(
            chave_origem=chave,
            defaults=dados,
        )
    return not existe


def _salvar_obrigacao_canonica(chave, dados):
    obrigacao, _ = ObrigacaoFinanceira.objects.update_or_create(
        chave_origem=chave,
        defaults=dados,
    )
    return obrigacao


def _salvar_baixa_canonica(chave, dados):
    baixa, _ = BaixaFinanceira.objects.update_or_create(
        chave_origem=chave,
        defaults=dados,
    )
    return baixa


def _salvar_alocacao_ou_simular(baixa, obrigacao, valor, aplicar):
    existe = BaixaFinanceiraAlocacao.objects.filter(
        baixa=baixa,
        obrigacao=obrigacao,
    ).exists()
    if aplicar:
        BaixaFinanceiraAlocacao.objects.update_or_create(
            baixa=baixa,
            obrigacao=obrigacao,
            defaults={"valor_alocado": valor},
        )
    return not existe


def _dimensao(objeto):
    dimensao = dados_dimensao_operacional(objeto) if objeto else {
        "cliente": None,
        "evento": None,
    }
    return {
        "cliente": dimensao["cliente"],
        "evento": dimensao["evento"],
    }


def _tipo_obrigacao_por_fluxo(tipo_fluxo):
    if tipo_fluxo == TIPO_FLUXO_ENTRADA:
        return ObrigacaoFinanceira.TIPO_RECEBER
    return ObrigacaoFinanceira.TIPO_PAGAR


def _status_obrigacao(status_origem, valor_realizado, valor_pendente):
    if status_origem == STATUS_CANCELADO:
        return STATUS_CANCELADO
    if valor_pendente <= ZERO:
        return STATUS_LIQUIDADO_CANONICO
    if valor_realizado > ZERO:
        return STATUS_PARCIAL
    return STATUS_PENDENTE


def _excedente(valor_previsto, valor_realizado):
    return max(quantizar_moeda(valor_realizado - valor_previsto), ZERO)


def _lancamentos_realizados():
    return LancamentoFinanceiro.objects.select_related(
        "cliente",
        "evento",
        "evento__orcamento",
        "receita_operacional",
        "despesa_operacional",
        "custo_fixo",
        "pagamento_custo_servico",
        "pagamento_custo_servico__custo_servico",
        "pagamento_custo_extra",
        "pagamento_custo_extra__custo_extra",
        "pagamento_parcela_divida",
        "pagamento_parcela_divida__parcela",
        "investimento",
        "financiamento_movimentacao",
    ).filter(status=STATUS_REALIZADO)


def _origens_obrigacao_vazias():
    return {
        "receita_operacional": None,
        "despesa_operacional": None,
        "custo_fixo": None,
        "evento_custo_servico": None,
        "evento_custo_extra": None,
        "parcela_divida": None,
        "investimento": None,
        "financiamento_movimentacao": None,
    }


def _origens_baixa_vazias():
    return {
        "receita_operacional": None,
        "despesa_operacional": None,
        "custo_fixo": None,
        "pagamento_custo_servico": None,
        "pagamento_custo_extra": None,
        "pagamento_parcela_divida": None,
        "investimento": None,
        "financiamento_movimentacao": None,
    }


def _verificar_paridade_obrigacoes(resultado, limit):
    esperado_por_chave = dict(iterar_obrigacoes_canonicas())
    chaves_esperadas = set(esperado_por_chave)
    resumo = resultado["obrigacoes"]
    resumo["expected"] = len(chaves_esperadas)
    resumo["existing"] = ObrigacaoFinanceira.objects.count()

    for chave, dados in esperado_por_chave.items():
        obrigacao = ObrigacaoFinanceira.objects.filter(chave_origem=chave).first()
        if not obrigacao:
            resumo["missing"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="obrigacao_ausente",
                chave=chave,
                mensagem="Obrigacao canonica ausente.",
            )
            continue

        diferencas = _comparar_campos(
            obrigacao,
            dados,
            CAMPOS_OBRIGACAO_PARIDADE,
            FK_OBRIGACAO_PARIDADE,
        )
        if diferencas:
            resumo["divergent"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="obrigacao_divergente",
                chave=chave,
                mensagem="Obrigacao canonica diverge da origem legada.",
                diferencas=diferencas,
            )

    for obrigacao in ObrigacaoFinanceira.objects.exclude(chave_origem__in=chaves_esperadas):
        resumo["extra"] += 1
        _adicionar_issue(
            resultado,
            limit,
            tipo="obrigacao_extra",
            chave=obrigacao.chave_origem or f"obrigacao:{obrigacao.id}",
            mensagem="Obrigacao canonica sem origem esperada no sincronizador.",
        )


def _verificar_paridade_baixas(resultado, limit):
    esperado_por_chave = {}
    for lancamento in _lancamentos_realizados():
        chave, dados = dados_baixa_por_lancamento(lancamento)
        esperado_por_chave[chave] = dados

    chaves_esperadas = set(esperado_por_chave)
    resumo = resultado["baixas"]
    resumo["expected"] = len(chaves_esperadas)
    resumo["existing"] = BaixaFinanceira.objects.count()

    for chave, dados in esperado_por_chave.items():
        baixa = BaixaFinanceira.objects.filter(chave_origem=chave).first()
        if not baixa:
            resumo["missing"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="baixa_ausente",
                chave=chave,
                mensagem="Baixa canonica ausente.",
            )
            continue

        diferencas = _comparar_campos(
            baixa,
            dados,
            CAMPOS_BAIXA_PARIDADE,
            FK_BAIXA_PARIDADE,
        )
        if diferencas:
            resumo["divergent"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="baixa_divergente",
                chave=chave,
                mensagem="Baixa canonica diverge do ledger.",
                diferencas=diferencas,
            )

    for baixa in BaixaFinanceira.objects.exclude(chave_origem__in=chaves_esperadas):
        resumo["extra"] += 1
        _adicionar_issue(
            resultado,
            limit,
            tipo="baixa_extra",
            chave=baixa.chave_origem or f"baixa:{baixa.id}",
            mensagem="Baixa canonica sem ledger esperado no sincronizador.",
        )


def _verificar_paridade_alocacoes(resultado, limit):
    resumo = resultado["alocacoes"]
    pares_esperados = set()

    for lancamento in _lancamentos_realizados():
        resumo["expected"] += 1
        baixa_chave = chave_baixa_por_lancamento(lancamento)
        obrigacao_chave = chave_obrigacao_por_lancamento(lancamento)

        obrigacao = ObrigacaoFinanceira.objects.filter(
            chave_origem=obrigacao_chave
        ).first()
        if not obrigacao:
            resumo["missing"] += 1
            resumo["semObrigacao"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="alocacao_sem_obrigacao",
                chave=f"{baixa_chave}->{obrigacao_chave or 'sem_obrigacao'}",
                mensagem="Alocacao esperada sem obrigacao canonica correspondente.",
            )
            continue

        baixa = BaixaFinanceira.objects.filter(chave_origem=baixa_chave).first()
        if not baixa:
            resumo["missing"] += 1
            resumo["semBaixa"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="alocacao_sem_baixa",
                chave=f"{baixa_chave}->{obrigacao_chave}",
                mensagem="Alocacao esperada sem baixa canonica correspondente.",
            )
            continue

        pares_esperados.add((baixa.id, obrigacao.id))
        alocacao = BaixaFinanceiraAlocacao.objects.filter(
            baixa=baixa,
            obrigacao=obrigacao,
        ).first()
        if not alocacao:
            resumo["missing"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="alocacao_ausente",
                chave=f"{baixa_chave}->{obrigacao_chave}",
                mensagem="Alocacao canonica ausente.",
            )
            continue

        esperado = quantizar_moeda(lancamento.valor)
        atual = quantizar_moeda(alocacao.valor_alocado)
        if atual != esperado:
            resumo["divergent"] += 1
            _adicionar_issue(
                resultado,
                limit,
                tipo="alocacao_divergente",
                chave=f"{baixa_chave}->{obrigacao_chave}",
                mensagem="Valor alocado diverge do lancamento financeiro.",
                diferencas=[
                    {
                        "field": "valor_alocado",
                        "expected": str(esperado),
                        "actual": str(atual),
                    }
                ],
            )

    resumo["existing"] = BaixaFinanceiraAlocacao.objects.count()
    for baixa_id, obrigacao_id in BaixaFinanceiraAlocacao.objects.values_list(
        "baixa_id",
        "obrigacao_id",
    ):
        if (baixa_id, obrigacao_id) in pares_esperados:
            continue
        resumo["extra"] += 1
        _adicionar_issue(
            resultado,
            limit,
            tipo="alocacao_extra",
            chave=f"baixa:{baixa_id}->obrigacao:{obrigacao_id}",
            mensagem="Alocacao canonica sem par esperado no sincronizador.",
        )


def _resumo_paridade():
    return {
        "expected": 0,
        "existing": 0,
        "missing": 0,
        "divergent": 0,
        "extra": 0,
    }


def _comparar_campos(instancia, dados, campos, campos_fk):
    diferencas = []
    for campo in campos:
        esperado = _valor_esperado_paridade(campo, dados.get(campo), campos_fk)
        atual = _valor_atual_paridade(instancia, campo, campos_fk)
        if atual != esperado:
            diferencas.append(
                {
                    "field": campo,
                    "expected": _serializar_valor_paridade(esperado),
                    "actual": _serializar_valor_paridade(atual),
                }
            )
    return diferencas


def _valor_esperado_paridade(campo, valor, campos_fk):
    if campo in campos_fk:
        return valor.pk if valor else None
    if campo in CAMPOS_DECIMAIS_PARIDADE:
        return quantizar_moeda(valor or ZERO)
    if valor is None:
        return ""
    return valor


def _valor_atual_paridade(instancia, campo, campos_fk):
    if campo in campos_fk:
        return getattr(instancia, f"{campo}_id")
    valor = getattr(instancia, campo)
    if campo in CAMPOS_DECIMAIS_PARIDADE:
        return quantizar_moeda(valor or ZERO)
    if valor is None:
        return ""
    return valor


def _serializar_valor_paridade(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor


def _adicionar_issue(resultado, limit, **issue):
    if len(resultado["issues"]) < limit:
        resultado["issues"].append(issue)
