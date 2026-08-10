from django.core.exceptions import ValidationError
from django.http import Http404
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Servico
from .models_servidores import Servidor
from .permissions import (
    ADD_SERVER_PERMISSION,
    CHANGE_SERVER_PERMISSION,
    CHANGE_SERVER_SALARY_PERMISSION,
    DELETE_SERVER_PERMISSION,
    VIEW_SERVER_PERMISSION,
    VIEW_SERVER_SALARY_PERMISSION,
    VIEW_SERVER_SENSITIVE_DATA_PERMISSION,
)
from .selectors_servidores import filtrar_servidores, obter_servidor, resumo_servidores
from .serializers_servidores import (
    ServidorDetailResponseSerializer,
    ServidorMutationResponseSerializer,
    ServidorPayloadSerializer,
    ServidoresListResponseSerializer,
    serializar_servidor,
)
from .serializers_api import HttpApiErrorSerializer
from .services_servidores import atualizar_servidor, criar_servidor, excluir_servidor
from .views_clientes_api import JsonBodySafeSessionAuthentication


def _errors(error):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"detail": getattr(error, "messages", [str(error)])}


def _denied(detail="Permission denied."):
    return Response({"detail": detail}, status=403)


def _unauthorized():
    return Response({"detail": "Authentication credentials were not provided."}, status=401)


def _is_json(request):
    return (request.content_type or "").split(";", 1)[0].strip() == "application/json"


def _permissoes(request):
    return {
        "canView": request.user.has_perm(VIEW_SERVER_PERMISSION),
        "canCreate": request.user.has_perm(ADD_SERVER_PERMISSION),
        "canUpdate": request.user.has_perm(CHANGE_SERVER_PERMISSION),
        "canDelete": request.user.has_perm(DELETE_SERVER_PERMISSION),
        "canViewSalary": request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION),
        "canChangeSalary": request.user.has_perm(CHANGE_SERVER_SALARY_PERMISSION),
        "canViewSensitiveData": request.user.has_perm(VIEW_SERVER_SENSITIVE_DATA_PERMISSION),
    }


def _opcoes_servicos():
    return [
        {
            "id": servico.id,
            "value": str(servico.id),
            "name": servico.nome,
            "label": servico.nome,
            "code": servico.codigo,
            "active": servico.ativo,
        }
        for servico in Servico.objects.order_by("nome", "id")
    ]


def _salvar(request, servidor=None):
    if not _is_json(request):
        return Response({"detail": "Content-Type deve ser application/json."}, status=415)
    pode_alterar_salario = request.user.has_perm(CHANGE_SERVER_SALARY_PERMISSION)
    dados_entrada = request.data.copy()
    if servidor is not None and "displayAsPartner" not in dados_entrada:
        dados_entrada["displayAsPartner"] = servidor.exibir_como_socio
    if servidor is not None and not pode_alterar_salario:
        dados_entrada["monthlySalary"] = servidor.salario_mensal
        dados_entrada["monthlyWorkloadHours"] = servidor.carga_horaria_mensal
        dados_entrada.pop("salaryEffectiveDate", None)
        dados_entrada.pop("workloadEffectiveDate", None)
        dados_entrada["contractStartDate"] = servidor.data_inicio_contrato
        dados_entrada["contractEndDate"] = servidor.data_fim_contrato
        dados_entrada["salaryPaymentDay"] = servidor.dia_pagamento_salario
        dados_entrada["salaryAutomationFromDate"] = (
            servidor.data_autorizacao_custo_salarial
        )
    elif servidor is not None:
        vinculo_solicitado = dados_entrada.get("linkType", servidor.tipo_vinculo)
        campos_automacao_existentes = {
            "monthlyWorkloadHours": (
                servidor.carga_horaria_mensal
                if vinculo_solicitado == Servidor.VINCULO_MENSALISTA
                else None
            ),
            "contractStartDate": servidor.data_inicio_contrato,
            "contractEndDate": servidor.data_fim_contrato,
            "salaryPaymentDay": servidor.dia_pagamento_salario,
            "salaryAutomationFromDate": servidor.data_autorizacao_custo_salarial,
        }
        for campo, valor in campos_automacao_existentes.items():
            if campo not in dados_entrada:
                dados_entrada[campo] = valor
    serializer = ServidorPayloadSerializer(data=dados_entrada)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=400)
    automacao_anterior = (
        servidor.data_autorizacao_custo_salarial
        if servidor is not None
        else None
    )
    automacao_solicitada = serializer.validated_data.get(
        "salaryAutomationFromDate"
    )
    if (
        automacao_anterior is None
        and automacao_solicitada is not None
        and not serializer.validated_data.get(
            "confirmSalaryAutomationActivation",
            False,
        )
    ):
        return Response(
            {
                "errors": {
                    "confirmSalaryAutomationActivation": [
                        "Confirme explicitamente a primeira ativação da automação salarial."
                    ]
                }
            },
            status=400,
        )
    salario = serializer.validated_data.get("monthlySalary")
    if servidor is None and salario is not None and not pode_alterar_salario:
        return _denied("O usuário não tem permissão para alterar salário.")
    try:
        dados_model = serializer.model_data()
        if servidor is not None and not request.user.has_perm(VIEW_SERVER_SENSITIVE_DATA_PERMISSION):
            dados_model.update(
                {
                    "documento": servidor.documento,
                    "telefone": servidor.telefone,
                    "email": servidor.email,
                    "data_nascimento": servidor.data_nascimento,
                    "endereco": servidor.endereco,
                    "observacoes": servidor.observacoes,
                }
            )
        argumentos = {
            "dados": dados_model,
            "servicos_ids": serializer.validated_data["serviceIds"],
            "usuario": request.user,
            "data_vigencia_salario": serializer.validated_data.get("salaryEffectiveDate"),
            "data_vigencia_jornada": serializer.validated_data.get(
                "workloadEffectiveDate"
            ),
        }
        if servidor is None:
            servidor = criar_servidor(**argumentos)
            status = 201
            mensagem = "Servidor criado com sucesso."
        else:
            servidor = atualizar_servidor(servidor, **argumentos)
            status = 200
            mensagem = "Servidor atualizado com sucesso."
        servidor = obter_servidor(servidor.pk)
    except ValidationError as error:
        return Response({"errors": _errors(error)}, status=400)
    permissoes = _permissoes(request)
    return Response(
        {
            "data": {
                "server": serializar_servidor(
                    servidor,
                    pode_ver_salario=permissoes["canViewSalary"],
                    pode_ver_sensiveis=permissoes["canViewSensitiveData"],
                ),
                "message": mensagem,
            }
        },
        status=status,
    )


