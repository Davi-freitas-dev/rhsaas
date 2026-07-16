from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.conf import settings
from django.db import connection, transaction

from .constants_dividas import STATUS_PARCELA_CANCELADA, STATUS_PARCELA_PAGA
from .demo_policy import assert_demo_write_allowed
from .constants_financeiros import (
    STATUS_CANCELADO,
    TIPO_FLUXO_SAIDA,
    TIPOS_CUSTO_SERVICO,
)
from .contracts_obrigacoes import (
    CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
    CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
    PERMISSOES_BAIXA_NATIVA,
    SUPPORTED_NATIVE_SETTLEMENT_SOURCES,
)
from .models import (
    BaixaFinanceiraAlocacao,
    DespesaOperacional,
    ObrigacaoFinanceira,
)
from .models_custo_fixo import CustoFixo
from .models_custos_extras import EventoCustoExtra
from .models_dividas import PagamentoParcelaDivida, ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from .models_servico import EventoCustoServico
from .selectors_obrigacoes import (
    ORIGEM_CUSTO_EXTRA,
    ORIGEM_CUSTO_FIXO,
    ORIGEM_CUSTO_SERVICO,
    ORIGEM_DESPESA_OPERACIONAL,
    ORIGEM_FINANCIAMENTO,
    ORIGEM_INVESTIMENTO,
    ORIGEM_PARCELA_DIVIDA,
    listar_obrigacoes_financeiras,
)
from .serializers_obrigacoes import (
    decimal_para_numero,
    permissoes_action_hints_obrigacoes,
    serializar_obrigacao_financeira,
)
from .services_dividas import montar_motivo_baixa_parcela
from .services_pagamentos_custos_extras import aplicar_baixa_custo_extra
from .services_pagamentos_servico import aplicar_baixa_custo_servico
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")


def select_for_update_self(queryset):
    if connection.features.has_select_for_update_of:
        return queryset.select_for_update(of=("self",))
    return queryset.select_for_update()


class ObrigacaoFinanceiraNaoEncontrada(ValidationError):
    pass


def liquidar_obrigacao_financeira(source, source_id, payload, usuario):
    source = str(source or "").strip()

    if source not in SUPPORTED_NATIVE_SETTLEMENT_SOURCES:
        raise ValidationError(
            {
                "source": (
                    "Esta origem ainda não suporta baixa nativa. Use o fluxo "
                    "especializado existente até a migração definitiva."
                )
            }
        )

    validar_permissao_baixa_nativa(source, usuario)

    if source == ORIGEM_DESPESA_OPERACIONAL:
        despesa = liquidar_despesa_operacional_manual(source_id, payload, usuario)
        return serializar_obrigacao_por_origem(source, despesa.id, usuario=usuario)

    if source == ORIGEM_CUSTO_FIXO:
        custo_fixo = liquidar_custo_fixo(source_id, payload, usuario)
        return serializar_obrigacao_por_origem(source, custo_fixo.id, usuario=usuario)

    if source == ORIGEM_CUSTO_EXTRA:
        custo_extra = liquidar_custo_extra_evento(source_id, payload, usuario)
        return serializar_obrigacao_por_origem(source, custo_extra.id, usuario=usuario)

    if source == ORIGEM_CUSTO_SERVICO:
        tipo = obter_tipo_custo_servico(payload)
        custo_servico = liquidar_custo_servico_evento(source_id, tipo, payload, usuario)
        return serializar_obrigacao_por_origem(
            source,
            custo_servico.id,
            tipo,
            usuario=usuario,
        )

    if source == ORIGEM_PARCELA_DIVIDA:
        parcela = liquidar_parcela_divida_fcf(source_id, payload, usuario)
        return serializar_obrigacao_por_origem(source, parcela.id, usuario=usuario)

    if source == ORIGEM_INVESTIMENTO:
        investimento = liquidar_investimento_fci(source_id, payload, usuario)
        return serializar_obrigacao_por_origem(source, investimento.id, usuario=usuario)

    if source == ORIGEM_FINANCIAMENTO:
        financiamento = liquidar_financiamento_fcf(source_id, payload, usuario)
        return serializar_obrigacao_por_origem(source, financiamento.id, usuario=usuario)

    raise ValidationError({"source": "Origem de obrigação inválida."})


