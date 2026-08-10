from rest_framework import serializers

from .models_servidores import Servidor
from .serializers_participacoes_servidores import DiaTrabalhadoResponseSerializer


ESTADOS_CUSTO_ANALITICO = [
    "calculated",
    "restricted",
    "incomplete",
    "notApplicable",
    "outOfFilter",
]

TIPOS_VINCULO_CUSTO = Servidor.TIPO_VINCULO_CHOICES
TIPOS_VINCULO_GRUPO_CUSTO = [*TIPOS_VINCULO_CUSTO, ("MIXED", "Vínculo alterado")]
BASE_FILTRO_PARTICIPACAO_HISTORICA = ["historicalParticipation"]


class CustosPorServidorQuerySerializer(serializers.Serializer):
    startDate = serializers.DateField()
    endDate = serializers.DateField()
    serverId = serializers.IntegerField(min_value=1, required=False)
    existence = serializers.ChoiceField(
        choices=["existing", "deleted"],
        required=False,
    )
    active = serializers.ChoiceField(choices=["true", "false"], required=False)
    linkType = serializers.ChoiceField(
        choices=TIPOS_VINCULO_CUSTO,
        required=False,
    )
    serviceId = serializers.IntegerField(min_value=1, required=False)
    eventId = serializers.IntegerField(min_value=1, required=False)
    manuallyEdited = serializers.ChoiceField(
        choices=["true", "false"],
        required=False,
    )

    def validate(self, attrs):
        if attrs["startDate"] > attrs["endDate"]:
            raise serializers.ValidationError(
                {"period": "A data inicial não pode ser posterior à data final."}
            )
        return attrs


class ServicoCustoServidorResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()


class ParticipacaoCustoServidorResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    eventId = serializers.IntegerField()
    eventName = serializers.CharField()
    eventNumber = serializers.CharField()
    eventDate = serializers.DateField()
    eventStatus = serializers.CharField()
    serviceId = serializers.IntegerField()
    serviceName = serializers.CharField()
    linkType = serializers.ChoiceField(choices=TIPOS_VINCULO_CUSTO)
    days = serializers.IntegerField()
    hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    workedDays = DiaTrabalhadoResponseSerializer(many=True)
    workDatesProvided = serializers.BooleanField()
    calculatedAmount = serializers.DecimalField(max_digits=12, decimal_places=2)
    finalAmount = serializers.DecimalField(max_digits=12, decimal_places=2)
    manuallyEdited = serializers.BooleanField()
    editReason = serializers.CharField()
    financialRealCost = serializers.DecimalField(max_digits=12, decimal_places=2)
    managerialAppropriation = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    managerialAppropriationCalculated = serializers.BooleanField()


class CustoSalarialServidorResponseSerializer(serializers.Serializer):
    competence = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    financialRealCost = serializers.DecimalField(max_digits=12, decimal_places=2)
    source = serializers.CharField()
    sourceType = serializers.ChoiceField(
        choices=["materializedSalaryOccurrence"]
    )


class CustoPorServidorGrupoResponseSerializer(serializers.Serializer):
    serverId = serializers.IntegerField(allow_null=True)
    serverReferenceId = serializers.IntegerField()
    serverName = serializers.CharField()
    serverDeleted = serializers.BooleanField()
    active = serializers.BooleanField()
    linkType = serializers.ChoiceField(choices=TIPOS_VINCULO_GRUPO_CUSTO)
    linkTypes = serializers.ListField(
        child=serializers.ChoiceField(choices=TIPOS_VINCULO_CUSTO)
    )
    services = ServicoCustoServidorResponseSerializer(many=True)
    participations = ParticipacaoCustoServidorResponseSerializer(many=True)
    salaryCosts = CustoSalarialServidorResponseSerializer(many=True)
    eventCount = serializers.IntegerField()
    participationCostTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    salaryCostTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        allow_null=True,
    )
    managerialAppropriationTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        allow_null=True,
    )
    totalByServer = serializers.DecimalField(max_digits=14, decimal_places=2)


