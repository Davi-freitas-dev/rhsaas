import calendar
import logging
import random
import time
import uuid
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q
from django.utils import timezone

from .constants_financeiros import STATUS_PENDENTE
from .models_custo_fixo import (
    AuditoriaCustoRecorrente,
    CustoFixo,
    PlanoCustoRecorrente,
)
from .models_servidores import HistoricoSalarialServidor, Servidor
from .services_auditoria_recorrencias import (
    registrar_evento_auditoria_recorrente,
)
from .utils_financeiros import ZERO_DECIMAL, quantizar_moeda


logger = logging.getLogger(__name__)

SQLSTATES_TRANSITORIOS = {"40001", "40P01"}
ATRASOS_RETRY_SEGUNDOS = (0.05, 0.15, 0.45)


class ConcorrenciaRecorrenciaEsgotada(RuntimeError):
    def __init__(self, sqlstate):
        self.sqlstate = sqlstate
        super().__init__("A operação concorrente não pôde ser concluída.")


def _sqlstate_excecao(error):
    atual = error
    visitados = set()
    while atual is not None and id(atual) not in visitados:
        visitados.add(id(atual))
        sqlstate = getattr(atual, "sqlstate", None) or getattr(
            atual,
            "pgcode",
            None,
        )
        if sqlstate:
            return sqlstate
        atual = getattr(atual, "__cause__", None) or getattr(
            atual,
            "__context__",
            None,
        )
    return None


def executar_com_retry_transacional(operacao):
    for tentativa in range(1, len(ATRASOS_RETRY_SEGUNDOS) + 2):
        try:
            return operacao()
        except OperationalError as error:
            sqlstate = _sqlstate_excecao(error)
            if sqlstate not in SQLSTATES_TRANSITORIOS:
                raise
            if tentativa > len(ATRASOS_RETRY_SEGUNDOS):
                raise ConcorrenciaRecorrenciaEsgotada(sqlstate) from error
            logger.warning(
                "Repetindo operação concorrente de recorrência",
                extra={"attempt": tentativa, "sqlstate": sqlstate},
            )
            atraso = ATRASOS_RETRY_SEGUNDOS[tentativa - 1]
            time.sleep(atraso + random.uniform(0, 0.025))


MOTIVOS_BLOQUEIO = {
    "inactive": "Plano inativo.",
    "outsidePlanPeriod": "Competência fora da vigência do plano.",
    "beforeAuthorization": "Competência anterior ao corte autorizado de materialização.",
    "beforePlanCreation": "Competência anterior à criação do plano.",
    "futureCompetence": "Competência futura não pode ser materializada antecipadamente.",
    "alreadyMaterialized": "Competência já materializada.",
    "serverUnavailable": "Servidor salarial indisponível.",
    "serverInactive": "Servidor inativo.",
    "notMonthlyServer": "Servidor não possui vínculo mensalista.",
    "outsideContract": "Competência fora do contrato do servidor.",
    "partialContractMonth": "Contrato não cobre a competência inteira; rateio automático não é permitido.",
    "salaryNotFound": "Não existe histórico salarial para a competência inteira.",
    "partialSalaryPeriod": "Vigência salarial não cobre a competência inteira; rateio automático não é permitido.",
    "invalidValue": "O plano não possui valor válido para materialização.",
}


def inicio_do_mes(valor):
    return date(valor.year, valor.month, 1)


def fim_do_mes(valor):
    return date(valor.year, valor.month, calendar.monthrange(valor.year, valor.month)[1])


def adicionar_meses_competencia(valor, meses):
    indice = valor.year * 12 + valor.month - 1 + meses
    return date(indice // 12, indice % 12 + 1, 1)


def iterar_competencias(inicio, fim):
    atual = inicio_do_mes(inicio)
    limite = inicio_do_mes(fim)
    while atual <= limite:
        yield atual
        atual = adicionar_meses_competencia(atual, 1)


def data_vencimento_da_competencia(competencia, dia_vencimento):
    ultimo_dia = calendar.monthrange(competencia.year, competencia.month)[1]
    return date(competencia.year, competencia.month, min(dia_vencimento, ultimo_dia))


def horizonte_maximo_meses():
    try:
        valor = int(getattr(settings, "CUSTOS_RECORRENTES_HORIZONTE_MAXIMO_MESES", 24))
    except (TypeError, ValueError):
        valor = 24
    return max(1, min(valor, 120))


def limitar_periodo_projecao(inicio, fim):
    if fim < inicio:
        raise ValidationError({"endDate": "A data final não pode ser anterior à data inicial."})

    inicio_normalizado = inicio_do_mes(inicio)
    fim_normalizado = fim_do_mes(fim)
    limite = fim_do_mes(
        adicionar_meses_competencia(inicio_normalizado, horizonte_maximo_meses() - 1)
    )
    return inicio_normalizado, min(fim_normalizado, limite), fim_normalizado > limite


def _carregar_historicos_salariais(planos, inicio, fim):
    servidor_ids = {
        plano.servidor_id
        for plano in planos
        if plano.origem == PlanoCustoRecorrente.ORIGEM_SALARIO
        and plano.servidor_id
    }
    historicos_por_servidor = {servidor_id: [] for servidor_id in servidor_ids}
    if not servidor_ids:
        return historicos_por_servidor

    historicos = (
        HistoricoSalarialServidor.objects.filter(
            servidor_id__in=servidor_ids,
            data_inicio__lte=fim,
        )
        .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=inicio))
        .order_by("servidor_id", "-data_inicio", "-id")
    )
    for historico in historicos:
        historicos_por_servidor[historico.servidor_id].append(historico)
    return historicos_por_servidor


