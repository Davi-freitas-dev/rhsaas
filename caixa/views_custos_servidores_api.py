from django.utils import timezone
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Evento, Servico
from .models_servidores import Servidor
from .permissions import (
    VIEW_SERVER_APPROPRIATION_PERMISSION,
    VIEW_SERVER_COSTS_PERMISSION,
)
from .security_salarios import usuario_pode_acessar_custos_salariais
from .selectors_custos_servidores import custos_por_servidor
from .serializers_custos_servidores import (
    CustosPorServidorQuerySerializer,
    CustosPorServidorResponseSerializer,
)
from .serializers_api import HttpApiErrorSerializer


PARAMETROS_FILTRO = {
    "startDate",
    "endDate",
    "serverId",
    "existence",
    "active",
    "linkType",
    "serviceId",
    "eventId",
    "manuallyEdited",
}


@never_cache
@extend_schema(
    parameters=[
        OpenApiParameter("startDate", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        OpenApiParameter("endDate", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        OpenApiParameter("serverId", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("existence", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("active", OpenApiTypes.BOOL, OpenApiParameter.QUERY),
        OpenApiParameter("linkType", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("serviceId", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("eventId", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("manuallyEdited", OpenApiTypes.BOOL, OpenApiParameter.QUERY),
    ],
    responses={
        200: CustosPorServidorResponseSerializer,
        400: HttpApiErrorSerializer,
        401: HttpApiErrorSerializer,
        403: HttpApiErrorSerializer,
        405: HttpApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_custos_por_servidor(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."}, status=401)
    if not request.user.has_perm(VIEW_SERVER_COSTS_PERMISSION):
        return Response({"detail": "Permission denied."}, status=403)
    hoje = timezone.localdate()
    parametros_desconhecidos = sorted(set(request.GET) - PARAMETROS_FILTRO)
    parametros_repetidos = sorted(
        chave
        for chave in PARAMETROS_FILTRO
        if len(request.GET.getlist(chave)) > 1
    )
    erros_query = {}
    if parametros_desconhecidos:
        erros_query["query"] = [
            "Parâmetros não reconhecidos: " + ", ".join(parametros_desconhecidos) + "."
        ]
    if parametros_repetidos:
        erros_query["duplicates"] = [
            "Parâmetros repetidos: " + ", ".join(parametros_repetidos) + "."
        ]
    if erros_query:
        return Response({"errors": erros_query}, status=400)

    entrada = {
        "startDate": request.GET.get("startDate") or hoje.replace(day=1).isoformat(),
        "endDate": request.GET.get("endDate") or hoje.isoformat(),
    }
    for chave in PARAMETROS_FILTRO - {"startDate", "endDate"}:
        valor = request.GET.get(chave)
        if valor not in (None, ""):
            entrada[chave] = valor
    query = CustosPorServidorQuerySerializer(data=entrada)
    if not query.is_valid():
        return Response({"errors": query.errors}, status=400)
    dados = query.validated_data
    data_inicial = dados["startDate"]
    data_final = dados["endDate"]
    filtros = {
        "data_inicial": data_inicial,
        "data_final": data_final,
        "servidor_id": dados.get("serverId", ""),
        "existencia": dados.get("existence", ""),
        "ativo": dados.get("active", ""),
        "tipo_vinculo": dados.get("linkType", ""),
        "servico_id": dados.get("serviceId", ""),
        "evento_id": dados.get("eventId", ""),
        "valor_editado": dados.get("manuallyEdited", ""),
    }
    pode_ver_salario = usuario_pode_acessar_custos_salariais(request.user)
    payload = custos_por_servidor(**filtros, usuario=request.user)
    meta_custos = payload.pop("meta")
    pode_ver_apropriacao = request.user.has_perm(VIEW_SERVER_APPROPRIATION_PERMISSION)
    if not pode_ver_apropriacao:
        for grupo in payload["servers"]:
            grupo["managerialAppropriationTotal"] = None
            for participacao in grupo["participations"]:
                participacao["managerialAppropriation"] = None
        payload["summary"]["managerialAppropriationTotal"] = None

    payload.update(
        {
            "filters": {
                "startDate": data_inicial.isoformat(),
                "endDate": data_final.isoformat(),
                "serverId": str(filtros["servidor_id"]),
                "existence": filtros["existencia"],
                "active": filtros["ativo"],
                "linkType": filtros["tipo_vinculo"],
                "serviceId": str(filtros["servico_id"]),
                "eventId": str(filtros["evento_id"]),
                "manuallyEdited": filtros["valor_editado"],
            },
            "filterOptions": {
                "servers": [
                    {"value": str(item.id), "label": item.nome}
                    for item in Servidor.objects.order_by("nome", "id")
                ],
                "services": [
                    {"value": str(item.id), "label": item.nome}
                    for item in Servico.objects.order_by("nome", "id")
                ],
                "events": [
                    {"value": str(item.id), "label": f"{item.numero} — {item.nome_evento}"}
                    for item in Evento.objects.filter(
                        data_inicio__range=(data_inicial, data_final)
                    ).order_by("data_inicio", "id")
                ],
            },
            "permissions": {
                "canView": True,
                "canViewSalary": pode_ver_salario,
                "canViewManagerialAppropriation": pode_ver_apropriacao,
            },
            "meta": {
                "source": "backend",
                "salarySource": (
                    "materializedSalaryOccurrence" if pode_ver_salario else "redacted"
                ),
                "distributionSource": "EventoCustoServico.valor_diarias",
                "managerialAppropriationCalculated": False,
                **meta_custos,
            },
        }
    )
    return Response({"data": payload})
