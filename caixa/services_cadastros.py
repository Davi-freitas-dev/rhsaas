import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .demo_policy import assert_demo_write_allowed, is_demo_seed_object
from .models import Orcamento
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
        with transaction.atomic():
            locked_budget = (
                Orcamento.objects.select_for_update()
                .select_related("cliente", "configuracao_financeira")
                .get(pk=orcamento.pk)
            )
            assert_demo_write_allowed(
                user,
                locked_budget,
                operation="approve_budget",
            )
            if is_demo_seed_object(locked_budget):
                raise PermissionDenied(
                    "O orcamento de exemplo da demo nao pode ser aprovado."
                )
            if locked_budget.status not in {"rascunho", "enviado"}:
                raise ValidationError(
                    "Somente orcamentos em rascunho ou enviados podem ser aprovados."
                )
            evento = locked_budget.aprovar_e_gerar_evento()
    except PermissionDenied as exc:
        return {
            "ok": False,
            "codigo": "permission_denied",
            "mensagem": str(exc),
            "evento": None,
        }
    except ValidationError as exc:
        return {
            "ok": False,
            "codigo": "invalid_state",
            "mensagem": "; ".join(exc.messages),
            "evento": None,
        }
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
        "mensagem": f"Contrato {locked_budget.contrato} aprovado. Evento {evento.contrato} gerado.",
        "evento": evento,
    }


def criar_custo_extra(form, user):
    custo_extra = form.save(commit=False)
    assert_demo_write_allowed(
        user,
        custo_extra.evento,
        operation="create_event_extra_cost",
    )
    custo_extra.criado_por = user
    custo_extra.atualizado_por = user
    custo_extra.save()
    return custo_extra