def _resolver_historico_salarial(
    plano,
    competencia,
    *,
    historicos_por_servidor=None,
):
    inicio = inicio_do_mes(competencia)
    fim = fim_do_mes(competencia)
    if historicos_por_servidor is None:
        historicos = list(
            HistoricoSalarialServidor.objects.filter(
                servidor_id=plano.servidor_id,
                data_inicio__lte=fim,
            )
            .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=inicio))
            .order_by("-data_inicio", "-id")
        )
    else:
        historicos = [
            historico
            for historico in historicos_por_servidor.get(plano.servidor_id, ())
            if historico.data_inicio <= fim
            and (historico.data_fim is None or historico.data_fim >= inicio)
        ]

    for historico in historicos:
        if historico.data_inicio <= inicio and (
            historico.data_fim is None or historico.data_fim >= fim
        ):
            return historico, ""
    if historicos:
        return None, "partialSalaryPeriod"
    return None, "salaryNotFound"


def avaliar_plano_na_competencia(
    plano,
    competencia,
    *,
    para_materializacao=False,
    data_referencia=None,
    historicos_por_servidor=None,
):
    competencia = inicio_do_mes(competencia)
    inicio = competencia
    fim = fim_do_mes(competencia)

    if not plano.ativo:
        return {"eligible": False, "reason": "inactive"}
    if fim < plano.data_inicio or (plano.data_fim and inicio > plano.data_fim):
        return {"eligible": False, "reason": "outsidePlanPeriod"}
    if (
        plano.criado_em
        and plano.origem != PlanoCustoRecorrente.ORIGEM_SALARIO
    ):
        data_criacao = timezone.localtime(plano.criado_em).date()
        if competencia < inicio_do_mes(data_criacao):
            return {"eligible": False, "reason": "beforePlanCreation"}
    if competencia < inicio_do_mes(plano.data_autorizacao_materializacao):
        return {"eligible": False, "reason": "beforeAuthorization"}
    if para_materializacao:
        data_referencia = data_referencia or timezone.localdate()
        if competencia > inicio_do_mes(data_referencia):
            return {"eligible": False, "reason": "futureCompetence"}
        if data_referencia < plano.data_autorizacao_materializacao:
            return {"eligible": False, "reason": "beforeAuthorization"}

    if plano.origem == PlanoCustoRecorrente.ORIGEM_SALARIO:
        servidor = plano.servidor
        if not servidor:
            return {"eligible": False, "reason": "serverUnavailable"}
        if not servidor.ativo:
            return {"eligible": False, "reason": "serverInactive"}
        if servidor.tipo_vinculo != Servidor.VINCULO_MENSALISTA:
            return {"eligible": False, "reason": "notMonthlyServer"}
        if servidor.data_inicio_contrato and fim < servidor.data_inicio_contrato:
            return {"eligible": False, "reason": "outsideContract"}
        if servidor.data_fim_contrato and inicio > servidor.data_fim_contrato:
            return {"eligible": False, "reason": "outsideContract"}
        if (
            servidor.data_inicio_contrato
            and servidor.data_inicio_contrato > inicio
        ) or (
            servidor.data_fim_contrato
            and servidor.data_fim_contrato < fim
        ):
            return {"eligible": False, "reason": "partialContractMonth"}

        historico, motivo = _resolver_historico_salarial(
            plano,
            competencia,
            historicos_por_servidor=historicos_por_servidor,
        )
        if motivo:
            return {"eligible": False, "reason": motivo}
        return {
            "eligible": True,
            "reason": "",
            "value": quantizar_moeda(historico.valor),
            "salaryHistory": historico,
        }

    if plano.valor_previsto is None or plano.valor_previsto <= ZERO_DECIMAL:
        return {"eligible": False, "reason": "invalidValue"}
    return {
        "eligible": True,
        "reason": "",
        "value": quantizar_moeda(plano.valor_previsto),
        "salaryHistory": None,
    }


