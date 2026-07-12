import logging

from django.db import transaction

from .permissions import can_approve_budget, current_schema_name


logger = logging.getLogger(__name__)


def criar_orcamento_com_itens(form, formset, custos_extras_formset=None):
    with transaction.atomic():
        orcamento = form.save()
        formset.instance = orcamento
        formset.save()
        if custos_extras_formset is not None:
            custos_extras_formset.instance = orcamento
            custos_extras_formset.save()

    return orcamento


def aprovar_orcamento(orcamento, user):
    if not can_approve_budget(user):
        return {
            "ok": False,
            "codigo": "permission_denied",
            "mensagem": "Você não possui permissão para aprovar orçamentos.",
            "evento": None,
        }

    try:
        evento = orcamento.aprovar_e_gerar_evento()
    except Exception:
        logger.exception(
            "budget_approval_failed budget_id=%s schema=%s user_id=%s stage=approval_flow",
            orcamento.pk,
            current_schema_name(),
            getattr(user, "pk", None),
        )
        return {
            "ok": False,
            "codigo": "approval_failed",
            "mensagem": "Não foi possível aprovar o orçamento. Tente novamente ou contate o suporte.",
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