def liquidar_obrigacao_financeira_com_contexto_canonico(
    source,
    source_id,
    payload,
    usuario,
):
    source = str(source or "").strip()
    write_model_source = CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED

    if usar_escrita_canonica_primeiro(source):
        from .services_escrita_canonica import liquidar_obrigacao_canonica_primeiro

        resultado = liquidar_obrigacao_canonica_primeiro(
            source,
            source_id,
            payload,
            usuario,
        )
        item = resultado["item"]
        write_model_source = resultado["writeModelSource"]
    else:
        item = liquidar_obrigacao_financeira(source, source_id, payload, usuario)

    contexto_canonico = serializar_contexto_baixa_canonica(
        item,
        write_model_source=write_model_source,
    )
    return {
        "item": item,
        "canonicalSettlement": contexto_canonico,
        "settlement": contexto_canonico,
    }


def usar_escrita_canonica_primeiro(source):
    fontes_habilitadas = set(
        getattr(settings, "CANONICAL_FIRST_SETTLEMENT_SOURCES", [])
    )
    return (
        bool(getattr(settings, "CANONICAL_FIRST_SETTLEMENT_ENABLED", False))
        and source in fontes_habilitadas
        and source in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
    )


def validar_permissao_baixa_nativa(source, usuario):
    permissao = PERMISSOES_BAIXA_NATIVA.get(source)
    if not permissao:
        raise PermissionDenied

    if not usuario or not usuario.is_authenticated:
        raise PermissionDenied

    if not usuario.has_perm(permissao):
        raise PermissionDenied


def liquidar_despesa_operacional_manual(source_id, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_pago",
    )
    data_pagamento = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    forma_pagamento = obter_texto(payload, "paymentMethod", "formaPagamento", "forma_pagamento")
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")
    motivo_baixa = obter_texto(payload, "writeOffReason", "motivoBaixa", "motivo_baixa")

    with transaction.atomic():
        try:
            despesa = (
                select_for_update_self(DespesaOperacional.objects.all())
                .select_related("evento", "evento__cliente", "evento__orcamento")
                .get(pk=source_id)
            )
        except (TypeError, ValueError, DespesaOperacional.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            despesa,
            operation="settle_operational_expense",
        )

        validar_despesa_operacional_manual_para_baixa(
            despesa,
            valor_realizado,
            data_pagamento,
            baixar_saldo,
            motivo_baixa,
        )

        despesa.valor_pago = valor_realizado
        despesa.data_pagamento = data_pagamento if valor_realizado > ZERO else None

        if forma_pagamento is not None:
            despesa.forma_pagamento = forma_pagamento

        if observacao is not None:
            despesa.observacao = observacao

        if baixar_saldo and valor_realizado < quantizar_moeda(despesa.valor_previsto):
            despesa.baixado_manualmente = True
            despesa.motivo_baixa = motivo_baixa
        else:
            despesa.baixado_manualmente = False
            despesa.motivo_baixa = ""

        despesa.atualizado_por = usuario
        if not despesa.criado_por_id:
            despesa.criado_por = usuario

        despesa.save()
        return despesa


def liquidar_custo_fixo(source_id, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_pago",
    )
    data_pagamento = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")
    motivo_baixa = obter_texto(payload, "writeOffReason", "motivoBaixa", "motivo_baixa")

    with transaction.atomic():
        try:
            custo_fixo = CustoFixo.objects.select_for_update().get(pk=source_id)
        except (TypeError, ValueError, CustoFixo.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            custo_fixo,
            operation="settle_fixed_cost",
        )

        validar_custo_fixo_para_baixa(
            custo_fixo,
            valor_realizado,
            data_pagamento,
            baixar_saldo,
            motivo_baixa,
        )

        custo_fixo.valor_pago = valor_realizado
        custo_fixo.data_pagamento = data_pagamento if valor_realizado > ZERO else None

        if observacao is not None:
            custo_fixo.observacao = observacao

        if baixar_saldo and valor_realizado < quantizar_moeda(custo_fixo.valor_previsto):
            custo_fixo.baixado_manualmente = True
            custo_fixo.motivo_baixa = motivo_baixa
        else:
            custo_fixo.baixado_manualmente = False
            custo_fixo.motivo_baixa = ""

        custo_fixo.atualizado_por = usuario
        if not custo_fixo.criado_por_id:
            custo_fixo.criado_por = usuario

        custo_fixo.save()
        return custo_fixo


