from collections import defaultdict
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from .constants_financeiros import STATUS_CANCELADO
from .models_custo_fixo import CustoFixo, PlanoCustoRecorrente
from .models_servidores import (
    HistoricoSalarialServidor,
    ParticipacaoServidorEvento,
    Servidor,
)
from .security_salarios import (
    filtrar_ocorrencias_salariais_por_usuario,
    usuario_pode_acessar_custos_salariais,
)
from .serializers_participacoes_servidores import serializar_dias_trabalhados
from .services_custos_recorrentes import (
    data_vencimento_da_competencia,
    fim_do_mes,
    inicio_do_mes,
    iterar_competencias,
)
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")
FONTE_SALARIO_CANONICA = "materializedSalaryOccurrence"
FONTE_SALARIO_LEGADA = "MATERIALIZED_SALARY_OCCURRENCE"

ESTADO_CALCULADO = "calculated"
ESTADO_RESTRITO = "restricted"
ESTADO_INCOMPLETO = "incomplete"
ESTADO_NAO_APLICAVEL = "notApplicable"
ESTADO_FORA_FILTRO = "outOfFilter"

MOTIVO_SEM_PERMISSAO_SALARIAL = "SALARY_PERMISSION_REQUIRED"
MOTIVO_EVENTO_INCOMPATIVEL = "EVENT_SCOPE_REQUIRES_MONTHLY_ALLOCATION"
MOTIVO_SERVICO_INCOMPATIVEL = "SERVICE_SCOPE_REQUIRES_MONTHLY_ALLOCATION"
MOTIVO_EDICAO_INCOMPATIVEL = "PARTICIPATION_FILTER_NOT_APPLICABLE_TO_SALARY"
MOTIVO_CONFIGURACAO_SALARIAL = "SALARY_CONFIGURATION_MISSING"
MOTIVO_OCORRENCIA_AUSENTE = "SALARY_OCCURRENCE_MISSING"
MOTIVO_OCORRENCIA_BLOQUEADA = "SALARY_OCCURRENCE_BLOCKED"
MOTIVO_SALARIO_LEGADO = "LEGACY_SALARY_UNCORRELATED"
MOTIVO_PERIODO_COBERTURA_EXCEDIDO = "SALARY_COVERAGE_PERIOD_EXCEEDS_LIMIT"


def _motivo_filtro_incompativel(*, servico_id, evento_id, valor_editado):
    if evento_id:
        return MOTIVO_EVENTO_INCOMPATIVEL
    if servico_id:
        return MOTIVO_SERVICO_INCOMPATIVEL
    if valor_editado:
        return MOTIVO_EDICAO_INCOMPATIVEL
    return ""


def _referencia_ocorrencia_salarial(ocorrencia):
    historico = ocorrencia.historico_salarial
    if historico:
        return historico.servidor_id_snapshot
    return ocorrencia.servidor_salario_id


def _ocorrencia_salarial_estruturada(ocorrencia):
    return bool(
        ocorrencia.origem_recorrencia == "salario"
        and ocorrencia.plano_recorrente_id
        and ocorrencia.competencia
        and ocorrencia.historico_salarial_id
        and _referencia_ocorrencia_salarial(ocorrencia) is not None
    )


def _servidores_mensalistas_esperados(
    *,
    data_inicial,
    data_final,
    servidor_id,
    existencia,
    ativo,
):
    if existencia == "deleted" or ativo in {"false", "0", "inativo"}:
        return []

    qs = Servidor.objects.filter(
        ativo=True,
        tipo_vinculo=Servidor.VINCULO_MENSALISTA,
        salario_mensal__gt=ZERO,
    ).order_by("id")
    if str(servidor_id).isdigit():
        qs = qs.filter(pk=int(servidor_id))

    servidores = []
    for servidor in qs:
        if (
            servidor.data_inicio_contrato
            and servidor.data_inicio_contrato > data_final
        ):
            continue
        if servidor.data_fim_contrato and servidor.data_fim_contrato < data_inicial:
            continue
        servidores.append(servidor)
    return servidores


def _historico_cobre_competencia(historicos, competencia):
    inicio = inicio_do_mes(competencia)
    fim = fim_do_mes(competencia)
    return any(
        historico.data_inicio <= inicio
        and (historico.data_fim is None or historico.data_fim >= fim)
        for historico in historicos
    )


