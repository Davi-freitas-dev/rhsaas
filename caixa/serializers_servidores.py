from decimal import Decimal

from rest_framework import serializers

from .models_servidores import Servidor


class ServidorPayloadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    documentType = serializers.ChoiceField(choices=Servidor.TIPO_DOCUMENTO_CHOICES)
    document = serializers.CharField(max_length=32)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    birthDate = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    active = serializers.BooleanField(default=True)
    linkType = serializers.ChoiceField(choices=Servidor.TIPO_VINCULO_CHOICES)
    displayAsPartner = serializers.BooleanField(
        required=False,
        help_text=(
            "Altera somente o rótulo exibido na coluna Vínculo. "
            "Não modifica o vínculo operacional."
        ),
    )
    monthlySalary = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    monthlyWorkloadHours = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("744.00"),
        required=False,
        allow_null=True,
    )
    salaryEffectiveDate = serializers.DateField(required=False)
    workloadEffectiveDate = serializers.DateField(required=False)
    contractStartDate = serializers.DateField(required=False, allow_null=True)
    contractEndDate = serializers.DateField(required=False, allow_null=True)
    salaryPaymentDay = serializers.IntegerField(
        min_value=1,
        max_value=31,
        required=False,
        allow_null=True,
    )
    salaryAutomationFromDate = serializers.DateField(required=False, allow_null=True)
    confirmSalaryAutomationActivation = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
    )
    serviceIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate(self, attrs):
        if attrs["linkType"] == Servidor.VINCULO_MENSALISTA:
            if attrs.get("monthlySalary") is None or attrs["monthlySalary"] <= 0:
                raise serializers.ValidationError(
                    {"monthlySalary": "Informe um salário mensal maior que zero."}
                )
        elif attrs.get("monthlySalary") not in (None, 0):
            raise serializers.ValidationError(
                {"monthlySalary": "Diarista não deve possuir salário mensal."}
            )
        if (
            attrs["linkType"] != Servidor.VINCULO_MENSALISTA
            and attrs.get("monthlyWorkloadHours") is not None
        ):
            raise serializers.ValidationError(
                {
                    "monthlyWorkloadHours": (
                        "Jornada mensal contratada é exclusiva de mensalistas."
                    )
                }
            )
        if (
            attrs.get("contractStartDate")
            and attrs.get("contractEndDate")
            and attrs["contractEndDate"] < attrs["contractStartDate"]
        ):
            raise serializers.ValidationError(
                {"contractEndDate": "O fim do contrato não pode ser anterior ao início."}
            )
        attrs["serviceIds"] = list(dict.fromkeys(attrs["serviceIds"]))
        return attrs

    def model_data(self):
        dados = self.validated_data
        return {
            "nome": dados["name"],
            "tipo_documento": dados["documentType"],
            "documento": dados["document"],
            "telefone": dados.get("phone", ""),
            "email": dados.get("email", ""),
            "data_nascimento": dados.get("birthDate"),
            "endereco": dados.get("address", ""),
            "observacoes": dados.get("notes", ""),
            "ativo": dados.get("active", True),
            "tipo_vinculo": dados["linkType"],
            "exibir_como_socio": dados.get("displayAsPartner", False),
            "salario_mensal": dados.get("monthlySalary"),
            "carga_horaria_mensal": dados.get("monthlyWorkloadHours"),
            "data_inicio_contrato": dados.get("contractStartDate"),
            "data_fim_contrato": dados.get("contractEndDate"),
            "dia_pagamento_salario": dados.get("salaryPaymentDay"),
            "data_autorizacao_custo_salarial": dados.get("salaryAutomationFromDate"),
        }


