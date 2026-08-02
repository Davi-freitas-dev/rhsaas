from decimal import Decimal

from rest_framework import serializers

from .services_dimensoes_operacionais import relacao_carregada


class DiaTrabalhadoPayloadSerializer(serializers.Serializer):
    date = serializers.DateField()
    hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        allow_null=True,
        required=False,
        default=None,
    )


def _validar_datas_duplicadas(dias_trabalhados):
    datas = [item["date"] for item in dias_trabalhados]
    if len(datas) != len(set(datas)):
        raise serializers.ValidationError(
            {"workedDays": "Não é permitido informar a mesma data mais de uma vez."}
        )


class ParticipacaoCreatePayloadSerializer(serializers.Serializer):
    serverId = serializers.IntegerField(min_value=1)
    serviceId = serializers.IntegerField(min_value=1)
    workedDays = DiaTrabalhadoPayloadSerializer(many=True, allow_empty=False)
    days = serializers.IntegerField(min_value=0, required=False)
    hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
    )

    def validate(self, attrs):
        _validar_datas_duplicadas(attrs["workedDays"])
        return attrs


class ParticipacaoUpdatePayloadSerializer(serializers.Serializer):
    serviceId = serializers.IntegerField(min_value=1)
    workedDays = DiaTrabalhadoPayloadSerializer(
        many=True,
        allow_empty=False,
        required=False,
    )
    days = serializers.IntegerField(min_value=0, required=False)
    hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    finalAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    editReason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if "workedDays" in attrs:
            _validar_datas_duplicadas(attrs["workedDays"])
        else:
            if "days" not in attrs or "hours" not in attrs:
                raise serializers.ValidationError(
                    {
                        "workedDays": (
                            "Informe as datas trabalhadas ou preserve os totais "
                            "do registro histórico."
                        )
                    }
                )
            if attrs["days"] <= 0 and attrs["hours"] <= 0:
                raise serializers.ValidationError(
                    {"days": "Informe ao menos dias ou horas trabalhadas."}
                )
        if "finalAmount" in attrs and not attrs.get("editReason", "").strip():
            raise serializers.ValidationError(
                {"editReason": "Informe o motivo da edição manual."}
            )
        return attrs


class DiaTrabalhadoResponseSerializer(serializers.Serializer):
    date = serializers.DateField()
    hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )


class ParticipacaoResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    serverId = serializers.IntegerField(allow_null=True)
    serverReferenceId = serializers.IntegerField()
    serverName = serializers.CharField()
    serverDeleted = serializers.BooleanField()
    serverActive = serializers.BooleanField()
    serviceId = serializers.IntegerField()
    serviceName = serializers.CharField()
    serviceCode = serializers.CharField()
    eventId = serializers.IntegerField()
    eventName = serializers.CharField()
    eventNumber = serializers.CharField()
    eventDate = serializers.DateField()
    eventStartDate = serializers.DateField()
    eventEndDate = serializers.DateField()
    eventStatus = serializers.CharField()
    linkType = serializers.CharField()
    days = serializers.IntegerField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    workedDays = DiaTrabalhadoResponseSerializer(many=True)
    workDatesProvided = serializers.BooleanField()
    calculatedAmount = serializers.DecimalField(max_digits=12, decimal_places=2)
    finalAmount = serializers.DecimalField(max_digits=12, decimal_places=2)
    manuallyEdited = serializers.BooleanField()
    editReason = serializers.CharField()
    monthlySalaryReference = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    managerialAppropriation = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    managerialAppropriationCalculated = serializers.BooleanField()
    financialRealCost = serializers.DecimalField(max_digits=12, decimal_places=2)
    distributionRule = serializers.CharField()
    distributedServiceTotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    distributionServerCount = serializers.IntegerField()
    readOnly = serializers.BooleanField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class ParticipacaoPermissionsSerializer(serializers.Serializer):
    canView = serializers.BooleanField()
    canManage = serializers.BooleanField()
    canEditDistributedValue = serializers.BooleanField()
    canRecalculate = serializers.BooleanField()
    canViewSalary = serializers.BooleanField()
    canViewManagerialAppropriation = serializers.BooleanField()


class ParticipacaoMutationDataSerializer(serializers.Serializer):
    participation = ParticipacaoResponseSerializer()


class ParticipacaoMutationResponseSerializer(serializers.Serializer):
    data = ParticipacaoMutationDataSerializer()


class ParticipacaoDetailDataSerializer(ParticipacaoMutationDataSerializer):
    permissions = ParticipacaoPermissionsSerializer()