def _analisar_cobertura_salarial(
    *,
    data_inicial,
    data_final,
    servidor_id,
    existencia,
    ativo,
    ocorrencias,
):
    for ocorrencia in ocorrencias:
        if not ocorrencia.ativo or ocorrencia.status == STATUS_CANCELADO:
            continue
        if not _ocorrencia_salarial_estruturada(ocorrencia):
            return False, MOTIVO_SALARIO_LEGADO

    quantidade_meses = (
        (data_final.year - data_inicial.year) * 12
        + data_final.month
        - data_inicial.month
        + 1
    )
    if quantidade_meses > 120:
        return False, MOTIVO_PERIODO_COBERTURA_EXCEDIDO

    servidores = _servidores_mensalistas_esperados(
        data_inicial=data_inicial,
        data_final=data_final,
        servidor_id=servidor_id,
        existencia=existencia,
        ativo=ativo,
    )
    if not servidores:
        return True, ""

    servidor_ids = [servidor.pk for servidor in servidores]
    planos_por_servidor = {
        plano.servidor_id: plano
        for plano in PlanoCustoRecorrente.objects.filter(
            servidor_id__in=servidor_ids,
            origem=PlanoCustoRecorrente.ORIGEM_SALARIO,
        ).order_by("servidor_id", "id")
    }
    historicos_por_servidor = defaultdict(list)
    for historico in HistoricoSalarialServidor.objects.filter(
        servidor_id__in=servidor_ids,
        data_inicio__lte=fim_do_mes(data_final),
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=inicio_do_mes(data_inicial))
    ).order_by("servidor_id", "data_inicio", "id"):
        historicos_por_servidor[historico.servidor_id].append(historico)

    ocorrencias_materializadas = {
        (ocorrencia.plano_recorrente_id, inicio_do_mes(ocorrencia.competencia))
        for ocorrencia in ocorrencias
        if ocorrencia.plano_recorrente_id and ocorrencia.competencia
    }
    competencia_atual = inicio_do_mes(timezone.localdate())

    for servidor in servidores:
        if not all(
            [
                servidor.data_inicio_contrato,
                servidor.dia_pagamento_salario,
                servidor.data_autorizacao_custo_salarial,
            ]
        ):
            return False, MOTIVO_CONFIGURACAO_SALARIAL

        plano = planos_por_servidor.get(servidor.pk)
        if not plano or not plano.ativo:
            return False, MOTIVO_CONFIGURACAO_SALARIAL

        for competencia in iterar_competencias(data_inicial, data_final):
            vencimento = data_vencimento_da_competencia(
                competencia,
                servidor.dia_pagamento_salario,
            )
            if not data_inicial <= vencimento <= data_final:
                continue
            if competencia > competencia_atual:
                continue
            if competencia < inicio_do_mes(
                servidor.data_autorizacao_custo_salarial
            ):
                continue

            inicio_competencia = inicio_do_mes(competencia)
            fim_competencia = fim_do_mes(competencia)
            if fim_competencia < servidor.data_inicio_contrato or (
                servidor.data_fim_contrato
                and inicio_competencia > servidor.data_fim_contrato
            ):
                continue
            if servidor.data_inicio_contrato > inicio_competencia or (
                servidor.data_fim_contrato
                and servidor.data_fim_contrato < fim_competencia
            ):
                return False, MOTIVO_OCORRENCIA_BLOQUEADA
            if fim_competencia < plano.data_inicio or (
                plano.data_fim and inicio_competencia > plano.data_fim
            ):
                return False, MOTIVO_CONFIGURACAO_SALARIAL
            if not _historico_cobre_competencia(
                historicos_por_servidor[servidor.pk],
                competencia,
            ):
                return False, MOTIVO_OCORRENCIA_BLOQUEADA
            if (plano.pk, inicio_competencia) not in ocorrencias_materializadas:
                return False, MOTIVO_OCORRENCIA_AUSENTE

    return True, ""


def _novo_grupo(participacao=None, ocorrencia_salarial=None):
    if participacao:
        servidor = participacao.servidor
        return {
            "serverId": servidor.id if servidor else None,
            "serverReferenceId": participacao.servidor_id_snapshot,
            "serverName": participacao.servidor_nome_snapshot,
            "serverDeleted": servidor is None,
            "active": bool(servidor and servidor.ativo),
            "linkType": participacao.tipo_vinculo,
            "linkTypes": {participacao.tipo_vinculo},
            "services": {},
            "participations": [],
            "salaryCosts": [],
        }
    historico = ocorrencia_salarial.historico_salarial
    servidor = ocorrencia_salarial.servidor_salario or (
        historico.servidor if historico else None
    )
    referencia = (
        historico.servidor_id_snapshot
        if historico
        else (servidor.id if servidor else None)
    )
    nome = (
        ocorrencia_salarial.servidor_nome_snapshot
        or (historico.servidor_nome_snapshot if historico else "")
        or (servidor.nome if servidor else "")
    )
    return {
        "serverId": servidor.id if servidor else None,
        "serverReferenceId": referencia,
        "serverName": nome,
        "serverDeleted": servidor is None,
        "active": bool(servidor and servidor.ativo),
        "linkType": Servidor.VINCULO_MENSALISTA,
        "linkTypes": {Servidor.VINCULO_MENSALISTA},
        "services": {},
        "participations": [],
        "salaryCosts": [],
    }


