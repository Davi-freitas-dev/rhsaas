import json

from django.views.decorators.http import require_GET
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import (
    DASHBOARD_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
    require_permission,
)
from .frontend_bridge import (
    legacy_frontend_redirect_required_response,
)
from .serializers_dashboard import (
    montar_payload_custos_por_evento_api,
    montar_payload_dashboard_financial_overview_api,
)
from .selectors_dashboard_contexto import STATUS_DASHBOARD_FILTRO
from .utils_periodos import (
    PERIODOS_FRONTEND_PARA_RAPIDO,
    intervalo_periodo_frontend,
    normalizar_intervalo_datas,
    normalizar_periodo_frontend,
    normalizar_periodo_rapido,
)
from .utils_contratos import normalizar_codigo_contrato_visual
from .utils_request import normalizar_data_iso


STATUS_FRONTEND_DASHBOARD = {valor for valor, _rotulo in STATUS_DASHBOARD_FILTRO}


@require_permission(DASHBOARD_PERMISSION)
def dashboard_financeiro(request):
    return legacy_frontend_redirect_required_response(request, "dashboard_financeiro")


@require_permission(DASHBOARD_PERMISSION)
def custos_por_evento(request):
    return legacy_frontend_redirect_required_response(request, "custos_por_evento")


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_dashboard_financial_overview(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(DASHBOARD_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    payload = montar_payload_dashboard_financial_overview_api(
        filtros_dashboard_financial_overview(request),
        request.session,
    )
    return drf_response_from_json_response(
        api_no_store_json_response(
            payload,
            json_dumps_params={"ensure_ascii": False},
        )
    )


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_custos_por_evento(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(DASHBOARD_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    payload = montar_payload_custos_por_evento_api(
        filtros_dashboard_financial_overview(request),
        request.session,
    )
    return drf_response_from_json_response(
        api_no_store_json_response(
            payload,
            json_dumps_params={"ensure_ascii": False},
        )
    )


def filtros_dashboard_financial_overview(request):
    data_inicial = normalizar_data_iso(request.GET.get("startDate"))
    data_final = normalizar_data_iso(request.GET.get("endDate"))
    data_inicial, data_final = normalizar_intervalo_datas(data_inicial, data_final)
    periodo = normalizar_periodo_frontend(request.GET.get("period", ""))
    periodo_rapido = normalizar_periodo_rapido(request.GET.get("quickPeriod", ""))
    evento = id_filtro(request.GET.get("eventId"))
    cliente = id_filtro(request.GET.get("clientId"))
    contrato_codigo = contrato_filtro(request.GET.get("contractCode"))
    tem_filtro_entidade = bool(
        evento or cliente or contrato_codigo
    )

    if data_inicial or data_final:
        periodo_rapido = ""
    elif periodo in PERIODOS_FRONTEND_PARA_RAPIDO:
        periodo_rapido = PERIODOS_FRONTEND_PARA_RAPIDO[periodo]
    elif periodo:
        data_inicial, data_final = intervalo_periodo_frontend(periodo)
        periodo_rapido = ""
    elif not periodo_rapido:
        periodo_rapido = "todos" if tem_filtro_entidade else "mes_atual"

    filtros = {
        "data_inicial": data_inicial,
        "data_final": data_final,
        "evento": evento,
        "cliente": cliente,
        "status": normalizar_status_dashboard(request.GET.get("status", "")),
        "periodo_rapido": periodo_rapido,
    }
    if contrato_codigo:
        filtros["contractCode"] = contrato_codigo
    return filtros


def normalizar_status_dashboard(valor):
    valor = str(valor or "").strip()
    return valor if valor in STATUS_FRONTEND_DASHBOARD else ""


def id_filtro(valor):
    valor = str(valor or "").strip()
    return valor if valor.isdigit() else ""


def contrato_filtro(valor):
    return normalizar_codigo_contrato_visual(valor)
