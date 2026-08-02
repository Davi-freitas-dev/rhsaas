from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Evento, Servico
from .models_servidores import ParticipacaoServidorEvento, Servidor
from .permissions import (
    CHANGE_SERVER_DISTRIBUTED_VALUE_PERMISSION,
    MANAGE_SERVER_PARTICIPATION_PERMISSION,
    RECALCULATE_SERVER_COSTS_PERMISSION,
    VIEW_EVENT_PERMISSION,
    VIEW_SERVER_APPROPRIATION_PERMISSION,
    VIEW_SERVER_PARTICIPATION_PERMISSION,
    VIEW_SERVER_SALARY_PERMISSION,
)
from .selectors_participacoes_servidores import (
    listar_participacoes_evento,
    obter_participacao,
)
from .serializers_participacoes_servidores import (
    ParticipacaoCreatePayloadSerializer,
    ParticipacaoDetailResponseSerializer,
    ParticipacaoMutationResponseSerializer,
    ParticipacaoUpdatePayloadSerializer,
    ParticipacoesEventoResponseSerializer,
    RecalculoParticipacoesResponseSerializer,
    serializar_participacao,
)
from .serializers_api import HttpApiErrorSerializer
from .services_participacoes_servidores import (
    atualizar_participacao,
    criar_participacao,
    excluir_participacao,
    recalcular_evento,
    restaurar_calculo_participacao,
)
from .views_clientes_api import JsonBodySafeSessionAuthentication


def _errors(error):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"detail": getattr(error, "messages", [str(error)])}


def _unauthorized():
    return Response({"detail": "Authentication credentials were not provided."}, status=401)


def _denied(detail="Permission denied."):
    return Response({"detail": detail}, status=403)


def _is_json(request):
    return (request.content_type or "").split(";", 1)[0].strip() == "application/json"


def _permissoes(request):
    pode_gerenciar = request.user.has_perm(MANAGE_SERVER_PARTICIPATION_PERMISSION)
    return {
        "canView": request.user.has_perm(
            VIEW_EVENT_PERMISSION
        ) and request.user.has_perm(VIEW_SERVER_PARTICIPATION_PERMISSION),
        "canManage": pode_gerenciar,
        "canEditDistributedValue": pode_gerenciar
        and request.user.has_perm(CHANGE_SERVER_DISTRIBUTED_VALUE_PERMISSION),
        "canRecalculate": pode_gerenciar
        and request.user.has_perm(RECALCULATE_SERVER_COSTS_PERMISSION),
        "canViewSalary": request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION),
        "canViewManagerialAppropriation": request.user.has_perm(
            VIEW_SERVER_APPROPRIATION_PERMISSION
        ),
    }


def _serializar(item, permissoes):
    return serializar_participacao(
        item,
        pode_ver_salario=permissoes["canViewSalary"],
        pode_ver_apropriacao=permissoes["canViewManagerialAppropriation"],
    )


def _opcoes_servidores():
    servidores = (
        Servidor.objects.filter(ativo=True)
        .prefetch_related("vinculos_servicos__servico")
        .order_by("nome", "id")
    )
    return [
        {
            "id": servidor.id,
            "value": str(servidor.id),
            "label": servidor.nome,
            "linkType": servidor.tipo_vinculo,
            "services": [
                {
                    "id": vinculo.servico_id,
                    "name": vinculo.servico.nome,
                    "code": vinculo.servico.codigo,
                }
                for vinculo in servidor.vinculos_servicos.all()
                if vinculo.ativo and vinculo.servico.ativo
            ],
        }
        for servidor in servidores
    ]