def _filtrar_participacoes(
    *,
    data_inicial,
    data_final,
    servidor_id="",
    existencia="",
    ativo="",
    tipo_vinculo="",
    servico_id="",
    evento_id="",
    valor_editado="",
):
    qs = ParticipacaoServidorEvento.objects.select_related(
        "servidor", "evento", "servico"
    ).prefetch_related("dias_trabalhados").filter(
        evento__data_inicio__range=(data_inicial, data_final)
    )
    if str(servidor_id).isdigit():
        referencia = int(servidor_id)
        qs = qs.filter(Q(servidor_id=referencia) | Q(servidor_id_snapshot=referencia))
    if existencia == "existing":
        qs = qs.filter(servidor__isnull=False)
    elif existencia == "deleted":
        qs = qs.filter(servidor__isnull=True)
    if ativo in {"true", "1", "ativo"}:
        qs = qs.filter(servidor__ativo=True)
    elif ativo in {"false", "0", "inativo"}:
        qs = qs.filter(Q(servidor__ativo=False) | Q(servidor__isnull=True))
    if tipo_vinculo in {Servidor.VINCULO_DIARISTA, Servidor.VINCULO_MENSALISTA}:
        qs = qs.filter(tipo_vinculo=tipo_vinculo)
    if str(servico_id).isdigit():
        qs = qs.filter(servico_id=int(servico_id))
    if str(evento_id).isdigit():
        qs = qs.filter(evento_id=int(evento_id))
    if valor_editado in {"true", "1"}:
        qs = qs.filter(valor_editado_manualmente=True)
    elif valor_editado in {"false", "0"}:
        qs = qs.filter(valor_editado_manualmente=False)
    return qs.order_by("servidor_nome_snapshot", "evento__data_inicio", "id")


def _filtrar_ocorrencias_salariais(
    *,
    usuario,
    data_inicial,
    data_final,
    servidor_id="",
    existencia="",
    ativo="",
    tipo_vinculo="",
):
    if tipo_vinculo == Servidor.VINCULO_DIARISTA:
        return CustoFixo.objects.none()
    qs = filtrar_ocorrencias_salariais_por_usuario(
        CustoFixo.objects.select_related(
            "servidor_salario",
            "historico_salarial__servidor",
        ).filter(data_vencimento__range=(data_inicial, data_final)),
        usuario,
    )
    if str(servidor_id).isdigit():
        referencia = int(servidor_id)
        qs = qs.filter(
            Q(servidor_salario_id=referencia)
            | Q(historico_salarial__servidor_id_snapshot=referencia)
        )
    if existencia == "existing":
        qs = qs.filter(servidor_salario__isnull=False)
    elif existencia == "deleted":
        qs = qs.filter(servidor_salario__isnull=True)
    if ativo in {"true", "1", "ativo"}:
        qs = qs.filter(servidor_salario__ativo=True)
    elif ativo in {"false", "0", "inativo"}:
        qs = qs.filter(Q(servidor_salario__ativo=False) | Q(servidor_salario__isnull=True))
    return qs.order_by("historico_salarial__servidor_id_snapshot", "competencia", "id")