@never_cache
@extend_schema(
    methods=["GET"],
    operation_id="servidores_list",
    responses={
        200: ServidoresListResponseSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["POST"],
    operation_id="servidores_create",
    request=ServidorPayloadSerializer,
    responses={
        201: ServidorMutationResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        415: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_servidores(request):
    if not request.user.is_authenticated:
        return _unauthorized()
    if request.method == "POST":
        if not request.user.has_perm(ADD_SERVER_PERMISSION):
            return _denied()
        return _salvar(request)
    if not request.user.has_perm(VIEW_SERVER_PERMISSION):
        return _denied()
    filtros = {
        "busca": (request.GET.get("search") or "").strip(),
        "ativo": (request.GET.get("active") or "").strip().lower(),
        "tipo_vinculo": (request.GET.get("linkType") or "").strip().upper(),
        "servico_id": (request.GET.get("serviceId") or "").strip(),
    }
    permissoes = _permissoes(request)
    servidores = filtrar_servidores(
        **filtros,
        pode_pesquisar_sensiveis=permissoes["canViewSensitiveData"],
    )
    resumo = resumo_servidores(servidores)
    return Response(
        {
            "data": {
                "servers": [
                    serializar_servidor(
                        servidor,
                        pode_ver_salario=permissoes["canViewSalary"],
                        pode_ver_sensiveis=permissoes["canViewSensitiveData"],
                    )
                    for servidor in servidores
                ],
                "summary": {
                    "total": resumo["total"],
                    "active": resumo["ativos"],
                    "inactive": resumo["inativos"],
                    "daily": resumo["diaristas"],
                    "monthly": resumo["mensalistas"],
                },
                "filters": filtros,
                "filterOptions": {
                    "linkTypes": [
                        {"value": valor, "label": rotulo}
                        for valor, rotulo in Servidor.TIPO_VINCULO_CHOICES
                    ],
                    "services": _opcoes_servicos(),
                },
                "permissions": permissoes,
                "meta": {"source": "backend"},
            }
        }
    )


@never_cache
@extend_schema(
    methods=["GET"],
    operation_id="servidores_retrieve",
    responses={
        200: ServidorDetailResponseSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="servidores_update",
    request=ServidorPayloadSerializer,
    responses={
        200: ServidorMutationResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        415: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["DELETE"],
    operation_id="servidores_destroy",
    responses={
        204: None,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT", "DELETE"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_servidor_detalhe(request, pk):
    if not request.user.is_authenticated:
        return _unauthorized()
    permissao_metodo = {
        "GET": VIEW_SERVER_PERMISSION,
        "PUT": CHANGE_SERVER_PERMISSION,
        "DELETE": DELETE_SERVER_PERMISSION,
    }[request.method]
    if not request.user.has_perm(permissao_metodo):
        return _denied()
    try:
        servidor = obter_servidor(pk)
    except Servidor.DoesNotExist as error:
        raise Http404 from error
    if request.method == "PUT":
        return _salvar(request, servidor)
    if request.method == "DELETE":
        excluir_servidor(servidor, usuario=request.user)
        return Response(status=204)
    permissoes = _permissoes(request)
    return Response(
        {
            "data": {
                "server": serializar_servidor(
                    servidor,
                    pode_ver_salario=permissoes["canViewSalary"],
                    pode_ver_sensiveis=permissoes["canViewSensitiveData"],
                ),
                "permissions": permissoes,
                "filterOptions": {"services": _opcoes_servicos()},
                "meta": {"source": "backend"},
            }
        }
    )