def liquidar_investimento_fci(source_id, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_realizado_fci",
    )
    data_realizacao = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
        "realizationDate",
        "dataRealizacao",
        "data_realizacao",
    )
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")
    motivo_baixa = obter_texto(payload, "writeOffReason", "motivoBaixa", "motivo_baixa")

    with transaction.atomic():
        try:
            investimento = (
                select_for_update_self(Investimento.objects.all())
                .select_related(
                    "evento",
                    "evento__cliente",
                    "evento__orcamento",
                )
                .get(pk=source_id)
            )
        except (TypeError, ValueError, Investimento.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            investimento,
            operation="settle_investment",
        )

        validar_investimento_fci_para_baixa(
            investimento,
            valor_realizado,
            data_realizacao,
            baixar_saldo,
            motivo_baixa,
        )

        investimento.valor_realizado = valor_realizado
        investimento.data_realizacao = data_realizacao if valor_realizado > ZERO else None

        if observacao is not None:
            investimento.observacao = observacao

        if baixar_saldo and valor_realizado < quantizar_moeda(investimento.valor_previsto):
            investimento.baixado_manualmente = True
            investimento.motivo_baixa = motivo_baixa
        else:
            investimento.baixado_manualmente = False
            investimento.motivo_baixa = ""

        investimento.atualizado_por = usuario
        if not investimento.criado_por_id:
            investimento.criado_por = usuario

        investimento.save()
        return investimento


def liquidar_financiamento_fcf(source_id, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_realizado_fcf",
    )
    data_realizacao = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
        "realizationDate",
        "dataRealizacao",
        "data_realizacao",
    )
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")

    with transaction.atomic():
        try:
            financiamento = (
                select_for_update_self(FinanciamentoMovimentacao.objects.all())
                .select_related(
                    "evento",
                    "evento__cliente",
                    "evento__orcamento",
                )
                .get(pk=source_id)
            )
        except (TypeError, ValueError, FinanciamentoMovimentacao.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            financiamento,
            operation="settle_financing",
        )

        validar_financiamento_fcf_para_baixa(
            financiamento,
            valor_realizado,
            data_realizacao,
            baixar_saldo,
        )

        financiamento.valor_realizado = valor_realizado
        financiamento.data_realizacao = data_realizacao if valor_realizado > ZERO else None

        if observacao is not None:
            financiamento.observacao = observacao

        financiamento.atualizado_por = usuario
        if not financiamento.criado_por_id:
            financiamento.criado_por = usuario

        financiamento.save()
        return financiamento