def custos_por_servidor(
    *,
    data_inicial,
    data_final,
    servidor_id="",
    existencia="",
    ativo="",
    tipo_vinculo="",
    servico_id="",
    evento_id="",
    valor_editado="",
    usuario=None,
):
    grupos = {}
    pode_ver_salario = usuario_pode_acessar_custos_salariais(usuario)
    motivo_filtro_incompativel = _motivo_filtro_incompativel(
        servico_id=servico_id,
        evento_id=evento_id,
        valor_editado=valor_editado,
    )
    participacoes = _filtrar_participacoes(
        data_inicial=data_inicial,
        data_final=data_final,
        servidor_id=servidor_id,
        existencia=existencia,
        ativo=ativo,
        tipo_vinculo=tipo_vinculo,
        servico_id=servico_id,
        evento_id=evento_id,
        valor_editado=valor_editado,
    )
    for item in participacoes:
        dias_trabalhados = serializar_dias_trabalhados(item)
        chave = item.servidor_id_snapshot
        grupo = grupos.setdefault(chave, _novo_grupo(participacao=item))
        grupo["linkTypes"].add(item.tipo_vinculo)
        grupo["services"][item.servico_id] = {
            "id": item.servico_id,
            "name": item.servico_nome_snapshot,
            "code": item.servico_codigo_snapshot,
        }
        custo_real = item.valor_final if item.tipo_vinculo == Servidor.VINCULO_DIARISTA else ZERO
        grupo["participations"].append(
            {
                "id": item.id,
                "eventId": item.evento_id,
                "eventName": item.evento.nome_evento,
                "eventNumber": item.evento.numero,
                "eventDate": item.evento.data_inicio.isoformat(),
                "eventStatus": item.evento.status,
                "serviceId": item.servico_id,
                "serviceName": item.servico_nome_snapshot,
                "linkType": item.tipo_vinculo,
                "days": item.quantidade_dias,
                "hours": f"{item.quantidade_horas:.2f}",
                "workedDays": dias_trabalhados,
                "workDatesProvided": bool(dias_trabalhados),
                "calculatedAmount": f"{item.valor_calculado:.2f}",
                "finalAmount": f"{item.valor_final:.2f}",
                "manuallyEdited": item.valor_editado_manualmente,
                "editReason": item.motivo_edicao,
                "financialRealCost": f"{custo_real:.2f}",
                "managerialAppropriation": "0.00",
                "managerialAppropriationCalculated": False,
            }
        )

    ocorrencias_salariais = []
    cobertura_salarial_completa = True
    motivo_cobertura_salarial = ""
    aplicar_salarios = (
        tipo_vinculo != Servidor.VINCULO_DIARISTA
        and pode_ver_salario
        and not motivo_filtro_incompativel
    )
    if aplicar_salarios:
        ocorrencias_salariais = list(
            _filtrar_ocorrencias_salariais(
                usuario=usuario,
                data_inicial=data_inicial,
                data_final=data_final,
                servidor_id=servidor_id,
                existencia=existencia,
                ativo=ativo,
                tipo_vinculo=tipo_vinculo,
            )
        )
        for ocorrencia in ocorrencias_salariais:
            if not ocorrencia.ativo or ocorrencia.status == STATUS_CANCELADO:
                continue
            if not _ocorrencia_salarial_estruturada(ocorrencia):
                # Registros parciais nunca são associados por nome nem entram em
                # totais; a cobertura semântica informa a inconsistência.
                continue
            referencia = _referencia_ocorrencia_salarial(ocorrencia)
            grupos.setdefault(
                referencia,
                _novo_grupo(ocorrencia_salarial=ocorrencia),
            )
            grupo = grupos[referencia]
            grupo["linkTypes"].add(Servidor.VINCULO_MENSALISTA)
            grupo["salaryCosts"].append(
                {
                    "competence": ocorrencia.competencia.strftime("%Y-%m"),
                    "amount": f"{ocorrencia.valor_previsto:.2f}",
                    "financialRealCost": f"{ocorrencia.valor_previsto:.2f}",
                    "source": FONTE_SALARIO_LEGADA,
                    "sourceType": FONTE_SALARIO_CANONICA,
                }
            )
        cobertura_salarial_completa, motivo_cobertura_salarial = (
            _analisar_cobertura_salarial(
                data_inicial=data_inicial,
                data_final=data_final,
                servidor_id=servidor_id,
                existencia=existencia,
                ativo=ativo,
                ocorrencias=ocorrencias_salariais,
            )
        )

    resultado = []
    for grupo in grupos.values():
        total_participacoes = quantizar_moeda(
            sum((Decimal(item["financialRealCost"]) for item in grupo["participations"]), ZERO)
        )
        total_salarios = quantizar_moeda(
            sum((Decimal(item["financialRealCost"]) for item in grupo["salaryCosts"]), ZERO)
        )
        grupo["services"] = sorted(grupo["services"].values(), key=lambda item: item["name"])
        grupo["linkTypes"] = sorted(
            grupo["linkTypes"],
            key=lambda valor: (valor != Servidor.VINCULO_DIARISTA, valor),
        )
        grupo["linkType"] = (
            grupo["linkTypes"][0]
            if len(grupo["linkTypes"]) == 1
            else "MIXED"
        )
        grupo["eventCount"] = len({item["eventId"] for item in grupo["participations"]})
        grupo["participationCostTotal"] = f"{total_participacoes:.2f}"
        grupo["salaryCostTotal"] = (
            f"{total_salarios:.2f}" if pode_ver_salario else None
        )
        grupo["managerialAppropriationTotal"] = "0.00"
        grupo["totalByServer"] = f"{quantizar_moeda(total_participacoes + total_salarios):.2f}"
        resultado.append(grupo)

    resultado.sort(key=lambda item: (item["serverName"].casefold(), item["serverReferenceId"]))
    total_periodo = quantizar_moeda(
        sum((Decimal(item["totalByServer"]) for item in resultado), ZERO)
    )
    total_diaristas = quantizar_moeda(
        sum((Decimal(item["participationCostTotal"]) for item in resultado), ZERO)
    )
    total_salarios = quantizar_moeda(
        sum(
            (
                Decimal(item["salaryCostTotal"])
                for item in resultado
                if item["salaryCostTotal"] is not None
            ),
            ZERO,
        )
    )

    estado_diaristas = (
        ESTADO_FORA_FILTRO
        if tipo_vinculo == Servidor.VINCULO_MENSALISTA
        else ESTADO_CALCULADO
    )
    motivo_diaristas = (
        "LINK_TYPE_MONTHLY_ONLY"
        if estado_diaristas == ESTADO_FORA_FILTRO
        else ""
    )
    if tipo_vinculo == Servidor.VINCULO_DIARISTA:
        estado_salarios = ESTADO_FORA_FILTRO
        motivo_salarios = "LINK_TYPE_DAILY_ONLY"
    elif not pode_ver_salario:
        estado_salarios = ESTADO_RESTRITO
        motivo_salarios = MOTIVO_SEM_PERMISSAO_SALARIAL
    elif motivo_filtro_incompativel:
        estado_salarios = ESTADO_NAO_APLICAVEL
        motivo_salarios = motivo_filtro_incompativel
    elif not cobertura_salarial_completa:
        estado_salarios = ESTADO_INCOMPLETO
        motivo_salarios = motivo_cobertura_salarial
    else:
        estado_salarios = ESTADO_CALCULADO
        motivo_salarios = ""

    if tipo_vinculo == Servidor.VINCULO_DIARISTA:
        estado_total = ESTADO_CALCULADO
        motivo_total = ""
        total_equipe = total_diaristas
    elif estado_salarios == ESTADO_CALCULADO:
        estado_total = ESTADO_CALCULADO
        motivo_total = ""
        total_equipe = (
            total_salarios
            if tipo_vinculo == Servidor.VINCULO_MENSALISTA
            else quantizar_moeda(total_diaristas + total_salarios)
        )
    else:
        estado_total = estado_salarios
        motivo_total = motivo_salarios
        total_equipe = None

    return {
        "servers": resultado,
        "summary": {
            "serverCount": len(resultado),
            "eventCount": len(
                {
                    item["eventId"]
                    for grupo in resultado
                    for item in grupo["participations"]
                }
            ),
            "diaristCostTotal": (
                f"{total_diaristas:.2f}"
                if estado_diaristas == ESTADO_CALCULADO
                else None
            ),
            "diaristCostState": estado_diaristas,
            "diaristCostReason": motivo_diaristas,
            "monthlySalaryTotal": (
                f"{total_salarios:.2f}"
                if estado_salarios == ESTADO_CALCULADO
                else None
            ),
            "monthlySalaryState": estado_salarios,
            "monthlySalaryReason": motivo_salarios,
            "teamCostTotal": (
                f"{total_equipe:.2f}" if total_equipe is not None else None
            ),
            "teamCostState": estado_total,
            "teamCostReason": motivo_total,
            "totalPeriod": f"{total_periodo:.2f}",
            "managerialAppropriationTotal": "0.00",
            "managerialAppropriationCalculated": False,
        },
        "meta": {
            "diaristPeriodBasis": "eventStartDate",
            "salaryPeriodBasis": "dueDate",
            "salaryValueBasis": "plannedMaterializedAmount",
            "salaryCoverage": estado_salarios,
            "serverFilterBasis": "currentIdOrHistoricalSnapshotId",
            "existenceFilterBasis": "currentRegistrationExistence",
            "activeFilterBasis": "currentRegistrationState",
            "linkTypeFilterBasis": "historicalParticipationOrSalaryOccurrence",
            "serviceFilterBasis": "historicalParticipation",
            "eventFilterBasis": "historicalParticipation",
            "manualEditFilterBasis": "historicalParticipation",
        },
    }
