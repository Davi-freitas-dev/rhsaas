from django.db import transaction
from django.db.models import Q

from .models_custo_fixo import AuditoriaCustoRecorrente, PlanoCustoRecorrente
from .models_servidores import HistoricoSalarialServidor, Servidor
from .services_auditoria_recorrencias import (
    registrar_evento_auditoria_recorrente,
)
from .services_custos_recorrentes import (
    fim_do_mes,
    inicio_do_mes,
    sincronizar_plano_salarial,
)


CONFIRMACAO_ATIVACAO = "ATIVAR_MENSALISTAS"


def avaliar_mensalista_para_ativacao(servidor, *, data_corte):
    planos = list(
        PlanoCustoRecorrente.objects.filter(
            servidor_id=servidor.pk,
            origem=PlanoCustoRecorrente.ORIGEM_SALARIO,
        ).order_by("id")
    )
    if len(planos) > 1:
        return {"status": "invalid", "reason": "CONFLICTING_SALARY_PLANS"}
    if planos:
        return {
            "status": "alreadyConfigured",
            "reason": "SALARY_PLAN_ALREADY_EXISTS",
            "planId": planos[0].pk,
        }
    if servidor.tipo_vinculo != Servidor.VINCULO_MENSALISTA:
        return {"status": "invalid", "reason": "NOT_MONTHLY_SERVER"}
    if not servidor.ativo:
        return {"status": "blocked", "reason": "INACTIVE_SERVER"}
    if not servidor.data_inicio_contrato:
        return {"status": "invalid", "reason": "CONTRACT_START_NOT_CONFIGURED"}
    if not servidor.dia_pagamento_salario:
        return {"status": "invalid", "reason": "PAYMENT_DAY_NOT_CONFIGURED"}

    competencia = inicio_do_mes(data_corte)
    fim_competencia = fim_do_mes(data_corte)
    if (
        servidor.data_inicio_contrato > competencia
        or (
            servidor.data_fim_contrato
            and servidor.data_fim_contrato < fim_competencia
        )
    ):
        return {"status": "blocked", "reason": "CONTRACT_NOT_FULL_MONTH"}

    historicos = list(
        HistoricoSalarialServidor.objects.filter(
            servidor_id=servidor.pk,
            data_inicio__lte=fim_competencia,
        )
        .filter(
            Q(data_fim__isnull=True)
            | Q(data_fim__gte=competencia)
        )
        .order_by("-data_inicio", "-id")
    )
    if any(
        historico.data_inicio <= competencia
        and (
            historico.data_fim is None
            or historico.data_fim >= fim_competencia
        )
        for historico in historicos
    ):
        return {"status": "eligible", "reason": ""}
    if historicos:
        return {"status": "blocked", "reason": "SALARY_HISTORY_NOT_FULL_MONTH"}
    return {"status": "invalid", "reason": "SALARY_HISTORY_NOT_FOUND"}


@transaction.atomic
def ativar_mensalista_existente(
    servidor,
    *,
    data_corte,
    correlation_id,
    usuario=None,
):
    servidor = Servidor.objects.select_for_update().get(pk=servidor.pk)
    resultado = avaliar_mensalista_para_ativacao(
        servidor,
        data_corte=data_corte,
    )
    if resultado["status"] == "eligible":
        servidor.data_autorizacao_custo_salarial = data_corte
        servidor._history_user = usuario
        servidor.full_clean()
        campos_atualizados = [
            "data_autorizacao_custo_salarial",
            "atualizado_em",
        ]
        if usuario is not None:
            servidor.atualizado_por = usuario
            campos_atualizados.append("atualizado_por")
        servidor.save(
            update_fields=campos_atualizados
        )
        plano, materializacao = sincronizar_plano_salarial(
            servidor,
            usuario=usuario,
            competencia_materializacao=data_corte,
        )
        resultado = {
            "status": "activated",
            "reason": "SERVER_ACTIVATED",
            "planId": plano.pk,
            "materializationStatus": (
                materializacao.get("status") if materializacao else None
            ),
        }

    status_auditoria = (
        AuditoriaCustoRecorrente.STATUS_SUCESSO
        if resultado["status"] in {"activated", "alreadyConfigured"}
        else AuditoriaCustoRecorrente.STATUS_BLOQUEADO
    )
    codigo_motivo = {
        "activated": AuditoriaCustoRecorrente.MOTIVO_SERVIDOR_ATIVADO,
        "alreadyConfigured": (
            AuditoriaCustoRecorrente.MOTIVO_SERVIDOR_JA_ATIVO
        ),
    }.get(
        resultado["status"],
        AuditoriaCustoRecorrente.MOTIVO_ATIVACAO_BLOQUEADA,
    )
    registrar_evento_auditoria_recorrente(
        tipo_evento=AuditoriaCustoRecorrente.TIPO_ATIVACAO,
        origem=AuditoriaCustoRecorrente.ORIGEM_ATIVACAO,
        plano_id=resultado.get("planId"),
        competencia=inicio_do_mes(data_corte),
        status=status_auditoria,
        codigo_motivo=codigo_motivo,
        ator=usuario,
        correlation_id=correlation_id,
    )
    return resultado