def liquidar_custo_extra_evento(source_id, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_pago",
    )
    data_pagamento = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    descricao_pagamento = obter_texto(
        payload,
        "paymentDescription",
        "descricaoPagamento",
        "descricao_pagamento",
    )
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")
    motivo_baixa = obter_texto(payload, "writeOffReason", "motivoBaixa", "motivo_baixa")

    with transaction.atomic():
        try:
            custo_extra = (
                select_for_update_self(EventoCustoExtra.objects.all())
                .select_related("evento", "evento__cliente", "evento__orcamento")
                .get(pk=source_id)
            )
        except (TypeError, ValueError, EventoCustoExtra.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            custo_extra,
            operation="settle_event_extra_cost",
        )

        total_atual = quantizar_moeda(custo_extra.total_pago)
        validar_custo_extra_evento_para_baixa(
            custo_extra,
            valor_realizado,
            total_atual,
            data_pagamento,
            baixar_saldo,
            motivo_baixa,
        )

        delta_pagamento = quantizar_moeda(valor_realizado - total_atual)
        if delta_pagamento > ZERO:
            pagamento = PagamentoEventoCustoExtra(
                custo_extra=custo_extra,
                descricao=descricao_pagamento or "Baixa de obrigação financeira",
                valor_pagamento=delta_pagamento,
                data_pagamento=data_pagamento,
                observacao=observacao or "",
                criado_por=usuario,
                atualizado_por=usuario,
            )
            pagamento.save()

        if baixar_saldo and valor_realizado < quantizar_moeda(custo_extra.valor_previsto):
            if not custo_extra.quitado:
                aplicar_baixa_custo_extra(custo_extra, motivo_baixa, usuario)

        custo_extra.refresh_from_db()
        return custo_extra


def liquidar_custo_servico_evento(source_id, tipo, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_pago",
    )
    data_pagamento = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    descricao_pagamento = obter_texto(
        payload,
        "paymentDescription",
        "descricaoPagamento",
        "descricao_pagamento",
    )
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")
    motivo_baixa = obter_texto(payload, "writeOffReason", "motivoBaixa", "motivo_baixa")
    config_tipo = TIPOS_CUSTO_SERVICO[tipo]

    with transaction.atomic():
        try:
            custo_servico = (
                select_for_update_self(EventoCustoServico.objects.all())
                .select_related(
                    "evento",
                    "evento__cliente",
                    "evento__orcamento",
                    "servico",
                )
                .get(pk=source_id)
            )
        except (TypeError, ValueError, EventoCustoServico.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            custo_servico,
            operation="settle_event_service_cost",
        )

        total_atual = quantizar_moeda(getattr(custo_servico, config_tipo["pago"]))
        validar_custo_servico_evento_para_baixa(
            custo_servico,
            tipo,
            valor_realizado,
            total_atual,
            data_pagamento,
            baixar_saldo,
            motivo_baixa,
        )

        delta_pagamento = quantizar_moeda(valor_realizado - total_atual)
        if delta_pagamento > ZERO:
            pagamento = PagamentoEventoCustoServico(
                custo_servico=custo_servico,
                tipo=tipo,
                descricao=(
                    descricao_pagamento
                    or f"Baixa de obrigação financeira - {config_tipo['rotulo']}"
                ),
                valor_pagamento=delta_pagamento,
                data_pagamento=data_pagamento,
                observacao=observacao or "",
                criado_por=usuario,
                atualizado_por=usuario,
            )
            pagamento.save()

        valor_previsto = quantizar_moeda(getattr(custo_servico, config_tipo["previsto"]))
        if baixar_saldo and valor_realizado < valor_previsto:
            if not getattr(custo_servico, config_tipo["quitado"]):
                aplicar_baixa_custo_servico(custo_servico, tipo, motivo_baixa, usuario)

        custo_servico.refresh_from_db()
        return custo_servico