def serializar_servidor(servidor, *, pode_ver_salario=False, pode_ver_sensiveis=False):
    vinculos = list(servidor.vinculos_servicos.all())
    return {
        "id": servidor.id,
        "name": servidor.nome,
        "documentType": servidor.tipo_documento,
        "document": servidor.documento if pode_ver_sensiveis else servidor.documento_mascarado,
        "documentMasked": servidor.documento_mascarado,
        "phone": servidor.telefone if pode_ver_sensiveis else "",
        "email": servidor.email if pode_ver_sensiveis else "",
        "birthDate": servidor.data_nascimento.isoformat() if servidor.data_nascimento and pode_ver_sensiveis else None,
        "address": servidor.endereco if pode_ver_sensiveis else "",
        "notes": servidor.observacoes if pode_ver_sensiveis else "",
        "active": servidor.ativo,
        "linkType": servidor.tipo_vinculo,
        "linkTypeLabel": servidor.get_tipo_vinculo_display(),
        "displayAsPartner": servidor.exibir_como_socio,
        "monthlySalary": (
            f"{servidor.salario_mensal:.2f}"
            if pode_ver_salario and servidor.salario_mensal is not None
            else None
        ),
        "monthlyWorkloadHours": (
            f"{servidor.carga_horaria_mensal:.2f}"
            if pode_ver_salario and servidor.carga_horaria_mensal is not None
            else None
        ),
        "contractStartDate": (
            servidor.data_inicio_contrato.isoformat()
            if pode_ver_salario and servidor.data_inicio_contrato
            else None
        ),
        "contractEndDate": (
            servidor.data_fim_contrato.isoformat()
            if pode_ver_salario and servidor.data_fim_contrato
            else None
        ),
        "salaryPaymentDay": (
            servidor.dia_pagamento_salario if pode_ver_salario else None
        ),
        "salaryAutomationFromDate": (
            servidor.data_autorizacao_custo_salarial.isoformat()
            if pode_ver_salario and servidor.data_autorizacao_custo_salarial
            else None
        ),
        "services": [
            {
                "id": vinculo.servico_id,
                "name": vinculo.servico.nome,
                "code": vinculo.servico.codigo,
                "active": vinculo.servico.ativo,
                "linkActive": vinculo.ativo,
            }
            for vinculo in vinculos
        ],
        "eventCount": getattr(servidor, "quantidade_eventos", 0),
        "createdAt": servidor.criado_em.isoformat(),
        "updatedAt": servidor.atualizado_em.isoformat(),
    }


class ServidorServicoResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    active = serializers.BooleanField()
    linkActive = serializers.BooleanField()


class ServidorResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    documentType = serializers.ChoiceField(choices=Servidor.TIPO_DOCUMENTO_CHOICES)
    document = serializers.CharField()
    documentMasked = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.CharField()
    birthDate = serializers.DateField(allow_null=True)
    address = serializers.CharField()
    notes = serializers.CharField()
    active = serializers.BooleanField()
    linkType = serializers.ChoiceField(choices=Servidor.TIPO_VINCULO_CHOICES)
    linkTypeLabel = serializers.CharField()
    displayAsPartner = serializers.BooleanField(
        help_text=(
            "Quando verdadeiro, a interface pode exibir 'Sócio' sem alterar "
            "linkType ou qualquer regra operacional."
        )
    )
    monthlySalary = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    monthlyWorkloadHours = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        allow_null=True,
    )
    contractStartDate = serializers.DateField(allow_null=True)
    contractEndDate = serializers.DateField(allow_null=True)
    salaryPaymentDay = serializers.IntegerField(allow_null=True)
    salaryAutomationFromDate = serializers.DateField(allow_null=True)
    services = ServidorServicoResponseSerializer(many=True)
    eventCount = serializers.IntegerField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()


class ServidorMutationDataSerializer(serializers.Serializer):
    server = ServidorResponseSerializer()
    message = serializers.CharField()


class ServidorMutationResponseSerializer(serializers.Serializer):
    data = ServidorMutationDataSerializer()


class ServidoresListDataSerializer(serializers.Serializer):
    servers = ServidorResponseSerializer(many=True)
    summary = serializers.DictField()
    filters = serializers.DictField()
    filterOptions = serializers.DictField()
    permissions = serializers.DictField()
    meta = serializers.DictField()


class ServidoresListResponseSerializer(serializers.Serializer):
    data = ServidoresListDataSerializer()


class ServidorDetailDataSerializer(serializers.Serializer):
    server = ServidorResponseSerializer()
    permissions = serializers.DictField()
    filterOptions = serializers.DictField()
    meta = serializers.DictField()


class ServidorDetailResponseSerializer(serializers.Serializer):
    data = ServidorDetailDataSerializer()
