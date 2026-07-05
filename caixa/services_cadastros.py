from django.db import transaction

from .permissions import is_tenant_administrator


def criar_orcamento_com_itens(form, formset, custos_extras_formset=None):
    with transaction.atomic():
        orcamento = form.save()
        formset.instance = orcamento
        formset.save()
        if custos_extras_formset is not None:
            custos_extras_formset.instance = orcamento
            custos_extras_formset.save()

    return orcamento


def aprovar_orcamento_como_superuser(orcamento, user):
    if not is_tenant_administrator(user):
        return {
            "ok": False,
            "mensagem": "Apenas administradores do tenant podem aprovar orçamentos por esta tela.",
            "evento": None,
        }

    return aprovar_orcamento(orcamento)


def aprovar_orcamento(orcamento):
    try:
        evento = orcamento.aprovar_e_gerar_evento()
    except Exception as erro:
        return {
            "ok": False,
            "mensagem": f"Não foi possível aprovar o contrato {orcamento.contrato}: {erro}",
            "evento": None,
        }

    return {
        "ok": True,
        "mensagem": f"Contrato {orcamento.contrato} aprovado. Evento {evento.contrato} gerado/atualizado.",
        "evento": evento,
    }


def criar_custo_extra(form, user):
    custo_extra = form.save(commit=False)
    custo_extra.criado_por = user
    custo_extra.atualizado_por = user
    custo_extra.save()
    return custo_extra
