from decimal import Decimal

from rest_framework import serializers


class RecurringPlanSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    category = serializers.CharField()
    categoryLabel = serializers.CharField()
    origin = serializers.CharField()
    originLabel = serializers.CharField()
    frequency = serializers.ChoiceField(choices=["mensal"])
    plannedAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    startDate = serializers.DateField()
    endDate = serializers.DateField(allow_null=True)
    dueDay = serializers.IntegerField(min_value=1, max_value=31)
    authorizedMaterializationDate = serializers.DateField()
    isActive = serializers.BooleanField()
    notes = serializers.CharField(allow_blank=True)
    serverId = serializers.IntegerField(allow_null=True)
    legacyFixedCostId = serializers.IntegerField(allow_null=True)
    renewedPlanId = serializers.IntegerField(allow_null=True)
    materializedCount = serializers.IntegerField(min_value=0)
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class RecurringPlanCreateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=150)
    category = serializers.CharField(max_length=30)
    origin = serializers.ChoiceField(
        choices=["comum"],
        required=False,
        default="comum",
    )
    plannedAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    startDate = serializers.DateField()
    endDate = serializers.DateField(required=False, allow_null=True)
    dueDay = serializers.IntegerField(
        min_value=1,
        max_value=31,
    )
    authorizedMaterializationDate = serializers.DateField()
    isActive = serializers.BooleanField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    legacyFixedCostId = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )
    renewedPlanId = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )


class RecurringPlanUpdateSerializer(RecurringPlanCreateSerializer):
    description = serializers.CharField(max_length=150, required=False)
    category = serializers.CharField(max_length=30, required=False)
    plannedAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    startDate = serializers.DateField(required=False)
    dueDay = serializers.IntegerField(
        min_value=1,
        max_value=31,
        required=False,
    )
    authorizedMaterializationDate = serializers.DateField(required=False)


class MaterializationItemResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    planId = serializers.IntegerField()
    competence = serializers.DateField()
    fixedCostId = serializers.IntegerField(
        required=False,
        allow_null=True,
    )
    reason = serializers.CharField(required=False, allow_blank=True)
    reasonLabel = serializers.CharField(required=False, allow_blank=True)
    value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )


class RecurringPlanListMetaSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=["backend"])


class RecurringPlanPermissionsSerializer(serializers.Serializer):
    canCreate = serializers.BooleanField()
    canUpdate = serializers.BooleanField()
    canMaterialize = serializers.BooleanField()


class RecurringPlanListDataSerializer(serializers.Serializer):
    recurringPlans = RecurringPlanSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    permissions = RecurringPlanPermissionsSerializer()
    meta = RecurringPlanListMetaSerializer()


class RecurringPlanListResponseSerializer(serializers.Serializer):
    data = RecurringPlanListDataSerializer()


class RecurringPlanDetailDataSerializer(serializers.Serializer):
    recurringPlan = RecurringPlanSerializer()


class RecurringPlanDetailResponseSerializer(serializers.Serializer):
    data = RecurringPlanDetailDataSerializer()


class RecurringPlanMutationDataSerializer(serializers.Serializer):
    recurringPlan = RecurringPlanSerializer()
    materialization = MaterializationItemResultSerializer(
        required=False,
        allow_null=True,
    )
    message = serializers.CharField()


class RecurringPlanMutationResponseSerializer(serializers.Serializer):
    data = RecurringPlanMutationDataSerializer()


class RecurringProjectionItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    planId = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=["projection"])
    description = serializers.CharField()
    category = serializers.CharField()
    categoryLabel = serializers.CharField()
    origin = serializers.CharField()
    competence = serializers.DateField()
    dueDate = serializers.DateField()
    status = serializers.ChoiceField(
        choices=["projected", "blocked", "materialized"]
    )
    statusLabel = serializers.CharField()
    blockedReason = serializers.CharField(allow_blank=True)
    blockedReasonLabel = serializers.CharField(allow_blank=True)
    projectedAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    forecastAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    plannedAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    paidAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    pendingPaymentAmount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    paymentDate = serializers.CharField(allow_blank=True)
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
    isOverdue = serializers.BooleanField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()
    readOnly = serializers.BooleanField()
    canEdit = serializers.BooleanField()
    canPay = serializers.BooleanField()
    serverId = serializers.IntegerField(allow_null=True)
    serverReferenceId = serializers.IntegerField(allow_null=True)
    source = serializers.ChoiceField(
        choices=["salaryHistory", "recurringPlan"]
    )
    salaryHistoryId = serializers.IntegerField(allow_null=True)


class RecurringProjectionSummarySerializer(serializers.Serializer):
    projectedAmount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    projectedCount = serializers.IntegerField(min_value=0)
    blockedCount = serializers.IntegerField(min_value=0)


class RecurringProjectionPeriodSerializer(serializers.Serializer):
    startDate = serializers.DateField()
    endDate = serializers.DateField()
    truncatedByHorizon = serializers.BooleanField()
    maximumHorizonMonths = serializers.IntegerField(min_value=1)


class RecurringProjectionDataSerializer(serializers.Serializer):
    items = RecurringProjectionItemSerializer(many=True)
    summary = RecurringProjectionSummarySerializer()
    period = RecurringProjectionPeriodSerializer()


class RecurringProjectionResponseSerializer(serializers.Serializer):
    data = RecurringProjectionDataSerializer()


class RecurringMaterializationRequestSerializer(serializers.Serializer):
    competence = serializers.DateField(required=False)
    recoverMissing = serializers.BooleanField(required=False, default=False)
    throughCompetence = serializers.DateField(required=False)
    dryRun = serializers.BooleanField(required=False, default=False)


class RecurringMaterializationSummarySerializer(serializers.Serializer):
    requested = serializers.IntegerField(min_value=0)
    created = serializers.IntegerField(min_value=0)
    wouldCreate = serializers.IntegerField(min_value=0)
    alreadyMaterialized = serializers.IntegerField(min_value=0)
    blocked = serializers.IntegerField(min_value=0)
    failed = serializers.IntegerField(min_value=0)
    notProcessed = serializers.IntegerField(min_value=0)


class RecurringMaterializationFailureSerializer(serializers.Serializer):
    code = serializers.CharField()
    planId = serializers.IntegerField(allow_null=True)
    competence = serializers.DateField(allow_null=True)


class RecurringMaterializationDataSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            "completed",
            "completed_with_blocks",
            "conflict",
            "failed",
        ]
    )
    correlationId = serializers.UUIDField()
    summary = RecurringMaterializationSummarySerializer()
    failure = RecurringMaterializationFailureSerializer(required=False)


class RecurringMaterializationResponseSerializer(serializers.Serializer):
    data = RecurringMaterializationDataSerializer()


class ApiErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    errors = serializers.JSONField(required=False)