class ParticipacaoDetailResponseSerializer(serializers.Serializer):
    data = ParticipacaoDetailDataSerializer()


class EventoParticipacoesResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    number = serializers.CharField()
    startDate = serializers.DateField()
    endDate = serializers.DateField()
    status = serializers.CharField()
    readOnly = serializers.BooleanField()


class ServicoOpcaoParticipacaoResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()


class ServidorOpcaoParticipacaoResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    value = serializers.CharField()
    label = serializers.CharField()
    linkType = serializers.CharField()
    services = ServicoOpcaoParticipacaoResponseSerializer(many=True)


class ParticipacoesEventoDataSerializer(serializers.Serializer):
    event = EventoParticipacoesResponseSerializer()
    participations = ParticipacaoResponseSerializer(many=True)
    serverOptions = ServidorOpcaoParticipacaoResponseSerializer(many=True)
    permissions = ParticipacaoPermissionsSerializer()
    meta = serializers.DictField(child=serializers.CharField())


class ParticipacoesEventoResponseSerializer(serializers.Serializer):
    data = ParticipacoesEventoDataSerializer()


class RecalculoParticipacoesDataSerializer(serializers.Serializer):
    recalculatedGroups = serializers.IntegerField()


class RecalculoParticipacoesResponseSerializer(serializers.Serializer):
    data = RecalculoParticipacoesDataSerializer()


def serializar_dias_trabalhados(participacao):
    cache = getattr(participacao, "_prefetched_objects_cache", {})
    dias = cache.get("dias_trabalhados")
    if dias is None:
        dias = participacao.dias_trabalhados.all()
    return [
        {
            "date": item.data.isoformat(),
            "hours": (
                f"{item.quantidade_horas:.2f}"
                if item.quantidade_horas is not None
                else None
            ),
        }
        for item in dias
    ]


def serializar_participacao(
    participacao,
    *,
    pode_ver_salario=False,
    pode_ver_apropriacao=False,
):
    servidor_excluido = participacao.servidor_id is None
    mensalista = participacao.tipo_vinculo == "MENSALISTA"
    servidor = relacao_carregada(participacao, "servidor")
    evento = relacao_carregada(participacao, "evento")
    dias_trabalhados = serializar_dias_trabalhados(participacao)
    return {
        "id": participacao.id,
        "serverId": participacao.servidor_id,
        "serverReferenceId": participacao.servidor_id_snapshot,
        "serverName": participacao.servidor_nome_snapshot,
        "serverDeleted": servidor_excluido,
        "serverActive": bool(servidor and servidor.ativo),
        "serviceId": participacao.servico_id,
        "serviceName": participacao.servico_nome_snapshot,
        "serviceCode": participacao.servico_codigo_snapshot,
        "eventId": participacao.evento_id,
        "eventName": evento.nome_evento if evento else "",
        "eventNumber": evento.numero if evento else "",
        "eventDate": evento.data_inicio.isoformat() if evento else "",
        "eventStartDate": evento.data_inicio.isoformat() if evento else "",
        "eventEndDate": evento.data_fim.isoformat() if evento else "",
        "eventStatus": evento.status if evento else "",
        "linkType": participacao.tipo_vinculo,
        "days": participacao.quantidade_dias,
        "hours": f"{participacao.quantidade_horas:.2f}",
        "workedDays": dias_trabalhados,
        "workDatesProvided": bool(dias_trabalhados),
        "calculatedAmount": f"{participacao.valor_calculado:.2f}",
        "finalAmount": f"{participacao.valor_final:.2f}",
        "manuallyEdited": participacao.valor_editado_manualmente,
        "editReason": participacao.motivo_edicao,
        "monthlySalaryReference": (
            f"{participacao.salario_mensal_referencia:.2f}"
            if pode_ver_salario
            and participacao.salario_mensal_referencia is not None
            else None
        ),
        "managerialAppropriation": "0.00" if pode_ver_apropriacao else None,
        "managerialAppropriationCalculated": False,
        "financialRealCost": (
            f"{(participacao.valor_final if not mensalista else 0):.2f}"
        ),
        "distributionRule": participacao.regra_calculo_snapshot,
        "distributedServiceTotal": (
            f"{participacao.valor_total_servico_snapshot:.2f}"
        ),
        "distributionServerCount": (
            participacao.quantidade_servidores_rateio_snapshot
        ),
        "readOnly": servidor_excluido
        or bool(evento and evento.status in {"concluido", "cancelado"}),
        "createdAt": participacao.criado_em.isoformat(),
        "updatedAt": participacao.atualizado_em.isoformat(),
    }