def _serializar_projecao(plano, competencia, avaliacao, *, materializada=False):
    valor = avaliacao.get("value", ZERO_DECIMAL)
    bloqueada = not avaliacao["eligible"]
    status = "materialized" if materializada else ("blocked" if bloqueada else "projected")
    motivo = avaliacao.get("reason", "")
    return {
        "id": f"projection:{plano.pk}:{competencia:%Y-%m}",
        "planId": plano.pk,
        "kind": "projection",
        "description": plano.descricao,
        "category": plano.categoria,
        "categoryLabel": plano.get_categoria_display(),
        "origin": plano.origem,
        "competence": competencia.isoformat(),
        "dueDate": data_vencimento_da_competencia(
            competencia,
            plano.dia_vencimento,
        ).isoformat(),
        "status": status,
        "statusLabel": {
            "projected": "Projetado",
            "blocked": "Bloqueado",
            "materialized": "Materializado",
        }[status],
        "blockedReason": motivo,
        "blockedReasonLabel": MOTIVOS_BLOQUEIO.get(motivo, ""),
        "projectedAmount": f"{valor:.2f}",
        "forecastAmount": f"{valor:.2f}",
        "plannedAmount": "0.00",
        "paidAmount": "0.00",
        "pendingPaymentAmount": "0.00",
        "paymentDate": "",
        "manuallySettled": False,
        "settlementReason": "",
        "notes": plano.observacao,
        "isActive": plano.ativo,
        "isRecurring": True,
        "monthsCount": 1,
        "parentId": None,
        "generatedAutomatically": True,
        "recordType": "automatico",
        "recordTypeLabel": "Projeção automática",
        "isOverdue": False,
        "createdAt": plano.criado_em.isoformat(),
        "updatedAt": plano.atualizado_em.isoformat(),
        "readOnly": True,
        "canEdit": False,
        "canPay": False,
        "serverId": plano.servidor_id,
        "serverReferenceId": plano.servidor_id,
        "source": (
            "salaryHistory"
            if plano.origem == PlanoCustoRecorrente.ORIGEM_SALARIO
            else "recurringPlan"
        ),
        "salaryHistoryId": (
            avaliacao.get("salaryHistory").pk
            if avaliacao.get("salaryHistory")
            else None
        ),
    }


def projetar_custos_recorrentes(*, inicio, fim, planos=None):
    inicio, fim, truncado = limitar_periodo_projecao(inicio, fim)
    if planos is None:
        planos = PlanoCustoRecorrente.objects.filter(ativo=True)
    planos = planos.select_related("servidor").filter(
        data_inicio__lte=fim,
    ).filter(Q(data_fim__isnull=True) | Q(data_fim__gte=inicio))

    planos_lista = list(planos.order_by("descricao", "id"))
    historicos_por_servidor = _carregar_historicos_salariais(
        planos_lista,
        inicio,
        fim,
    )
    ocorrencias = {
        (plano_id, competencia)
        for plano_id, competencia in CustoFixo.objects.filter(
            plano_recorrente__in=planos_lista,
            competencia__gte=inicio,
            competencia__lte=fim,
        ).values_list("plano_recorrente_id", "competencia")
    }
    itens = []
    for plano in planos_lista:
        for competencia in iterar_competencias(inicio, fim):
            if (plano.pk, competencia) in ocorrencias:
                continue
            avaliacao = avaliar_plano_na_competencia(
                plano,
                competencia,
                historicos_por_servidor=historicos_por_servidor,
            )
            if avaliacao.get("reason") == "outsidePlanPeriod":
                continue
            itens.append(_serializar_projecao(plano, competencia, avaliacao))

    total_projetado = sum(
        (
            Decimal(item["projectedAmount"])
            for item in itens
            if item["status"] == "projected"
        ),
        ZERO_DECIMAL,
    )
    return {
        "items": itens,
        "summary": {
            "projectedAmount": f"{quantizar_moeda(total_projetado):.2f}",
            "projectedCount": sum(item["status"] == "projected" for item in itens),
            "blockedCount": sum(item["status"] == "blocked" for item in itens),
        },
        "period": {
            "startDate": inicio.isoformat(),
            "endDate": fim.isoformat(),
            "truncatedByHorizon": truncado,
            "maximumHorizonMonths": horizonte_maximo_meses(),
        },
    }