def liquidar_parcela_divida_fcf(source_id, payload, usuario):
    valor_realizado = obter_decimal_obrigatorio(
        payload,
        "realizedAmount",
        "valorRealizado",
        "valor_realizado",
        "paidAmount",
        "valor_pago",
    )
    data_pagamento = obter_data_opcional(
        payload,
        "paymentDate",
        "dataPagamento",
        "data_pagamento",
    )
    forma_pagamento = obter_texto(payload, "paymentMethod", "formaPagamento", "forma_pagamento")
    observacao = obter_texto(payload, "notes", "observacao")
    baixar_saldo = obter_booleano(payload, "settleRemainingBalance", "baixarSaldo", "baixar_saldo")
    motivo_baixa = obter_texto(payload, "writeOffReason", "motivoBaixa", "motivo_baixa")

    with transaction.atomic():
        try:
            parcela = (
                select_for_update_self(ParcelaDivida.objects.all())
                .select_related(
                    "divida",
                    "divida__evento",
                    "divida__evento__cliente",
                    "divida__evento__orcamento",
                )
                .get(pk=source_id)
            )
        except (TypeError, ValueError, ParcelaDivida.DoesNotExist) as exc:
            raise ObrigacaoFinanceiraNaoEncontrada(
                {"sourceId": "Obrigação financeira não encontrada."}
            ) from exc

        assert_demo_write_allowed(
            usuario,
            parcela,
            operation="settle_debt_installment",
        )

        aplicar_ajustes_parcela_divida(parcela, payload, usuario)
        total_atual = quantizar_moeda(parcela.valor_pago)
        validar_parcela_divida_fcf_para_baixa(
            parcela,
            valor_realizado,
            total_atual,
            data_pagamento,
            baixar_saldo,
            motivo_baixa,
        )

        delta_pagamento = quantizar_moeda(valor_realizado - total_atual)
        if delta_pagamento > ZERO:
            pagamento = PagamentoParcelaDivida(
                parcela=parcela,
                data_pagamento=data_pagamento,
                valor_pagamento=delta_pagamento,
                forma_pagamento=forma_pagamento or "",
                observacao=observacao or "",
                criado_por=usuario,
                atualizado_por=usuario,
            )
            pagamento.save()

        parcela.refresh_from_db()
        if baixar_saldo and valor_realizado < quantizar_moeda(parcela.valor_total_devido):
            parcela.baixado_manualmente = True
            parcela.motivo_baixa = montar_motivo_baixa_parcela(
                parcela.motivo_baixa,
                motivo_baixa,
            )
            parcela.atualizado_por = usuario
            parcela.save(
                update_fields=[
                    "baixado_manualmente",
                    "motivo_baixa",
                    "status",
                    "atualizado_por",
                    "atualizado_em",
                ],
                sincronizacao_pagamento=True,
            )

        parcela.refresh_from_db()
        return parcela


def validar_despesa_operacional_manual_para_baixa(
    despesa,
    valor_realizado,
    data_pagamento,
    baixar_saldo,
    motivo_baixa,
):
    valor_atual = quantizar_moeda(despesa.valor_pago)
    valor_previsto = quantizar_moeda(despesa.valor_previsto)

    if despesa.origem != DespesaOperacional.ORIGEM_MANUAL:
        raise ValidationError(
            {
                "source": (
                    "Somente despesas operacionais manuais suportam baixa nativa "
                    "neste endpoint inicial."
                )
            }
        )

    if despesa.status == "cancelado":
        raise ValidationError({"status": "Obrigação cancelada não pode ser liquidada."})

    if valor_realizado > ZERO and not data_pagamento:
        raise ValidationError({"paymentDate": "Informe a data do pagamento."})

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_pagamento if valor_realizado > valor_atual else None,
        baixar_saldo,
        motivo_baixa,
    )


def validar_custo_fixo_para_baixa(
    custo_fixo,
    valor_realizado,
    data_pagamento,
    baixar_saldo,
    motivo_baixa,
):
    valor_atual = quantizar_moeda(custo_fixo.valor_pago)
    valor_previsto = quantizar_moeda(custo_fixo.valor_previsto)

    if custo_fixo.status == "cancelado":
        raise ValidationError({"status": "Custo fixo cancelado não pode ser liquidado."})

    if valor_realizado > ZERO and not data_pagamento:
        raise ValidationError({"paymentDate": "Informe a data do pagamento."})

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_pagamento if valor_realizado > valor_atual else None,
        baixar_saldo,
        motivo_baixa,
    )


def validar_investimento_fci_para_baixa(
    investimento,
    valor_realizado,
    data_realizacao,
    baixar_saldo,
    motivo_baixa,
):
    valor_atual = quantizar_moeda(investimento.valor_realizado)
    valor_previsto = quantizar_moeda(investimento.valor_previsto)

    if investimento.tipo_fluxo != TIPO_FLUXO_SAIDA:
        raise ValidationError(
            {"source": "Somente investimentos de saída podem ser liquidados como obrigação."}
        )

    if investimento.status == STATUS_CANCELADO:
        raise ValidationError({"status": "Investimento cancelado não pode ser liquidado."})

    if valor_realizado > ZERO and not data_realizacao:
        raise ValidationError({"paymentDate": "Informe a data da realização."})

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_realizacao if valor_realizado > valor_atual else None,
        baixar_saldo,
        motivo_baixa,
    )


