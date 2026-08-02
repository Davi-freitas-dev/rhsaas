from decimal import Decimal

from django.db.models import Q

from .models_custo_fixo import CustoFixo
from .models_servidores import ParticipacaoServidorEvento, Servidor
from .security_salarios import filtrar_ocorrencias_salariais_por_usuario
from .serializers_participacoes_servidores import serializar_dias_trabalhados
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")


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

    aplicar_salarios = not servico_id and not evento_id and not valor_editado
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
            historico = ocorrencia.historico_salarial
            referencia = (
                historico.servidor_id_snapshot
                if historico
                else ocorrencia.servidor_salario_id
            )
            if referencia is None:
                # Uma ocorrência salarial precisa manter uma referência histórica;
                # omitir uma linha corrompida é mais seguro que atribuí-la a outro
                # servidor ou expor um dado não correlacionável.
                continue
            grupos.setdefault(
                referencia,
                _novo_grupo(ocorrencia_salarial=ocorrencia),
            )
            grupo = grupos[referencia]
            grupo["salaryCosts"].append(
                {
                    "competence": ocorrencia.competencia.strftime("%Y-%m"),
                    "amount": f"{ocorrencia.valor_previsto:.2f}",
                    "financialRealCost": f"{ocorrencia.valor_previsto:.2f}",
                    "source": "MATERIALIZED_SALARY_OCCURRENCE",
                }
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
        grupo["eventCount"] = len({item["eventId"] for item in grupo["participations"]})
        grupo["participationCostTotal"] = f"{total_participacoes:.2f}"
        grupo["salaryCostTotal"] = f"{total_salarios:.2f}"
        grupo["managerialAppropriationTotal"] = "0.00"
        grupo["totalByServer"] = f"{quantizar_moeda(total_participacoes + total_salarios):.2f}"
        resultado.append(grupo)

    resultado.sort(key=lambda item: (item["serverName"].casefold(), item["serverReferenceId"]))
    total_periodo = quantizar_moeda(
        sum((Decimal(item["totalByServer"]) for item in resultado), ZERO)
    )
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
            "totalPeriod": f"{total_periodo:.2f}",
            "managerialAppropriationTotal": "0.00",
            "managerialAppropriationCalculated": False,
        },
    }
