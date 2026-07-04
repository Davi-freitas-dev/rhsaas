from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum

from .forms_dividas import PagamentoParcelaDividaForm
from .models_dividas import Credor, DividaFinanceira, ParcelaDivida
from .selectors_pagamentos import queryset_parcelas_fcf_pagaveis
from .utils_forms import adicionar_erros_validacao
from .utils_financeiros import decimal_zero


def parcela_disponivel_para_pagamento(parcela):
    return parcela.disponivel_para_pagamento


def recalcular_pagamento_parcela(parcela):
    total_pago = decimal_zero(parcela.pagamentos.aggregate(
        total=Sum("valor_pagamento")
    )["total"])

    parcela.valor_pago = parcela.arredondar2(total_pago)
    parcela.save(sincronizacao_pagamento=True)


def recalcular_pagamento_parcelas(parcelas):
    for parcela in parcelas:
        recalcular_pagamento_parcela(parcela)


def recalcular_pagamento_parcelas_por_ids(parcelas_ids):
    parcelas = ParcelaDivida.objects.filter(id__in=parcelas_ids)
    recalcular_pagamento_parcelas(parcelas)


def prorrogar_parcelas_pendentes(parcelas, usuario):
    quantidade = 0

    for parcela in parcelas:
        if not parcela_disponivel_para_pagamento(parcela):
            continue

        parcela.prorrogar_para_mes_seguinte(
            usuario=usuario,
            juros=Decimal("0.00"),
            multa=Decimal("0.00"),
        )
        quantidade += 1

    return quantidade


def prorrogar_parcelas_em_aberto(parcelas, usuario):
    return prorrogar_parcelas_pendentes(parcelas, usuario)


def parcelas_disponiveis_para_pagamento(divida_id):
    return queryset_parcelas_fcf_pagaveis(divida_id=divida_id).order_by("numero_parcela")


def queryset_dividas_com_credor_inconsistente():
    return (
        DividaFinanceira.objects
        .select_related("credor_cadastro")
        .exclude(
            credor_cadastro__isnull=False,
            credor=F("credor_cadastro__nome"),
        )
        .order_by("id")
    )


def resumir_integridade_credores_dividas(limit=20):
    _validar_limit_relatorio(limit)
    dividas = queryset_dividas_com_credor_inconsistente()
    total = dividas.count()
    itens = [
        _acao_sincronizacao_credor_divida(divida)
        for divida in dividas[:limit]
    ]

    return {
        "checked": True,
        "consistent": total == 0,
        "totalIssues": total,
        "pendingCount": total,
        "returnedIssues": len(itens),
        "limit": limit,
        "items": itens,
    }


def sincronizar_credores_dividas_fcf(aplicar=False, limit=20):
    _validar_limit_relatorio(limit)
    dividas_ids = list(
        queryset_dividas_com_credor_inconsistente().values_list("id", flat=True)
    )
    resultado = {
        "mode": "apply" if aplicar else "dry-run",
        "readOnly": not aplicar,
        "checked": len(dividas_ids),
        "pendingCount": len(dividas_ids),
        "fixed": 0,
        "wouldFix": 0,
        "unresolved": 0,
        "items": [],
        "limit": limit,
    }

    dividas = (
        DividaFinanceira.objects
        .select_related("credor_cadastro")
        .filter(id__in=dividas_ids)
        .order_by("id")
    )
    for divida in dividas:
        acao = _acao_sincronizacao_credor_divida(divida)
        if len(resultado["items"]) < limit:
            resultado["items"].append(acao)

        if not acao["canFix"]:
            resultado["unresolved"] += 1
            continue

        if not aplicar:
            resultado["wouldFix"] += 1
            continue

        _aplicar_sincronizacao_credor_divida(divida, acao)
        resultado["fixed"] += 1

    restante = resumir_integridade_credores_dividas(limit=limit)
    resultado["remainingIssues"] = (
        restante["totalIssues"] if aplicar else len(dividas_ids)
    )
    resultado["consistentAfter"] = resultado["remainingIssues"] == 0
    return resultado