def resumir_completude_materializacao(
    *,
    inicio,
    fim,
    excluir_salarios=False,
    data_referencia=None,
):
    if not inicio or not fim:
        return {
            "assessed": False,
            "complete": False,
            "status": "notAssessed",
            "reason": "UNBOUNDED_PERIOD",
        }
    if isinstance(inicio, str):
        inicio = date.fromisoformat(inicio)
    if isinstance(fim, str):
        fim = date.fromisoformat(fim)
    inicio = inicio_do_mes(inicio)
    fim = fim_do_mes(fim)
    data_referencia = data_referencia or timezone.localdate()
    limite_atual = fim_do_mes(data_referencia)
    fim = min(fim, limite_atual)
    if fim < inicio:
        return {
            "assessed": True,
            "complete": True,
            "status": "notApplicable",
            "reason": "FUTURE_PERIOD",
            "expectedCount": 0,
            "materializedCount": 0,
            "missingCount": 0,
            "blockedCount": 0,
            "excludedSalaryData": bool(excluir_salarios),
        }

    quantidade_meses = (
        (fim.year - inicio.year) * 12 + fim.month - inicio.month + 1
    )
    if quantidade_meses > 120:
        return {
            "assessed": False,
            "complete": False,
            "status": "notAssessed",
            "reason": "PERIOD_EXCEEDS_MAXIMUM",
            "maximumMonths": 120,
            "excludedSalaryData": bool(excluir_salarios),
        }

    planos = PlanoCustoRecorrente.objects.filter(
        ativo=True,
        data_inicio__lte=fim,
    ).filter(Q(data_fim__isnull=True) | Q(data_fim__gte=inicio))
    if excluir_salarios:
        planos = planos.exclude(origem=PlanoCustoRecorrente.ORIGEM_SALARIO)
    planos_lista = list(
        planos.select_related("servidor").order_by("id")
    )
    historicos_por_servidor = _carregar_historicos_salariais(
        planos_lista,
        inicio,
        fim,
    )
    ocorrencias = {
        (plano_id, competencia)
        for plano_id, competencia in CustoFixo.objects.filter(
            plano_recorrente__in=planos_lista,
            competencia__gte=inicio,
            competencia__lte=fim,
        ).values_list("plano_recorrente_id", "competencia")
    }

    esperados = 0
    materializados = 0
    ausentes = 0
    bloqueados = 0
    for plano in planos_lista:
        for competencia in iterar_competencias(inicio, fim):
            if fim_do_mes(competencia) < plano.data_inicio or (
                plano.data_fim and competencia > plano.data_fim
            ):
                continue
            chave = (plano.pk, competencia)
            if chave in ocorrencias:
                esperados += 1
                materializados += 1
                continue
            avaliacao = avaliar_plano_na_competencia(
                plano,
                competencia,
                para_materializacao=True,
                data_referencia=data_referencia,
                historicos_por_servidor=historicos_por_servidor,
            )
            if avaliacao["eligible"]:
                esperados += 1
                ausentes += 1
            elif avaliacao.get("reason") not in {
                "outsidePlanPeriod",
                "beforeAuthorization",
                "beforePlanCreation",
                "futureCompetence",
            }:
                bloqueados += 1

    completo = ausentes == 0 and bloqueados == 0
    return {
        "assessed": True,
        "complete": completo,
        "status": "complete" if completo else "incomplete",
        "reason": (
            ""
            if completo
            else (
                "RECURRING_COSTS_NOT_MATERIALIZED"
                if ausentes
                else "RECURRING_COSTS_BLOCKED"
            )
        ),
        "periodStart": inicio.isoformat(),
        "checkedThrough": fim.isoformat(),
        "expectedCount": esperados,
        "materializedCount": materializados,
        "missingCount": ausentes,
        "blockedCount": bloqueados,
        "excludedSalaryData": bool(excluir_salarios),
    }


def _dados_ocorrencia(plano, competencia, avaliacao, usuario):
    historico = avaliacao.get("salaryHistory")
    salarial = plano.origem == PlanoCustoRecorrente.ORIGEM_SALARIO
    return {
        "descricao": (
            f"{plano.descricao} — {competencia:%m/%Y}"
            if salarial
            else plano.descricao
        ),
        "categoria": plano.categoria,
        "valor_previsto": avaliacao["value"],
        "valor_pago": ZERO_DECIMAL,
        "data_vencimento": data_vencimento_da_competencia(
            competencia,
            plano.dia_vencimento,
        ),
        "data_pagamento": None,
        "status": STATUS_PENDENTE,
        "observacao": plano.observacao,
        "ativo": True,
        "recorrente": False,
        "quantidade_meses": 1,
        "custo_pai": None,
        "gerado_automaticamente": True,
        "plano_recorrente": plano,
        "competencia": competencia,
        "origem_recorrencia": "salario" if salarial else "plano",
        "servidor_salario": plano.servidor if salarial else None,
        "historico_salarial": historico,
        "servidor_nome_snapshot": (
            historico.servidor_nome_snapshot if historico else ""
        ),
        "criado_por": usuario,
        "atualizado_por": usuario,
    }