def validar_financiamento_fcf_para_baixa(
    financiamento,
    valor_realizado,
    data_realizacao,
    baixar_saldo,
):
    valor_atual = quantizar_moeda(financiamento.valor_realizado)
    valor_previsto = quantizar_moeda(financiamento.valor_previsto)

    if financiamento.tipo_fluxo != TIPO_FLUXO_SAIDA:
        raise ValidationError(
            {"source": "Somente movimentações FCF de saída podem ser liquidadas como obrigação."}
        )

    if financiamento.status == STATUS_CANCELADO:
        raise ValidationError({"status": "Movimentação FCF cancelada não pode ser liquidada."})

    if valor_realizado > ZERO and not data_realizacao:
        raise ValidationError({"paymentDate": "Informe a data da realização."})

    if baixar_saldo and valor_realizado < valor_previsto:
        raise ValidationError(
            {
                "settleRemainingBalance": (
                    "Movimentação FCF não suporta baixa do saldo restante. "
                    "Ajuste o valor realizado ou use o fluxo especializado."
                )
            }
        )

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_realizacao if valor_realizado > valor_atual else None,
        False,
        "",
    )


def validar_custo_extra_evento_para_baixa(
    custo_extra,
    valor_realizado,
    valor_atual,
    data_pagamento,
    baixar_saldo,
    motivo_baixa,
):
    valor_previsto = quantizar_moeda(custo_extra.valor_previsto)

    if custo_extra.quitado and valor_realizado > valor_atual:
        raise ValidationError({"status": "Custo extra já foi baixado manualmente."})

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_pagamento if valor_realizado > valor_atual else None,
        baixar_saldo,
        motivo_baixa,
    )


def validar_custo_servico_evento_para_baixa(
    custo_servico,
    tipo,
    valor_realizado,
    valor_atual,
    data_pagamento,
    baixar_saldo,
    motivo_baixa,
):
    config_tipo = TIPOS_CUSTO_SERVICO[tipo]
    valor_previsto = quantizar_moeda(getattr(custo_servico, config_tipo["previsto"]))

    if getattr(custo_servico, config_tipo["quitado"]) and valor_realizado > valor_atual:
        raise ValidationError({"status": "Tipo de custo de serviço já foi baixado manualmente."})

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_pagamento if valor_realizado > valor_atual else None,
        baixar_saldo,
        motivo_baixa,
    )


def validar_parcela_divida_fcf_para_baixa(
    parcela,
    valor_realizado,
    valor_atual,
    data_pagamento,
    baixar_saldo,
    motivo_baixa,
):
    valor_previsto = quantizar_moeda(parcela.valor_total_devido)

    if parcela.status == STATUS_PARCELA_CANCELADA:
        raise ValidationError({"status": "Parcela cancelada não pode ser liquidada."})

    if parcela.baixado_manualmente and valor_realizado > valor_atual:
        raise ValidationError({"status": "Parcela já foi baixada manualmente."})

    if parcela.status == STATUS_PARCELA_PAGA and valor_realizado > valor_atual:
        raise ValidationError({"status": "Parcela já foi paga."})

    validar_valores_baixa_acumulada(
        valor_realizado,
        valor_atual,
        valor_previsto,
        data_pagamento if valor_realizado > valor_atual else None,
        baixar_saldo,
        motivo_baixa,
    )