def _validar_limit_relatorio(limit):
    if limit < 0:
        raise ValueError("limit deve ser maior ou igual a 0.")


def _item_integridade_credor_divida(divida):
    credor_cadastro = divida.credor_cadastro
    issue_type = (
        "credor_cadastro_ausente"
        if credor_cadastro is None
        else "credor_textual_divergente"
    )

    return {
        "issueType": issue_type,
        "debtId": divida.id,
        "description": divida.descricao,
        "legacyCreditor": divida.credor,
        "creditorId": getattr(credor_cadastro, "id", None),
        "creditorName": getattr(credor_cadastro, "nome", ""),
    }


def _acao_sincronizacao_credor_divida(divida):
    item = _item_integridade_credor_divida(divida)
    credor_cadastro = divida.credor_cadastro

    if credor_cadastro is not None:
        return {
            **item,
            "action": "atualizar_credor_textual",
            "canFix": True,
            "targetCreditorId": credor_cadastro.id,
            "targetCreditorName": credor_cadastro.nome,
        }

    nome_credor = (divida.credor or "").strip()
    if not nome_credor:
        return {
            **item,
            "action": "corrigir_manual",
            "canFix": False,
            "reason": "Divida sem credor cadastrado e sem texto legado para vincular.",
        }

    credor_existente = (
        Credor.objects.filter(nome__iexact=nome_credor).order_by("id").first()
    )

    return {
        **item,
        "action": "vincular_credor_cadastrado",
        "canFix": True,
        "targetCreditorId": getattr(credor_existente, "id", None),
        "targetCreditorName": getattr(credor_existente, "nome", nome_credor),
        "willCreateCreditor": credor_existente is None,
    }


def _aplicar_sincronizacao_credor_divida(divida, acao):
    if acao["action"] == "atualizar_credor_textual":
        DividaFinanceira.objects.filter(pk=divida.pk).update(
            credor=acao["targetCreditorName"],
        )
        return

    if acao["action"] != "vincular_credor_cadastrado":
        return

    credor, _criado = Credor.obter_ou_criar_por_nome(
        acao["targetCreditorName"],
    )
    DividaFinanceira.objects.filter(pk=divida.pk).update(
        credor_cadastro=credor,
        credor=credor.nome,
    )


def registrar_pagamento_parcela_com_lock(form, usuario):
    form.pagamento_registrado = False
    parcela = form.parcela

    try:
        with transaction.atomic():
            parcela = ParcelaDivida.objects.select_for_update().select_related("divida").get(
                pk=form.parcela.pk,
            )

            form = PagamentoParcelaDividaForm(form.data, parcela=parcela)
            form.pagamento_registrado = False

            if not parcela_disponivel_para_pagamento(parcela):
                form.add_error(None, "Esta parcela não possui valor pendente para pagamento.")
                return form, parcela

            if not form.is_valid():
                return form, parcela

            valor_pagamento = form.cleaned_data.get("valor_pagamento") or Decimal("0.00")

            if valor_pagamento > Decimal("0.00"):
                pagamento = form.save(commit=False)
                pagamento.criado_por = usuario
                pagamento.atualizado_por = usuario
                pagamento.save()

            if form.cleaned_data.get("baixar_saldo"):
                parcela.refresh_from_db()
                parcela.baixado_manualmente = True
                parcela.motivo_baixa = montar_motivo_baixa_parcela(
                    parcela.motivo_baixa,
                    form.cleaned_data.get("motivo_baixa"),
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
    except ValidationError as erro:
        adicionar_erros_validacao(form, erro)
        return form, parcela

    form.pagamento_registrado = True
    return form, parcela


def montar_motivo_baixa_parcela(motivo_atual, motivo_baixa):
    motivo_atual = (motivo_atual or "").strip()
    motivo_novo = (motivo_baixa or "").strip()

    if not motivo_atual:
        return motivo_novo

    if motivo_novo in motivo_atual.split("; "):
        return motivo_atual

    return f"{motivo_atual}; {motivo_novo}"