def _materializar_plano_competencia_uma_tentativa(
    plano,
    competencia,
    *,
    usuario=None,
    dry_run=False,
):
    competencia = inicio_do_mes(competencia)
    existente = CustoFixo.objects.filter(
        plano_recorrente=plano,
        competencia=competencia,
    ).first()
    if existente:
        return {
            "status": "alreadyMaterialized",
            "planId": plano.pk,
            "competence": competencia.isoformat(),
            "fixedCostId": existente.pk,
        }

    avaliacao = avaliar_plano_na_competencia(
        plano,
        competencia,
        para_materializacao=True,
    )
    if not avaliacao["eligible"]:
        return {
            "status": "blocked",
            "planId": plano.pk,
            "competence": competencia.isoformat(),
            "reason": avaliacao["reason"],
            "reasonLabel": MOTIVOS_BLOQUEIO.get(avaliacao["reason"], ""),
        }

    if dry_run:
        return {
            "status": "wouldCreate",
            "planId": plano.pk,
            "competence": competencia.isoformat(),
            "value": f"{avaliacao['value']:.2f}",
        }

    try:
        with transaction.atomic():
            plano_bloqueado = (
                PlanoCustoRecorrente.objects.select_for_update(of=("self",))
                .select_related("servidor")
                .get(pk=plano.pk)
            )
            existente = CustoFixo.objects.filter(
                plano_recorrente=plano_bloqueado,
                competencia=competencia,
            ).first()
            if existente:
                return {
                    "status": "alreadyMaterialized",
                    "planId": plano.pk,
                    "competence": competencia.isoformat(),
                    "fixedCostId": existente.pk,
                }

            avaliacao = avaliar_plano_na_competencia(
                plano_bloqueado,
                competencia,
                para_materializacao=True,
            )
            if not avaliacao["eligible"]:
                return {
                    "status": "blocked",
                    "planId": plano.pk,
                    "competence": competencia.isoformat(),
                    "reason": avaliacao["reason"],
                    "reasonLabel": MOTIVOS_BLOQUEIO.get(avaliacao["reason"], ""),
                }

            custo = CustoFixo(**_dados_ocorrencia(
                plano_bloqueado,
                competencia,
                avaliacao,
                usuario,
            ))
            custo._history_user = usuario
            custo.full_clean()
            custo.save()
            return {
                "status": "created",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "fixedCostId": custo.pk,
                "value": f"{custo.valor_previsto:.2f}",
            }
    except IntegrityError:
        existente = CustoFixo.objects.filter(
            plano_recorrente_id=plano.pk,
            competencia=competencia,
        ).first()
        if existente:
            return {
                "status": "alreadyMaterialized",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "fixedCostId": existente.pk,
            }
        raise


def materializar_plano_competencia(
    plano,
    competencia,
    *,
    usuario=None,
    dry_run=False,
):
    return executar_com_retry_transacional(
        lambda: _materializar_plano_competencia_uma_tentativa(
            plano,
            competencia,
            usuario=usuario,
            dry_run=dry_run,
        )
    )


def _contagens_resultados(resultados, *, total_solicitado):
    contagens = {
        status: sum(resultado["status"] == status for resultado in resultados)
        for status in [
            "created",
            "wouldCreate",
            "alreadyMaterialized",
            "ignored",
            "blocked",
            "error",
        ]
    }
    contagens["notProcessed"] = max(total_solicitado - len(resultados), 0)
    return contagens