def validar_valores_baixa_acumulada(
    valor_realizado,
    valor_atual,
    valor_previsto,
    data_novo_pagamento,
    baixar_saldo,
    motivo_baixa,
):
    if valor_realizado < valor_atual:
        raise ValidationError(
            {
                "realizedAmount": (
                    "O valor realizado acumulado não pode ser menor que o valor já registrado."
                )
            }
        )

    if valor_realizado > valor_previsto:
        raise ValidationError(
            {"realizedAmount": "O valor realizado acumulado não pode superar o previsto."}
        )

    if data_novo_pagamento is None and valor_realizado > valor_atual:
        raise ValidationError({"paymentDate": "Informe a data do pagamento."})

    if baixar_saldo and valor_realizado < valor_previsto and not motivo_baixa:
        raise ValidationError(
            {"writeOffReason": "Informe o motivo para baixar o saldo restante."}
        )


def serializar_obrigacao_por_origem(source, source_id, source_detail="", usuario=None):
    permissoes_action_hints = permissoes_action_hints_obrigacoes(usuario)

    for item in listar_obrigacoes_financeiras({"source": source}):
        if item["source"] != source or item["source_id"] != source_id:
            continue

        if source_detail and item["source_detail"] != source_detail:
            continue

        return serializar_obrigacao_financeira(
            item,
            permissoes_action_hints=permissoes_action_hints,
        )

    raise ObrigacaoFinanceiraNaoEncontrada(
        {"sourceId": "Obrigação financeira não encontrada após a baixa."}
    )


def serializar_contexto_baixa_canonica(
    item,
    write_model_source=CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
):
    chave_obrigacao = montar_chave_obrigacao_canonica_item(item)
    obrigacao = (
        ObrigacaoFinanceira.objects.filter(chave_origem=chave_obrigacao)
        .select_related("cliente", "evento", "evento__orcamento")
        .first()
    )

    if not obrigacao:
        return {
            "available": False,
            "synced": False,
            "writeModelSource": write_model_source,
            "obligationKey": chave_obrigacao,
            "obligationId": None,
            "settlementCount": 0,
            "allocationCount": 0,
            "allocatedAmount": 0.0,
            "latestSettlement": None,
            "reason": "canonical_obligation_missing",
        }

    alocacoes = list(
        BaixaFinanceiraAlocacao.objects.select_related(
            "baixa",
            "baixa__lancamento_financeiro",
        )
        .filter(obrigacao=obrigacao)
        .order_by("-baixa__data_baixa", "-baixa__id")
    )
    valor_alocado = quantizar_moeda(
        sum((alocacao.valor_alocado for alocacao in alocacoes), ZERO)
    )
    valor_realizado = quantizar_moeda(
        Decimal(str(item.get("realizedAmount") or item.get("paidAmount") or 0))
    )

    return {
        "available": True,
        "synced": valor_alocado == valor_realizado,
        "writeModelSource": write_model_source,
        "obligationKey": obrigacao.chave_origem,
        "obligationId": obrigacao.id,
        "settlementModel": "BaixaFinanceira",
        "allocationModel": "BaixaFinanceiraAlocacao",
        "settlementCount": len(alocacoes),
        "allocationCount": len(alocacoes),
        "allocatedAmount": decimal_para_numero(valor_alocado),
        "realizedAmount": decimal_para_numero(valor_realizado),
        "pendingAmount": decimal_para_numero(obrigacao.valor_pendente),
        "latestSettlement": (
            serializar_baixa_canonica(alocacoes[0].baixa)
            if alocacoes
            else None
        ),
        "reason": "",
    }


def montar_chave_obrigacao_canonica_item(item):
    source = item.get("source") or item.get("origin") or item.get("origem") or ""
    source_id = item.get("sourceId") or item.get("originId") or item.get("source_id")
    source_detail = (
        item.get("sourceDetail")
        or item.get("source_detail")
        or item.get("detalheOrigem")
        or ""
    )

    if source == ORIGEM_CUSTO_SERVICO:
        return f"{source}:{source_id}:{source_detail}"
    return f"{source}:{source_id}"