class CustosPorServidorSummarySerializer(serializers.Serializer):
    serverCount = serializers.IntegerField()
    eventCount = serializers.IntegerField()
    diaristCostTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        allow_null=True,
    )
    diaristCostState = serializers.ChoiceField(choices=ESTADOS_CUSTO_ANALITICO)
    diaristCostReason = serializers.CharField(allow_blank=True)
    monthlySalaryTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        allow_null=True,
    )
    monthlySalaryState = serializers.ChoiceField(choices=ESTADOS_CUSTO_ANALITICO)
    monthlySalaryReason = serializers.CharField(allow_blank=True)
    teamCostTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        allow_null=True,
    )
    teamCostState = serializers.ChoiceField(choices=ESTADOS_CUSTO_ANALITICO)
    teamCostReason = serializers.CharField(allow_blank=True)
    totalPeriod = serializers.DecimalField(max_digits=14, decimal_places=2)
    managerialAppropriationTotal = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        allow_null=True,
    )
    managerialAppropriationCalculated = serializers.BooleanField()


class CustosPorServidorFiltersSerializer(serializers.Serializer):
    startDate = serializers.DateField()
    endDate = serializers.DateField()
    serverId = serializers.CharField()
    existence = serializers.CharField()
    active = serializers.CharField()
    linkType = serializers.CharField()
    serviceId = serializers.CharField()
    eventId = serializers.CharField()
    manuallyEdited = serializers.CharField()


class FiltroOpcaoCustoServidorSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class CustosPorServidorFilterOptionsSerializer(serializers.Serializer):
    servers = FiltroOpcaoCustoServidorSerializer(many=True)
    services = FiltroOpcaoCustoServidorSerializer(many=True)
    events = FiltroOpcaoCustoServidorSerializer(many=True)


class CustosPorServidorPermissionsSerializer(serializers.Serializer):
    canView = serializers.BooleanField()
    canViewSalary = serializers.BooleanField()
    canViewManagerialAppropriation = serializers.BooleanField()


class CustosPorServidorMetaSerializer(serializers.Serializer):
    source = serializers.CharField()
    salarySource = serializers.CharField()
    distributionSource = serializers.CharField()
    managerialAppropriationCalculated = serializers.BooleanField()
    diaristPeriodBasis = serializers.ChoiceField(choices=["eventStartDate"])
    salaryPeriodBasis = serializers.ChoiceField(choices=["dueDate"])
    salaryValueBasis = serializers.ChoiceField(
        choices=["plannedMaterializedAmount"]
    )
    salaryCoverage = serializers.ChoiceField(choices=ESTADOS_CUSTO_ANALITICO)
    serverFilterBasis = serializers.ChoiceField(
        choices=["currentIdOrHistoricalSnapshotId"]
    )
    existenceFilterBasis = serializers.ChoiceField(
        choices=["currentRegistrationExistence"]
    )
    activeFilterBasis = serializers.ChoiceField(
        choices=["currentRegistrationState"]
    )
    linkTypeFilterBasis = serializers.ChoiceField(
        choices=["historicalParticipationOrSalaryOccurrence"]
    )
    serviceFilterBasis = serializers.ChoiceField(
        choices=BASE_FILTRO_PARTICIPACAO_HISTORICA
    )
    eventFilterBasis = serializers.ChoiceField(
        choices=BASE_FILTRO_PARTICIPACAO_HISTORICA
    )
    manualEditFilterBasis = serializers.ChoiceField(
        choices=BASE_FILTRO_PARTICIPACAO_HISTORICA
    )


class CustosPorServidorDataSerializer(serializers.Serializer):
    servers = CustoPorServidorGrupoResponseSerializer(many=True)
    summary = CustosPorServidorSummarySerializer()
    filters = CustosPorServidorFiltersSerializer()
    filterOptions = CustosPorServidorFilterOptionsSerializer()
    permissions = CustosPorServidorPermissionsSerializer()
    meta = CustosPorServidorMetaSerializer()


class CustosPorServidorResponseSerializer(serializers.Serializer):
    data = CustosPorServidorDataSerializer()