def _registrar_resultado_materializacao(
    resultado,
    *,
    origem,
    correlation_id,
    usuario,
    recuperacao=False,
):
    status_resultado = resultado["status"]
    if status_resultado == "wouldCreate":
        return
    if status_resultado == "created":
        status = AuditoriaCustoRecorrente.STATUS_SUCESSO
        codigo = (
            AuditoriaCustoRecorrente.MOTIVO_RECUPERADO
            if recuperacao
            else AuditoriaCustoRecorrente.MOTIVO_MATERIALIZADO
        )
    elif status_resultado == "alreadyMaterialized":
        status = AuditoriaCustoRecorrente.STATUS_SUCESSO
        codigo = AuditoriaCustoRecorrente.MOTIVO_JA_MATERIALIZADO
    elif status_resultado in {"blocked", "ignored"}:
        status = AuditoriaCustoRecorrente.STATUS_BLOQUEADO
        codigo = AuditoriaCustoRecorrente.MOTIVO_BLOQUEIO_DOMINIO
    elif resultado.get("reason") == "CONCURRENCY_RETRY_EXHAUSTED":
        status = AuditoriaCustoRecorrente.STATUS_CONFLITO
        codigo = AuditoriaCustoRecorrente.MOTIVO_CONCORRENCIA_ESGOTADA
    else:
        status = AuditoriaCustoRecorrente.STATUS_FALHA
        codigo = AuditoriaCustoRecorrente.MOTIVO_FALHA_INESPERADA

    registrar_evento_auditoria_recorrente(
        tipo_evento=(
            AuditoriaCustoRecorrente.TIPO_RECUPERACAO
            if recuperacao
            else AuditoriaCustoRecorrente.TIPO_MATERIALIZACAO
        ),
        origem=origem,
        plano_id=resultado.get("planId"),
        competencia=date.fromisoformat(resultado["competence"]),
        status=status,
        codigo_motivo=codigo,
        ator=usuario,
        correlation_id=correlation_id,
    )


def materializar_competencia(
    *,
    competencia=None,
    usuario=None,
    dry_run=False,
    planos=None,
    origem=AuditoriaCustoRecorrente.ORIGEM_SISTEMA,
    correlation_id=None,
):
    competencia = inicio_do_mes(competencia or timezone.localdate())
    correlation_id = uuid.UUID(str(correlation_id or uuid.uuid4()))
    if planos is None:
        planos = PlanoCustoRecorrente.objects.all()
    planos_lista = list(planos.select_related("servidor").order_by("id"))
    resultados = []
    falha = None
    status_lote = "completed"
    for plano in planos_lista:
        try:
            resultado = materializar_plano_competencia(
                plano,
                competencia,
                usuario=usuario,
                dry_run=dry_run,
            )
        except ConcorrenciaRecorrenciaEsgotada:
            resultado = {
                "status": "error",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "reason": "CONCURRENCY_RETRY_EXHAUSTED",
            }
            falha = {
                "code": "CONCURRENCY_RETRY_EXHAUSTED",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
            }
            status_lote = "conflict"
        except Exception as error:
            logger.error(
                "Falha ao materializar plano recorrente",
                extra={
                    "plan_id": plano.pk,
                    "competence": competencia.isoformat(),
                    "correlation_id": str(correlation_id),
                    "exception_class": error.__class__.__name__,
                },
            )
            resultado = {
                "status": "error",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "reason": "UNEXPECTED_MATERIALIZATION_FAILURE",
            }
            falha = {
                "code": "UNEXPECTED_MATERIALIZATION_FAILURE",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
            }
            status_lote = "failed"
        if (
            resultado["status"] == "blocked"
            and resultado.get("reason")
            in {
                "inactive",
                "outsidePlanPeriod",
                "beforeAuthorization",
                "beforePlanCreation",
                "futureCompetence",
            }
        ):
            resultado["status"] = "ignored"
        resultados.append(resultado)
        _registrar_resultado_materializacao(
            resultado,
            origem=origem,
            correlation_id=correlation_id,
            usuario=usuario,
        )
        if falha:
            break

    contagens = _contagens_resultados(
        resultados,
        total_solicitado=len(planos_lista),
    )
    if status_lote == "completed" and (
        contagens["blocked"] or contagens["ignored"]
    ):
        status_lote = "completed_with_blocks"
    return {
        "status": status_lote,
        "correlationId": str(correlation_id),
        "competence": competencia.isoformat(),
        "dryRun": dry_run,
        "counts": contagens,
        "results": resultados,
        "failure": falha,
    }