def serializar_baixa_canonica(baixa):
    settlement_amount = decimal_para_numero(baixa.valor_total)
    return {
        "id": baixa.id,
        "key": baixa.chave_origem,
        "amount": settlement_amount,
        "settlementAmount": settlement_amount,
        "date": baixa.data_baixa.isoformat() if baixa.data_baixa else "",
        "settlementDate": baixa.data_baixa.isoformat() if baixa.data_baixa else "",
        "type": baixa.tipo,
        "cashFlowGroup": baixa.fluxo,
        "nature": baixa.natureza,
        "description": baixa.descricao,
        "settlementDescription": baixa.descricao,
        "status": baixa.status,
        "writeModelSource": baixa.fonte_escrita,
        "ledgerEntryId": baixa.lancamento_financeiro_id,
    }


def aplicar_ajustes_parcela_divida(parcela, payload, usuario):
    valor_juros = obter_decimal_opcional(
        payload,
        "interestAmount",
        "valorJuros",
        "valor_juros",
        "juros",
    )
    valor_multa = obter_decimal_opcional(
        payload,
        "fineAmount",
        "valorMulta",
        "valor_multa",
        "multa",
    )
    valor_desconto = obter_decimal_opcional(
        payload,
        "discountAmount",
        "valorDesconto",
        "valor_desconto",
        "desconto",
    )

    if valor_juros is None and valor_multa is None and valor_desconto is None:
        return

    if valor_juros is not None:
        parcela.valor_juros = valor_juros
    if valor_multa is not None:
        parcela.valor_multa = valor_multa
    if valor_desconto is not None:
        parcela.valor_desconto = valor_desconto

    if parcela.valor_total_devido < ZERO:
        raise ValidationError(
            {"discountAmount": "O desconto não pode superar o valor devido da parcela."}
        )

    parcela.atualizado_por = usuario
    parcela.save(
        update_fields=[
            "valor_juros",
            "valor_multa",
            "valor_desconto",
            "status",
            "atualizado_por",
            "atualizado_em",
        ]
    )


def obter_tipo_custo_servico(payload):
    tipo = obter_texto(
        payload,
        "sourceDetail",
        "source_detail",
        "originDetail",
        "tipo",
        "tipoCustoServico",
        "tipo_custo_servico",
        "component",
        "componente",
    )

    if not tipo:
        raise ValidationError(
            {"sourceDetail": "Informe o tipo do custo de serviço a liquidar."}
        )

    if tipo not in TIPOS_CUSTO_SERVICO:
        raise ValidationError({"sourceDetail": "Tipo de custo de serviço inválido."})

    return tipo


def obter_decimal_obrigatorio(payload, *nomes):
    valor = obter_primeiro_valor(payload, *nomes)
    if valor in (None, ""):
        raise ValidationError({nomes[0]: "Informe o valor realizado acumulado."})

    try:
        decimal = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError({nomes[0]: "Valor realizado invalido."}) from exc

    decimal = quantizar_moeda(decimal)
    if decimal < ZERO:
        raise ValidationError({nomes[0]: "O valor realizado não pode ser negativo."})

    return decimal


def obter_decimal_opcional(payload, *nomes):
    valor = obter_primeiro_valor(payload, *nomes)
    if valor in (None, ""):
        return None

    try:
        decimal = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError({nomes[0]: "Valor invalido."}) from exc

    decimal = quantizar_moeda(decimal)
    if decimal < ZERO:
        raise ValidationError({nomes[0]: "O valor não pode ser negativo."})

    return decimal


def obter_data_opcional(payload, *nomes):
    valor = obter_primeiro_valor(payload, *nomes)
    if not valor:
        return None

    try:
        return date.fromisoformat(str(valor))
    except ValueError as exc:
        raise ValidationError({nomes[0]: "Data de pagamento invalida."}) from exc


def obter_texto(payload, *nomes):
    valor = obter_primeiro_valor(payload, *nomes)
    if valor is None:
        return None
    return str(valor).strip()


def obter_booleano(payload, *nomes):
    valor = obter_primeiro_valor(payload, *nomes)
    if isinstance(valor, bool):
        return valor

    return str(valor or "").strip().lower() in {"1", "true", "sim", "yes", "on"}


def obter_primeiro_valor(payload, *nomes):
    for nome in nomes:
        if nome in payload:
            return payload[nome]
    return None