@never_cache
@extend_schema(
    methods=["GET"],
    responses={
        200: ParticipacoesEventoResponseSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["POST"],
    request=ParticipacaoCreatePayloadSerializer,
    responses={
        201: ParticipacaoMutationResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        415: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_participacoes_evento(request, evento_id):
    if not request.user.is_authenticated:
        return _unauthorized()
    permissoes = _permissoes(request)
    if request.method == "POST":
        if not permissoes["canManage"]:
            return _denied()
    elif not permissoes["canView"]:
        return _denied()
    evento = get_object_or_404(Evento.objects.select_related("cliente"), pk=evento_id)
    if request.method == "POST":
        if not _is_json(request):
            return Response({"detail": "Content-Type deve ser application/json."}, status=415)
        serializer = ParticipacaoCreatePayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"errors": serializer.errors}, status=400)
        try:
            servidor = Servidor.objects.get(pk=serializer.validated_data["serverId"])
            servico = Servico.objects.get(pk=serializer.validated_data["serviceId"])
            participacao = criar_participacao(
                evento=evento,
                servidor=servidor,
                servico=servico,
                quantidade_dias=serializer.validated_data.get("days", 0),
                quantidade_horas=serializer.validated_data.get("hours", 0),
                datas_trabalhadas=serializer.validated_data["workedDays"],
                usuario=request.user,
            )
            participacao = obter_participacao(participacao.pk)
        except (Servidor.DoesNotExist, Servico.DoesNotExist):
            return Response({"errors": {"detail": ["Servidor ou serviço não encontrado."]}}, status=400)
        except ValidationError as error:
            return Response({"errors": _errors(error)}, status=400)
        return Response(
            {"data": {"participation": _serializar(participacao, permissoes)}},
            status=201,
        )
    participacoes = listar_participacoes_evento(evento)
    return Response(
        {
            "data": {
                "event": {
                    "id": evento.id,
                    "name": evento.nome_evento,
                    "number": evento.numero,
                    "startDate": evento.data_inicio.isoformat(),
                    "endDate": evento.data_fim.isoformat(),
                    "status": evento.status,
                    "readOnly": evento.status in {"concluido", "cancelado"},
                },
                "participations": [_serializar(item, permissoes) for item in participacoes],
                "serverOptions": _opcoes_servidores() if permissoes["canManage"] else [],
                "permissions": permissoes,
                "meta": {"source": "backend"},
            }
        }
    )


@never_cache
@extend_schema(
    methods=["GET"],
    responses={
        200: ParticipacaoDetailResponseSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    request=ParticipacaoUpdatePayloadSerializer,
    responses={
        200: ParticipacaoMutationResponseSerializer,
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
    responses={
        204: None,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT", "DELETE"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_participacao_detalhe(request, pk):
    if not request.user.is_authenticated:
        return _unauthorized()
    permissoes = _permissoes(request)
    if request.method == "GET":
        if not permissoes["canView"]:
            return _denied()
    elif not permissoes["canManage"]:
        return _denied()
    try:
        participacao = obter_participacao(pk)
    except ParticipacaoServidorEvento.DoesNotExist as error:
        raise Http404 from error
    if request.method == "GET":
        return Response({"data": {"participation": _serializar(participacao, permissoes), "permissions": permissoes}})
    if request.method == "DELETE":
        try:
            excluir_participacao(participacao, usuario=request.user)
        except ValidationError as error:
            return Response({"errors": _errors(error)}, status=400)
        return Response(status=204)
    if not _is_json(request):
        return Response({"detail": "Content-Type deve ser application/json."}, status=415)
    serializer = ParticipacaoUpdatePayloadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=400)
    if "finalAmount" in serializer.validated_data and not permissoes["canEditDistributedValue"]:
        return _denied("O usuário não tem permissão para editar o valor distribuído.")
    try:
        servico = Servico.objects.get(pk=serializer.validated_data["serviceId"])
        participacao = atualizar_participacao(
            participacao,
            servico=servico,
            quantidade_dias=serializer.validated_data.get(
                "days",
                participacao.quantidade_dias,
            ),
            quantidade_horas=serializer.validated_data.get(
                "hours",
                participacao.quantidade_horas,
            ),
            datas_trabalhadas=serializer.validated_data.get("workedDays"),
            valor_final=serializer.validated_data.get("finalAmount"),
            motivo_edicao=serializer.validated_data.get("editReason", ""),
            usuario=request.user,
        )
        participacao = obter_participacao(participacao.pk)
    except Servico.DoesNotExist:
        return Response({"errors": {"serviceId": ["Serviço não encontrado."]}}, status=400)
    except ValidationError as error:
        return Response({"errors": _errors(error)}, status=400)
    return Response({"data": {"participation": _serializar(participacao, permissoes)}})


@never_cache
@extend_schema(
    request=None,
    responses={
        200: ParticipacaoMutationResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_restaurar_calculo_participacao(request, pk):
    if not request.user.is_authenticated:
        return _unauthorized()
    if not (
        request.user.has_perm(MANAGE_SERVER_PARTICIPATION_PERMISSION)
        and request.user.has_perm(CHANGE_SERVER_DISTRIBUTED_VALUE_PERMISSION)
    ):
        return _denied()
    participacao = get_object_or_404(ParticipacaoServidorEvento, pk=pk)
    try:
        participacao = restaurar_calculo_participacao(participacao, usuario=request.user)
        participacao = obter_participacao(participacao.pk)
    except ValidationError as error:
        return Response({"errors": _errors(error)}, status=400)
    permissoes = _permissoes(request)
    return Response({"data": {"participation": _serializar(participacao, permissoes)}})


@never_cache
@extend_schema(
    request=None,
    responses={
        200: RecalculoParticipacoesResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        404: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_recalcular_participacoes_evento(request, evento_id):
    if not request.user.is_authenticated:
        return _unauthorized()
    if not (
        request.user.has_perm(MANAGE_SERVER_PARTICIPATION_PERMISSION)
        and request.user.has_perm(RECALCULATE_SERVER_COSTS_PERMISSION)
    ):
        return _denied()
    evento = get_object_or_404(Evento, pk=evento_id)
    try:
        grupos = recalcular_evento(evento, usuario=request.user)
    except ValidationError as error:
        return Response({"errors": _errors(error)}, status=400)
    return Response({"data": {"recalculatedGroups": grupos}})