def recuperar_competencias_ausentes(
    *,
    competencia_limite=None,
    usuario=None,
    dry_run=False,
    planos=None,
    origem=AuditoriaCustoRecorrente.ORIGEM_SISTEMA,
    correlation_id=None,
):
    correlation_id = uuid.UUID(str(correlation_id or uuid.uuid4()))
    competencia_limite = inicio_do_mes(
        competencia_limite or timezone.localdate()
    )
    if competencia_limite > inicio_do_mes(timezone.localdate()):
        raise ValidationError(
            {"throughCompetence": "A competência-limite não pode ser futura."}
        )
    if planos is None:
        planos = PlanoCustoRecorrente.objects.filter(ativo=True)

    planos_lista = list(planos.select_related("servidor").order_by("id"))
    candidatos = []
    for plano in planos_lista:
        if not plano.ativo:
            continue
        limites_iniciais = [
            inicio_do_mes(plano.data_inicio),
            inicio_do_mes(plano.data_autorizacao_materializacao),
        ]
        if plano.origem != PlanoCustoRecorrente.ORIGEM_SALARIO:
            data_criacao = timezone.localtime(plano.criado_em).date()
            limites_iniciais.append(inicio_do_mes(data_criacao))
        primeira = max(limites_iniciais)
        ultima = competencia_limite
        if plano.data_fim:
            ultima = min(ultima, inicio_do_mes(plano.data_fim))
        if primeira > ultima:
            continue
        candidatos.extend(
            (plano, competencia)
            for competencia in iterar_competencias(primeira, ultima)
        )

    existentes = {}
    if candidatos:
        plano_ids = {plano.pk for plano, _ in candidatos}
        primeira_global = min(competencia for _, competencia in candidatos)
        ultima_global = max(competencia for _, competencia in candidatos)
        existentes = {
            (plano_id, competencia): custo_id
            for plano_id, competencia, custo_id in CustoFixo.objects.filter(
                plano_recorrente_id__in=plano_ids,
                competencia__gte=primeira_global,
                competencia__lte=ultima_global,
            ).values_list("plano_recorrente_id", "competencia", "id")
        }

    resultados = []
    falha = None
    status_lote = "completed"
    for plano, competencia in candidatos:
        if (plano.pk, competencia) in existentes:
            resultado = {
                "status": "alreadyMaterialized",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "fixedCostId": existentes[(plano.pk, competencia)],
            }
            resultados.append(resultado)
            _registrar_resultado_materializacao(
                resultado,
                origem=origem,
                correlation_id=correlation_id,
                usuario=usuario,
                recuperacao=True,
            )
            continue
        try:
            resultado = materializar_plano_competencia(
                plano,
                competencia,
                usuario=usuario,
                dry_run=dry_run,
            )
        except ConcorrenciaRecorrenciaEsgotada:
            resultado = {
                "status": "error",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "reason": "CONCURRENCY_RETRY_EXHAUSTED",
            }
            falha = {
                "code": "CONCURRENCY_RETRY_EXHAUSTED",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
            }
            status_lote = "conflict"
        except Exception as error:
            logger.error(
                "Falha ao recuperar competência de plano recorrente",
                extra={
                    "plan_id": plano.pk,
                    "competence": competencia.isoformat(),
                    "correlation_id": str(correlation_id),
                    "exception_class": error.__class__.__name__,
                },
            )
            resultado = {
                "status": "error",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
                "reason": "UNEXPECTED_MATERIALIZATION_FAILURE",
            }
            falha = {
                "code": "UNEXPECTED_MATERIALIZATION_FAILURE",
                "planId": plano.pk,
                "competence": competencia.isoformat(),
            }
            status_lote = "failed"
        if (
            resultado["status"] == "blocked"
            and resultado.get("reason")
            in {
                "inactive",
                "outsidePlanPeriod",
                "beforeAuthorization",
                "beforePlanCreation",
                "futureCompetence",
            }
        ):
            resultado["status"] = "ignored"
        resultados.append(resultado)
        _registrar_resultado_materializacao(
            resultado,
            origem=origem,
            correlation_id=correlation_id,
            usuario=usuario,
            recuperacao=True,
        )
        if falha:
            break

    contagens = _contagens_resultados(
        resultados,
        total_solicitado=len(candidatos),
    )
    if status_lote == "completed" and (
        contagens["blocked"] or contagens["ignored"]
    ):
        status_lote = "completed_with_blocks"
    return {
        "status": status_lote,
        "correlationId": str(correlation_id),
        "throughCompetence": competencia_limite.isoformat(),
        "dryRun": dry_run,
        "counts": contagens,
        "results": resultados,
        "failure": falha,
    }


