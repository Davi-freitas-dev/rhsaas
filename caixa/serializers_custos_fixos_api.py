"""Contrato OpenAPI concreto das rotas legadas de custos fixos."""

from rest_framework import serializers


class FixedCostPayloadSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=150)
    category = serializers.CharField(max_length=30, required=False)
    plannedAmount = serializers.DecimalField(max_digits=12, decimal_places=2)
    paidAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default="0.00",
    )
    dueDate = serializers.DateField()
    paymentDate = serializers.DateField(required=False, allow_null=True)
    status = serializers.CharField(max_length=20, required=False)
    manuallySettled = serializers.BooleanField(required=False)
    settlementReason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    isActive = serializers.BooleanField(required=False)
    isRecurring = serializers.BooleanField(required=False)
    monthsCount = serializers.IntegerField(min_value=1, required=False)
    openEnded = serializers.BooleanField(required=False)
    # Obrigatório quando isRecurring=true; condicional para manter compatibilidade
    # com custos avulsos já suportados pela rota legada.
    authorizedMaterializationDate = serializers.DateField(required=False)


class FixedCostItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    categoryLabel = serializers.CharField()
    plannedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    paidAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    pendingPaymentAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    dueDate = serializers.CharField()
    paymentDate = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    statusLabel = serializers.CharField()
    manuallySettled = serializers.BooleanField()
    settlementReason = serializers.CharField(allow_blank=True)
    notes = serializers.CharField(allow_blank=True)
    isActive = serializers.BooleanField()
    isRecurring = serializers.BooleanField()
    monthsCount = serializers.IntegerField()
    parentId = serializers.IntegerField(allow_null=True)
    generatedAutomatically = serializers.BooleanField()
    recordType = serializers.CharField()
    recordTypeLabel = serializers.CharField()
    kind = serializers.CharField()
    origin = serializers.CharField()
    planId = serializers.IntegerField(allow_null=True)
    competence = serializers.CharField(allow_blank=True)
    serverId = serializers.IntegerField(allow_null=True)
    serverReferenceId = serializers.IntegerField(allow_null=True)
    source = serializers.CharField()
    projectedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    forecastAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    readOnly = serializers.BooleanField()
    canEdit = serializers.BooleanField()
    canPay = serializers.BooleanField()
    isOverdue = serializers.BooleanField()
    createdAt = serializers.CharField(allow_blank=True)
    updatedAt = serializers.CharField(allow_blank=True)
    # Presentes apenas em ocorrências materializadas; projeções não são dados seed.
    isSeed = serializers.BooleanField(required=False)
    isReadOnly = serializers.BooleanField(required=False)


class FixedCostGroupSerializer(serializers.Serializer):
    category = serializers.CharField()
    categoryLabel = serializers.CharField()
    items = FixedCostItemSerializer(many=True)
    plannedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    paidAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    pendingPaymentAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    realizedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    materializedPlannedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    projectedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    forecastAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    total = serializers.IntegerField()
    overdueCount = serializers.IntegerField()


class FixedCostSummarySerializer(serializers.Serializer):
    plannedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    paidAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    realizedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    materializedPlannedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    pendingPaymentAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    projectedAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    forecastAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    total = serializers.IntegerField()
    materializedCount = serializers.IntegerField()
    projectedCount = serializers.IntegerField()
    blockedProjectionCount = serializers.IntegerField()
    manualCount = serializers.IntegerField()
    automaticCount = serializers.IntegerField()
    overdueCount = serializers.IntegerField()


class FixedCostPermissionsSerializer(serializers.Serializer):
    canCreate = serializers.BooleanField(required=False)
    canUpdate = serializers.BooleanField()


class FixedCostListDataSerializer(serializers.Serializer):
    fixedCosts = FixedCostItemSerializer(many=True)
    projections = FixedCostItemSerializer(many=True)
    groups = FixedCostGroupSerializer(many=True)
    summary = FixedCostSummarySerializer()
    filters = serializers.JSONField()
    filterOptions = serializers.JSONField()
    permissions = FixedCostPermissionsSerializer()
    meta = serializers.JSONField()


class FixedCostListResponseSerializer(serializers.Serializer):
    data = FixedCostListDataSerializer()


class FixedCostDetailDataSerializer(serializers.Serializer):
    fixedCost = FixedCostItemSerializer()
    permissions = FixedCostPermissionsSerializer()
    meta = serializers.JSONField()


class FixedCostDetailResponseSerializer(serializers.Serializer):
    data = FixedCostDetailDataSerializer()


class FixedCostMutationDataSerializer(serializers.Serializer):
    fixedCost = FixedCostItemSerializer(allow_null=True)
    recurringPlan = serializers.JSONField(required=False, allow_null=True)
    materialization = serializers.JSONField(required=False, allow_null=True)
    message = serializers.CharField()


class FixedCostMutationResponseSerializer(serializers.Serializer):
    data = FixedCostMutationDataSerializer()