def _validar_renovacao(plano):
    if plano.plano_renovado_id:
        anterior = PlanoCustoRecorrente.objects.select_for_update().get(
            pk=plano.plano_renovado_id
        )
        plano.plano_renovado = anterior
        if anterior.origem != plano.origem:
            raise ValidationError(
                {"renewedPlanId": "A renovação deve manter a origem do plano anterior."}
            )
        if anterior.data_fim is None:
            raise ValidationError(
                {"renewedPlanId": "Encerre o plano anterior antes de criar a renovação."}
            )
        if plano.data_inicio <= anterior.data_fim:
            raise ValidationError(
                {"startDate": "A renovação não pode sobrepor a vigência do plano anterior."}
            )

    if plano.custo_legado_referencia_id:
        referencia = CustoFixo.objects.only("id", "custo_pai_id").get(
            pk=plano.custo_legado_referencia_id
        )
        raiz_id = referencia.custo_pai_id or referencia.pk
        serie = list(
            CustoFixo.objects.select_for_update()
            .filter(Q(pk=raiz_id) | Q(custo_pai_id=raiz_id))
            .only(
                "id",
                "custo_pai_id",
                "data_vencimento",
                "origem_recorrencia",
                "categoria",
            )
            .order_by("id")
        )
        raiz = next((item for item in serie if item.pk == raiz_id), None)
        if raiz is None:
            raise ValidationError(
                {"legacyFixedCostId": "A raiz da série legada não foi encontrada."}
            )
        plano.custo_legado_referencia = raiz

        if any(
            item.origem_recorrencia == "salario" or item.categoria == "salario"
            for item in serie
        ):
            raise ValidationError(
                {"legacyFixedCostId": "Plano comum não pode renovar custo salarial."}
            )

        inicio_plano = inicio_do_mes(plano.data_inicio)
        fim_plano = inicio_do_mes(plano.data_fim) if plano.data_fim else None
        sobrepostas = [
            inicio_do_mes(item.data_vencimento)
            for item in serie
            if inicio_do_mes(item.data_vencimento) >= inicio_plano
            and (
                fim_plano is None
                or inicio_do_mes(item.data_vencimento) <= fim_plano
            )
        ]
        if sobrepostas:
            raise ValidationError(
                {
                    "legacyFixedCostId": (
                        "A renovação não pode sobrepor competências "
                        "fisicamente existentes na série legada."
                    )
                }
            )


@transaction.atomic
def criar_plano_recorrente(
    *,
    dados,
    usuario=None,
    materializar_atual=True,
    competencia_materializacao=None,
):
    plano = PlanoCustoRecorrente(**dados)
    plano.criado_por = usuario
    plano.atualizado_por = usuario
    plano._history_user = usuario
    _validar_renovacao(plano)
    plano.full_clean()
    plano.save()

    materializacao = None
    if materializar_atual:
        materializacao = materializar_plano_competencia(
            plano,
            competencia_materializacao or timezone.localdate(),
            usuario=usuario,
        )
    return plano, materializacao


@transaction.atomic
def atualizar_plano_recorrente(plano, *, dados, usuario=None):
    plano = PlanoCustoRecorrente.objects.select_for_update().get(pk=plano.pk)
    for campo, valor in dados.items():
        setattr(plano, campo, valor)
    plano.atualizado_por = usuario
    plano._history_user = usuario
    _validar_renovacao(plano)
    plano.full_clean()
    plano.save()
    return plano


@transaction.atomic
def sincronizar_plano_salarial(
    servidor,
    *,
    usuario=None,
    competencia_materializacao=None,
):
    planos = PlanoCustoRecorrente.objects.select_for_update().filter(
        servidor=servidor,
        origem=PlanoCustoRecorrente.ORIGEM_SALARIO,
    ).order_by("id")
    plano = planos.first()

    configurado = all(
        [
            servidor.tipo_vinculo == Servidor.VINCULO_MENSALISTA,
            servidor.data_inicio_contrato,
            servidor.dia_pagamento_salario,
            servidor.data_autorizacao_custo_salarial,
        ]
    )
    if not configurado:
        if plano and plano.ativo:
            plano.ativo = False
            plano.atualizado_por = usuario
            plano._history_user = usuario
            plano.save(update_fields=["ativo", "atualizado_por", "atualizado_em"])
        return None, None

    dados = {
        "descricao": f"Salário — {servidor.nome}",
        "categoria": "salario",
        "origem": PlanoCustoRecorrente.ORIGEM_SALARIO,
        "periodicidade": PlanoCustoRecorrente.PERIODICIDADE_MENSAL,
        "valor_previsto": None,
        "data_inicio": servidor.data_inicio_contrato,
        "data_fim": servidor.data_fim_contrato,
        "dia_vencimento": servidor.dia_pagamento_salario,
        "data_autorizacao_materializacao": servidor.data_autorizacao_custo_salarial,
        "ativo": servidor.ativo,
        "observacao": "Valor proveniente do histórico salarial do servidor.",
        "servidor": servidor,
    }
    if plano:
        plano = atualizar_plano_recorrente(plano, dados=dados, usuario=usuario)
        materializacao = materializar_plano_competencia(
            plano,
            competencia_materializacao or timezone.localdate(),
            usuario=usuario,
        )
        return plano, materializacao

    return criar_plano_recorrente(
        dados=dados,
        usuario=usuario,
        materializar_atual=True,
        competencia_materializacao=competencia_materializacao,
    )
